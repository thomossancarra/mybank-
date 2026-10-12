from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from django import forms
from django.utils import timezone
import uuid
import logging
logger = logging.getLogger(__name__)

from .models import (
    Account,
    Transaction,
    Notification,
    SupportRequest,
    SupportMessage,
    SystemSettings,
    AdminActivity,
)


# Create the MyBank Support Team group


class FundAccountForm(forms.Form):
    funding_type = forms.ChoiceField(
        label="Funding Type",
        choices=[
            ("local", "Local"),
            ("international", "International"),
        ]
    )

    amount = forms.DecimalField(
        label="Amount",
        max_digits=12,
        decimal_places=2,
        min_value=0.01
    )

    description = forms.CharField(
        label="Payment Description / Purpose",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. Salary payment, investment proceeds"
            }
        )
    )


@admin.action(description="Fund selected account")
def fund_account(modeladmin, request, queryset):

    if "apply" in request.POST:

        form = FundAccountForm(request.POST)

        if form.is_valid():

            account_id = request.POST.get("_selected_action")

            account = Account.objects.get(pk=account_id)

            funding_type = form.cleaned_data["funding_type"]
            amount = form.cleaned_data["amount"]
            description = form.cleaned_data["description"]

            previous_balance = account.balance
            account.balance += amount
            account.save()

            reference = (
                f"MBK-CR-"
                f"{timezone.now().strftime('%Y%m%d')}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )

            Transaction.objects.create(
                account=account,
                transaction_type="deposit",
                amount=amount,
                description=description,
                funding_type=funding_type,
                reference=reference,
            )

            AdminActivity.objects.create(
                admin_user=request.user,
                action="Account Funded",
                details=(
                    f"Credited account {account.account_number} "
                    f"with ${amount:,.2f} USD. "
                    f"Funding Type: {funding_type.title()}. "
                    f"Description: {description}. "
                    f"Reference: {reference}."
                ),
            )

            Notification.objects.create(
                account=account,
                title="Account Credited",
                message=(
                    f"Your account has been credited with "
                    f"{amount} USD.\n\n"
                    f"Funding Type: {funding_type.title()}\n"
                    f"Purpose: {description}\n"
                    f"Reference: {reference}"
                )
            )

            send_mail(
                subject="MyBank Account Credit Notification",
                message=f"""
Dear {account.user.first_name or account.user.username},

Your MyBank account has been successfully credited.

ACCOUNT CREDIT DETAILS
----------------------

Account Holder:
{account.user.get_full_name() or account.user.username}

Account Number:
{account.account_number}

Funding Type:
{funding_type.title()}

Amount Credited:
${amount:,.2f} USD

Payment Description:
{description}

Previous Balance:
${previous_balance:,.2f} USD

New Available Balance:
${account.balance:,.2f} USD

Transaction Reference:
{reference}

Date:
{timezone.now().strftime("%B %d, %Y at %H:%M")}

The above credit has been successfully applied to your MyBank account.

If you do not recognize this transaction, please contact MyBank Account Support immediately.

For your security, never share your password, PIN, or security codes with anyone.

Kind regards,

MyBank
Account Administration
Secure Online Banking
""",
                from_email="noreply@mybank.com",
                recipient_list=[account.user.email],
                fail_silently=False,
            )

            modeladmin.message_user(
                request,
                f"Account {account.account_number} was successfully credited "
                f"with ${amount:,.2f}. "
                f"Reference: {reference}"
            )

            return None

    else:
        form = FundAccountForm()

    from django.shortcuts import render

    return render(
        request,
        "admin/fund_account.html",
        {
            "form": form,
            "account": queryset.first(),
            "title": "Fund Customer Account",
        },
    )



@admin.action(description="Approve selected accounts")
def approve_accounts(modeladmin, request, queryset):
    approved_count = 0
    email_sent_count = 0
    email_failed_count = 0
    activity_failed_count = 0

    login_url = request.build_absolute_uri(reverse("login"))

    for account in queryset.select_related("user"):
        # Approve the account first.
        account.status = "approved"
        account.save(update_fields=["status"])
        approved_count += 1

        # Record the approval without allowing a logging failure
        # to interrupt the rest of the approval process.
        try:
            AdminActivity.objects.create(
                admin_user=request.user,
                action="Account Approved",
                details=(
                    f"Approved account {account.account_number} "
                    f"for {account.user.username}."
                ),
            )
        except Exception:
            activity_failed_count += 1
            logger.exception(
                "Failed to record approval activity for account %s",
                account.account_number,
            )

        # A welcome email cannot be sent without a recipient address.
        if not account.user.email:
            email_failed_count += 1
            logger.warning(
                "No email address is registered for account %s",
                account.account_number,
            )
            continue

        message = (
            f"Dear {account.user.first_name or account.user.username},\n\n"
            "Welcome to MyBank International Finance.\n\n"
            "We are pleased to inform you that your account application "
            "has been reviewed and approved.\n\n"
            f"Account Number: {account.account_number}\n\n"
            "You can access your account using your account number "
            "and the password you created during registration.\n\n"
            f"Login: {login_url}\n\n"
            "Please keep your account information secure and never "
            "share your password with anyone.\n\n"
            "Thank you for choosing MyBank International Finance.\n\n"
            "Kind regards,\n"
            "MyBank International Finance\n"
            "Account Administration"
        )

        try:
            result = send_mail(
                subject="Welcome to MyBank International Finance",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[account.user.email],
                fail_silently=False,
            )

            if result == 1:
                email_sent_count += 1
            else:
                email_failed_count += 1
                logger.error(
                    "Welcome email was not accepted for account %s",
                    account.account_number,
                )

        except Exception:
            email_failed_count += 1
            logger.exception(
                "Failed to send welcome email for account %s",
                account.account_number,
            )

    if approved_count:
        messages.success(
            request,
            f"{approved_count} account(s) approved successfully.",
        )

    if email_sent_count:
        messages.success(
            request,
            f"Email server accepted {email_sent_count} welcome email(s) "
            "for sending.",
        )

    if email_failed_count:
        messages.warning(
            request,
            f"Welcome email failed for {email_failed_count} account(s). "
            "Check the Render logs for details.",
        )

    if activity_failed_count:
        messages.warning(
            request,
            f"Approval activity could not be recorded for "
            f"{activity_failed_count} account(s). Check the Render logs.",
        )
@admin.action(description="Reject selected accounts")
def reject_accounts(modeladmin, request, queryset):
    queryset.update(status="rejected")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):

    list_display = (
        "account_number",
        "user",
        "country",
        "account_type",
        "currency",
        "balance",
        "status",
    )

    list_filter = (
        "status",
        "account_type",
        "country",
        "currency",
    )

    search_fields = (
        "account_number",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )

    actions = [
        approve_accounts,
        reject_accounts,
        fund_account,
    ]
    
    
@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):

    list_display = (
        "reference_number",
        "account",
        "subject",
        "status",
        "created_at",
    )

    search_fields = (
        "reference_number",
        "subject",
        "account__user__username",
    )

    list_filter = (
        "status",
        "created_at",
    )
    ordering = (
        "-created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "reference_number",
        "subject",
        "message",
        "account__account_number",
        "account__user__username",
        "account__user__email",
    )

    readonly_fields = (
        "reference_number",
        "account",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):

    list_display = (
        "support_request",
        "sender",
        "message",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "support_request__reference_number",
        "sender__username",
        "sender__email",
        "message",
    )

    readonly_fields = (
        "sender",
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.sender = request.user

        super().save_model(
            request,
            obj,
            form,
            change
        )

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):

    list_display = (
        "bank_name",
        "support_email",
        "maintenance_mode",
        "updated_at",
    )

    readonly_fields = (
        "updated_at",
    )


from django.template.response import TemplateResponse


@admin.register(AdminActivity)
class AdminActivityAdmin(admin.ModelAdmin):

    list_display = (
        "admin_user",
        "action",
        "details",
        "created_at",
    )

    list_filter = (
        "created_at",
        "action",
    )

    search_fields = (
        "admin_user__username",
        "admin_user__email",
        "action",
        "details",
    )

    readonly_fields = (
        "admin_user",
        "created_at",
    )

    ordering = (
        "-created_at",
    )