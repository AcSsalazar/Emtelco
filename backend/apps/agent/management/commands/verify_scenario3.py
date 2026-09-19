"""Demonstrate Scenario 3 persistence at the backend level.

Runs the same tools the agent uses (no LLM involved) and shows the rows that
end up in the database, so the result does not depend on what the agent says.

Usage:
    python manage.py verify_scenario3
    python manage.py verify_scenario3 --order GUI-845A7W
    python manage.py verify_scenario3 --cleanup
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import Customer
from apps.agent.orchestrator import escalate_conversation
from apps.agent.tools import registry as tool_registry
from apps.agent.tools.registry import ToolContext, execute_tool
from apps.conversations.models import Conversation
from apps.orders.models import Order, Warranty
from apps.support.models import SupportTicket

DEFAULT_IDENTIFICATION = "1023456789"


class Command(BaseCommand):
    help = "Demuestra la persistencia del Escenario 3 (garantía y soporte)."

    def add_arguments(self, parser):
        parser.add_argument("--identification", default=DEFAULT_IDENTIFICATION)
        parser.add_argument("--order", help="Número de guía a usar (GUI-XXXXXX).")
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Borra la conversación y los tickets creados al terminar.",
        )

    def handle(self, *args, **options):
        tool_registry._load_tools()
        customer = self._customer(options["identification"])
        order = self._order(customer, options.get("order"))
        warranty = Warranty.objects.filter(order=order).first()

        self.stdout.write(self.style.MIGRATE_HEADING("=== ESTADO ANTES ==="))
        self._print_warranties(customer)
        self.stdout.write(f"Tickets del cliente: {SupportTicket.objects.filter(customer=customer).count()}")
        self.stdout.write(
            f"Conversaciones escaladas: {Conversation.objects.filter(customer=customer, escalated=True).count()}"
        )

        conversation = Conversation.objects.create(customer=customer, title="Verificación Escenario 3")
        context = ToolContext(customer=customer, conversation=conversation)
        created_tickets = []

        # --- Paso 1: validar cobertura -----------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== PASO 1 · Validar cobertura (tool: check_warranty) ==="
        ))
        result = execute_tool("check_warranty", {"order_number": order.number}, context)
        self.stdout.write(f"found={result.get('found')} count={result.get('count')}")
        for item in result.get("warranties", []):
            self.stdout.write(
                f"  {item['number']} | {item['product']} | {item['coverage_status']} "
                f"| is_active={item['is_active']} | vence {item['expiration_date']}"
            )
        self.stdout.write("→ Cobertura leída de la base de datos.")

        # --- Paso 2: registrar el caso ------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== PASO 2 · Registrar el caso (tool: create_warranty_request) ==="
        ))
        result = execute_tool(
            "create_warranty_request",
            {
                "order_number": order.number,
                "description": "El televisor no enciende; la pantalla queda negra y solo se escucha el audio.",
            },
            context,
        )
        if "error" in result:
            raise CommandError(result["error"])
        created_tickets.append(result["ticket_number"])
        self.stdout.write(
            f"created={result['created']} ticket_number={result['ticket_number']} "
            f"order_number={result['order_number']}"
        )
        self._print_ticket(result["ticket_number"])

        # --- Paso 3: escalamiento -----------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== PASO 3 · Escalamiento (escalate_conversation) ==="
        ))
        escalate_conversation(conversation)
        conversation.refresh_from_db()
        self.stdout.write(
            f"conversations_conversation.escalated = {conversation.escalated} "
            f"(id={conversation.id})"
        )
        escalation_ticket = (
            SupportTicket.objects.filter(
                conversation=conversation, source=SupportTicket.Source.ESCALATION
            )
            .order_by("-id")
            .first()
        )
        if escalation_ticket:
            created_tickets.append(escalation_ticket.number)
            self._print_ticket(escalation_ticket.number)

        # --- Después -------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== ESTADO DESPUÉS ==="))
        self.stdout.write(f"Tickets del cliente: {SupportTicket.objects.filter(customer=customer).count()}")
        self.stdout.write(
            f"Conversaciones escaladas: {Conversation.objects.filter(customer=customer, escalated=True).count()}"
        )

        if options["cleanup"]:
            SupportTicket.objects.filter(number__in=created_tickets).delete()
            conversation.delete()
            self.stdout.write(self.style.WARNING("\nDatos de la verificación eliminados (--cleanup)."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nDatos dejados en la base para inspección en /admin/ "
                    f"(conversación #{conversation.id}, tickets {', '.join(created_tickets)})."
                )
            )

    # -- helpers ---------------------------------------------------------
    def _customer(self, identification: str) -> Customer:
        customer = Customer.objects.filter(identification=identification).first()
        if customer is None:
            raise CommandError(f"No existe un cliente con identificación {identification}.")
        return customer

    def _order(self, customer: Customer, number: str | None) -> Order:
        qs = Order.objects.filter(customer=customer).select_related("product")
        if number:
            order = qs.filter(number__iexact=number).first()
            if order is None:
                raise CommandError(f"No existe el pedido {number} para este cliente.")
            return order
        order = (
            qs.filter(
                warranties__coverage_status=Warranty.CoverageStatus.ACTIVE,
                product__category="tv",
            )
            .order_by("-created_at")
            .first()
        )
        if order is None:
            order = (
                qs.filter(warranties__coverage_status=Warranty.CoverageStatus.ACTIVE)
                .order_by("-created_at")
                .first()
            )
        if order is None:
            order = qs.order_by("-created_at").first()
        if order is None:
            raise CommandError("El cliente no tiene pedidos.")
        return order

    def _print_warranties(self, customer: Customer) -> None:
        warranties = Warranty.objects.filter(order__customer=customer).select_related(
            "product", "order"
        )
        self.stdout.write("Garantías del cliente:")
        for warranty in warranties:
            self.stdout.write(
                f"  {warranty.number} | {warranty.product.name} | "
                f"{warranty.coverage_status} | vence {warranty.expiration_date} | "
                f"pedido {warranty.order.number}"
            )

    def _print_ticket(self, number: str) -> None:
        ticket = SupportTicket.objects.select_related("customer", "warranty").get(
            number=number
        )
        self.stdout.write("Fila persistida en support_supportticket:")
        self.stdout.write(
            f"  id={ticket.id}  number={ticket.number}  source={ticket.source}  "
            f"status={ticket.status}  priority={ticket.priority}"
        )
        self.stdout.write(
            f"  customer={ticket.customer.full_name} ({ticket.customer.identification})"
        )
        self.stdout.write(
            f"  warranty={ticket.warranty.number if ticket.warranty else '-'}  "
            f"conversation=#{ticket.conversation_id}"
        )
        self.stdout.write(f"  created_at={ticket.created_at:%Y-%m-%d %H:%M:%S} (ahora {timezone.now():%H:%M:%S})")
