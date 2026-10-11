import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reset the existing MyBank administrator password."

    def handle(self, *args, **options):
        password = os.environ.get("MYBANK_ADMIN_RESET_PASSWORD")

        if not password:
            raise CommandError(
                "MYBANK_ADMIN_RESET_PASSWORD is not configured."
            )

        if len(password) < 12:
            raise CommandError(
                "The temporary password must contain at least 12 characters."
            )

        User = get_user_model()

        try:
            admin = User.objects.get(username="admin")
        except User.DoesNotExist:
            raise CommandError(
                "The admin user does not exist in this database."
            )

        if admin.check_password(password):
            self.stdout.write(
                self.style.SUCCESS(
                    "The administrator password is already set correctly."
                )
            )
            return

        admin.set_password(password)
        admin.save(update_fields=["password"])

        self.stdout.write(
            self.style.SUCCESS(
                "The administrator password has been reset successfully."
            )
        )
