import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or configure the dedicated MyBank live administrator."

    def handle(self, *args, **options):
        username = os.environ.get("MYBANK_ADMIN_USERNAME", "").strip()
        password = os.environ.get("MYBANK_ADMIN_RESET_PASSWORD", "")

        if not username or not password:
            raise CommandError(
                "MYBANK_ADMIN_USERNAME and "
                "MYBANK_ADMIN_RESET_PASSWORD must be configured."
            )

        if len(password) < 16:
            raise CommandError(
                "Use a temporary password of at least 16 characters."
            )

        User = get_user_model()

        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            user = None

        if user is not None and not user.is_superuser:
            raise CommandError(
                "That username already belongs to a non-superuser. "
                "Choose a different, unused administrator username."
            )

        if user is None:
            user = User.objects.create_user(
                **{
                    User.USERNAME_FIELD: username,
                    "password": password,
                }
            )
        elif user.check_password(password):
            self.stdout.write(
                self.style.SUCCESS(
                    "The administrator account is already configured."
                )
            )
            return
        else:
            user.set_password(password)

        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                "The live administrator account is ready."
            )
        )
