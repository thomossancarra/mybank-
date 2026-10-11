from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Show administrator usernames for troubleshooting."

    def handle(self, *args, **options):
        User = get_user_model()

        admins = User.objects.filter(
            is_superuser=True
        ).values_list("username", flat=True)

        usernames = list(admins)

        if usernames:
            self.stdout.write("Superuser usernames:")
            for username in usernames:
                self.stdout.write(f"- {username}")
        else:
            self.stdout.write("No superuser accounts found.")
