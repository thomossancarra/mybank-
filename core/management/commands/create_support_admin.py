from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create the MyBank support admin user"

    def handle(self, *args, **kwargs):
        username = "supportadmin"
        password = "SupportAdmin123!"

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Support admin '{username}' already exists."
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            email="support@mybank.com",
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Support admin created successfully."
            )
        )