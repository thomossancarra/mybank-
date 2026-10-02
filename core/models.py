from django.db import models
import random
from django.contrib.auth.models import User

COUNTRY_CURRENCIES = {
    "Nigeria": "NGN",
    "United States": "USD",
    "United Kingdom": "GBP",
    "Canada": "CAD",
    "Mexico": "MXN",
    "Brazil": "BRL",
    "Spain": "EUR",
    "France": "EUR",
    "Germany": "EUR",
    "Italy": "EUR",
    "Portugal": "EUR",
    "Netherlands": "EUR",
    "Ireland": "EUR",
    "Australia": "AUD",
    "New Zealand": "NZD",
    "Japan": "JPY",
    "China": "CNY",
    "India": "INR",
    "South Africa": "ZAR",
    "Ghana": "GHS",
    "Kenya": "KES",
    "Switzerland": "CHF",
    "Sweden": "SEK",
    "Norway": "NOK",
    "Denmark": "DKK",
}

def generate_account_number():
    return str(random.randint(1000000000, 9999999999))


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    country = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    state = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    ACCOUNT_TYPES = [
        ("savings", "Savings"),
        ("current", "Current"),
    ]

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES,
        default="savings"
    )

    ACCOUNT_STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS,
        default="pending"
    )


    profile_photo = models.ImageField(

        upload_to="profile_photos/",
        blank=True,
        null=True
    )

    account_number = models.CharField(

        max_length=10,

        unique=True,

        null=True,

        blank=True

    )

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if not self.account_number:
            account_number = generate_account_number()

            while Account.objects.filter(account_number=account_number).exists():
                account_number = generate_account_number()

            self.account_number = account_number

        super().save(*args, **kwargs)
    

    def __str__(self):
        return self.user.username


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("deposit", "Account Credit"),
        ("withdraw", "Withdrawal"),
        ("transfer", "Transfer"),
    ]

    FUNDING_TYPES = [
        ("local", "Local"),
        ("international", "International"),
    ]

    funding_type = models.CharField(
        max_length=20,
        choices=FUNDING_TYPES,
        blank=True,
        null=True
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    description = models.CharField(
        max_length=255,
        blank=True
    )

    reference = models.CharField(
    max_length=50,
    unique=True,
    blank=True,
    null=True
)
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.account.user.username} - {self.transaction_type} - ₦{self.amount}"  

class Notification(models.Model):
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=200)

    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TransferOTP(models.Model):
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transfer_otps"
    )

    recipient_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="received_transfer_otps"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    code = models.CharField(
        max_length=6
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    verified = models.BooleanField(
        default=False
    )

class SupportRequest(models.Model):

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="support_requests"
    )

    reference_number = models.CharField(
        max_length=30,
        unique=True
    )

    subject = models.CharField(
        max_length=200
    )

    message = models.TextField()

    status = models.CharField(
    max_length=30,
    choices=[
        ("Received", "Received"),
        ("In Progress", "In Progress"),
        ("Awaiting Customer", "Awaiting Customer"),
        ("Resolved", "Resolved"),
        ("Closed", "Closed"),
    ],
    default="Received",
)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.reference_number


class SupportMessage(models.Model):

    support_request = models.ForeignKey(
        SupportRequest,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.support_request.reference_number} - {self.sender.username}"

class SystemSettings(models.Model):


    bank_name = models.CharField(
        max_length=150,
        default="MyBank"
    )

    support_email = models.EmailField(
        default="support@mybank.com"
    )

    support_phone = models.CharField(
        max_length=30,
        blank=True
    )

    support_message = models.TextField(
        blank=True,
        default="Our support team is available to assist you."
    )

    maintenance_mode = models.BooleanField(
        default=False
    )

    maintenance_message = models.TextField(
        blank=True,
        default="MyBank is temporarily unavailable for maintenance. Please try again later."
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.bank_name
        
class AdminActivity(models.Model):

    admin_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    action = models.CharField(
        max_length=255
    )

    details = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.admin_user.username} - {self.action}"