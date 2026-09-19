# Arquitectura

## Visión general

```text
React (Vite, JavaScript)
   │  JWT
   ▼
Django REST API
   ├─ Authentication / Authorization
   ├─ Guard / Moderation
   ├─ Agent Orchestrator
   │     ├─ Context Builder (historial + memoria)
   │     ├─ LLM Provider (OpenAI)
   │     └─ Tools  ──► Django ORM ──► SQLite
   └─ Memory / Conversation (persistencia)
```

La base de datos es la única fuente de verdad para precios, stock, pedidos,
fechas y garantías. El LLM nunca es fuente de datos de negocio.

## Capas

### Guard (`apps/agent/guard.py`, `apps/agent/moderation.py`)

Es una **capa de seguridad**, no de flujo conversacional. Solo decide lo que es
binario y determinista:

1. **Bloqueos**: estado permanente o temporal del cliente.
2. **Violaciones**: insultos o contenido inapropiado, que disparan la escalera de
   penalización.

Todo lo demás se devuelve como **señal** para que el **Agent** lo resuelva con el
contexto completo de la conversación:

- alcance (`in_scope` / `out_of_scope`) → el agente redirige con amabilidad;
- `prompt_injection` → el agente rechaza y continúa.

La clasificación incluye los **últimos mensajes** de la conversación, de modo que
una respuesta corta ("máximo 5 millones", "el del televisor") se interpreta en
contexto y nunca se bloquea por parecer aislada. El Guard nunca responde en
lugar del agente ni corta la conversación por alcance.

La penalización se decide siempre en backend, en `moderation.py`, nunca en el
prompt. Escalera (configurable con `AGENT_PERMANENT_BLOCK_AFTER`):

| Violación | Insulto leve (`low`) | Contenido grave (`high`) |
|---|---|---|
| 1.ª | Advertencia | Bloqueo temporal (3 min) |
| 2.ª | Advertencia más firme | Permanente |
| 3.ª | Bloqueo temporal (3 min) | Permanente |
| 4.ª+ | Permanente | Permanente |

El primer strike nunca es permanente. `manage.py moderation` permite ver el
estado y desbloquear (`--unblock <identificación>`) para soporte y pruebas.

La misma llamada clasificadora extrae señales de perfil (usos, software, marcas,
sistema, presupuesto, experiencia) que se fusionan en `CustomerProfile`.

Como red de seguridad, `output_guard.py` revisa la respuesta del agente antes de
guardarla: si contiene lenguaje inapropiado, la reemplaza por un mensaje seguro.

### Agent (`apps/agent/orchestrator.py`)

Responde: *¿cómo se resuelve la solicitud?*

1. Ejecuta Guard.
2. Construye el contexto (system prompt + historial reciente + memoria).
3. Llama al LLM con las herramientas disponibles.
4. Ejecuta tool calls contra la base de datos y realimenta al modelo.
5. Genera la respuesta final.
6. Clasifica el resultado del turno y actualiza intentos sin resolver y
   escalamiento.

### Tools (`apps/agent/tools/`)

Diez herramientas expuestas por function calling, todas contra el ORM y
restringidas al cliente autenticado:

- Catálogo: `search_products`, `get_product_details`, `compare_products`,
  `recommend_products`.
- Pedidos: `get_order_status`, `get_delivery_estimate`,
  `update_delivery_address`.
- Garantías y soporte: `check_warranty`, `create_warranty_request`,
  `create_support_ticket`.

Cada una declara nombre, descripción, JSON schema de parámetros, validación y
manejo de errores. Los errores se devuelven como `{"error": ...}` sin filtrar
detalles internos.

### Memoria (`apps/agent/memory.py`, `apps/agent/context_builder.py`)

Memoria estructurada persistente (sin RAG ni embeddings): nombre, presupuesto,
productos consultados, preferencias, último pedido, último producto, intención
reciente e intentos sin resolver. El Context Builder decide qué enviar al
modelo (memoria + últimos N mensajes).

## Abstracción del proveedor LLM

```text
Agent
  └─ LLMProvider (contrato)
        └─ OpenAIProvider (implementación)
```

`apps/agent/llm/base.py` define `LLMProvider`, `LLMResponse` y `ToolCall`.
`factory.py` resuelve el proveedor según `LLM_PROVIDER`. Cambiar de proveedor no
afecta a tools, memoria, modelos de negocio, API ni frontend. Los tests inyectan
un proveedor falso con `set_llm_provider()` sin tocar código de producción.

## Modelo de datos

- `Customer` (1:1 con `User`), `CustomerProfile` (preferencias persistentes) y
  `CustomerModeration`.
- `Product` (incluye `image` para las miniaturas del chat).
- `Order` y `Warranty`.
- `Conversation`, `Message` (con `metadata` para adjuntos estructurados, como
  las tarjetas de producto), `ConversationMemory`.
- `SupportTicket`.

El detalle de una conversación devuelve los últimos 50 mensajes
(`MESSAGE_LIMIT`) y el total en `message_count`. `POST .../messages` acepta
`{"retry": true}` para regenerar la respuesta de un turno interrumpido sin
duplicar el mensaje del usuario.

## Perfil del cliente

`CustomerProfile` guarda preferencias durables (usos, software, marcas, sistema,
presupuesto, experiencia). Se alimenta de dos fuentes: la clasificación por
turno (fusionada con el Guard, en una sola llamada) y la herramienta
`save_customer_preference`. Se inyecta en el system prompt junto con la memoria
de la conversación y se expone en `GET/PATCH /api/profile`.

## Prompt caching y coste

El prompt del agente se divide en dos mensajes de sistema:

1. **Estable**: la política (`docs/agent-policy.md`), idéntica en cada petición.
2. **Volátil**: perfil, memoria de la conversación y señales del turno.

Junto con los esquemas de herramientas (que van primero), la parte estable forma
un **prefijo cacheable**. OpenAI cachea automáticamente los prefijos largos, así
que los turnos repetidos pagan una fracción de esos tokens (en `gpt-4o-mini`, el
token cacheado cuesta la mitad).

Las herramientas de catálogo devuelven **tarjetas compactas** (id, nombre, marca,
precio, stock, imagen y especificaciones clave); la ficha completa se reserva
para `get_product_details` y `compare_products`, lo que reduce el tamaño de los
resultados de herramienta.

`manage.py token_report` mide el consumo con el tokenizer real:

```bash
python backend/manage.py token_report
python backend/manage.py token_report --conversation 12
```

## Imágenes de producto

`fetch_product_images` asigna una imagen a cada producto (descarga con respaldo
de generación local con Pillow) y la guarda en `backend/media/products/`. El
orquestador recolecta los productos devueltos por las herramientas y los adjunta
como `metadata.products` al mensaje del asistente; el frontend los renderiza como
tarjetas con miniatura.

## Seguridad

- JWT (access/refresh) en todas las rutas del agente.
- La identidad sale de `request.user -> Customer`; el frontend nunca envía un
  `customer_id` en el que el backend confíe.
- Autorización por propietario en views y tools (un cliente no ve ni modifica
  datos de otro).
- Errores internos solo a logs; al usuario, mensajes naturales.
- La API key de OpenAI vive solo en el backend.
