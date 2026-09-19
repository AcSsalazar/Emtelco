"""Inspect or change a customer's moderation state.

Usage:
    python manage.py moderation --list
    python manage.py moderation --unblock 1023456789
    python manage.py moderation --block 1023456789
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import Customer, CustomerModeration
from apps.agent import moderation as moderation_service


class Command(BaseCommand):
    help = "Inspect or change a customer's moderation state."

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", help="List all moderation states.")
        parser.add_argument(
            "--unblock",
            metavar="IDENTIFICATION",
            help="Clear blocks and reset counters for a customer.",
        )
        parser.add_argument(
            "--block",
            metavar="IDENTIFICATION",
            help="Set a permanent block for a customer.",
        )

    def handle(self, *args, **options):
        if options["unblock"]:
            self._unblock(options["unblock"])
            return
        if options["block"]:
            self._block(options["block"])
            return
        self._list()

    def _get_customer(self, identification: str) -> Customer:
        customer = Customer.objects.filter(identification=identification).first()
        if customer is None:
            raise CommandError(
                f"No existe un cliente con identificación {identification}."
            )
        return customer

    def _unblock(self, identification: str) -> None:
        customer = self._get_customer(identification)
        moderation_service.unblock(customer)
        self.stdout.write(
            self.style.SUCCESS(
                f"{customer.full_name} desbloqueado y contadores en cero."
            )
        )

    def _block(self, identification: str) -> None:
        customer = self._get_customer(identification)
        moderation_service.block_permanently(customer)
        self.stdout.write(
            self.style.WARNING(f"{customer.full_name} bloqueado permanentemente.")
        )

    def _list(self) -> None:
        states = CustomerModeration.objects.select_related("customer")
        if not states.exists():
            self.stdout.write("Sin estados de moderación.")
            return
        now = timezone.now()
        for moderation in states:
            if moderation.permanent_blocked:
                state = "permanente"
            elif moderation.temporary_block_until and moderation.temporary_block_until > now:
                state = "temporal"
            else:
                state = "ok"
            self.stdout.write(
                f"{moderation.customer.identification}  "
                f"{moderation.customer.full_name}: {state} "
                f"(violaciones={moderation.violation_count}, "
                f"advertencias={moderation.warning_count})"
            )
