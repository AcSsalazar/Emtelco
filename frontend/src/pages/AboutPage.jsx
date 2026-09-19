import { Link } from "react-router-dom";

export default function AboutPage() {
  return (
    <div className="about">
      <header className="about-hero">
        <p className="eyebrow">Acerca de</p>
        <h1>Emmet, un asesor que decide y actúa</h1>
        <p className="lead">
          Un agente de atención al cliente para un retail de electrónica que no
          se limita a listar datos: interpreta, compara, recomienda y resuelve
          usando herramientas reales contra la base de datos.
        </p>
      </header>

      <section className="about-section">
        <h2>El problema</h2>
        <p>
          Un chatbot que solo repite campos obliga al cliente a hacer todo el
          trabajo. La atención de verdad exige entender la necesidad, consultar
          información confiable y decidir cuándo resolver, cuándo preguntar y
          cuándo escalar.
        </p>
      </section>

      <section className="about-section">
        <h2>El enfoque</h2>
        <p>
          Separamos <strong>hechos</strong> de <strong>criterio</strong>. Los
          datos del negocio (precios, stock, pedidos, entregas, garantías) salen
          siempre de herramientas que consultan la base de datos. El razonamiento
          —comparar, priorizar, recomendar— vive en el agente, guiado por una
          política controlada. Así el agente asesora de verdad sin inventar un
          solo dato.
        </p>
      </section>

      <section className="about-section">
        <h2>Cómo funciona</h2>
        <ol className="about-steps">
          <li>
            <strong>Guard:</strong> decide si la solicitud debe procesarse
            (bloqueos, contenido inapropiado, fuera de dominio) y extrae señales
            de perfil.
          </li>
          <li>
            <strong>Agente:</strong> interpreta la intención, decide si necesita
            una herramienta, la ejecuta y redacta una respuesta natural.
          </li>
          <li>
            <strong>Herramientas:</strong> catálogo, comparación, recomendación,
            pedidos, entregas y garantías, siempre contra la base de datos.
          </li>
          <li>
            <strong>Memoria y perfil:</strong> conserva el contexto de la
            conversación y las preferencias del cliente para adaptar el tono.
          </li>
          <li>
            <strong>Escalamiento:</strong> cuando el caso lo requiere, lo registra
            y lo deja para una persona del equipo.
          </li>
        </ol>
      </section>

      <section className="about-section">
        <h2>Confianza y seguridad</h2>
        <ul className="about-list">
          <li>La API key del modelo vive solo en el backend.</li>
          <li>Cada cliente accede únicamente a su propia información.</li>
          <li>No se revelan instrucciones internas ni secretos.</li>
          <li>Sin datos inventados: si no está en el sistema, se dice.</li>
        </ul>
      </section>

      <section className="about-section">
        <h2>Tecnología</h2>
        <p>
          Django REST + JWT + SQLite en el backend, con una capa de proveedor de
          LLM intercambiable. React + Vite en el frontend. Tests con pytest,
          incluido el flujo completo de solicitud a respuesta.
        </p>
      </section>

      <div className="about-cta">
        <Link to="/register" className="btn-primary">
          Crear cuenta
        </Link>
        <Link to="/login" className="btn-secondary">
          Iniciar sesión
        </Link>
      </div>
    </div>
  );
}
