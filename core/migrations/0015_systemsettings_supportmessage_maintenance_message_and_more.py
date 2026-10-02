from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_alter_supportrequest_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "bank_name",
                    models.CharField(
                        default="MyBank",
                        max_length=150,
                    ),
                ),
                (
                    "support_email",
                    models.EmailField(
                        default="support@mybank.com",
                        max_length=254,
                    ),
                ),
                (
                    "support_phone",
                    models.CharField(
                        blank=True,
                        max_length=30,
                    ),
                ),
                (
                    "support_message",
                    models.TextField(
                        blank=True,
                        default="Our support team is available to assist you.",
                    ),
                ),
                (
                    "maintenance_mode",
                    models.BooleanField(
                        default=False,
                    ),
                ),
                (
                    "maintenance_message",
                    models.TextField(
                        blank=True,
                        default="MyBank is temporarily unavailable for maintenance. Please try again later.",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
            ],
        ),
    ]