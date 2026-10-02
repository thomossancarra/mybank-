from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import random
from datetime import timedelta
from io import BytesIO
from django.http import FileResponse
from decimal import Decimal, InvalidOperation
import requests
from babel.numbers import get_territory_currencies

from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .forms import SignUpForm
from .models import (
    Account,
    Transaction,
    Notification,
    TransferOTP,
    SupportRequest,
    SupportMessage,
    SystemSettings,
)


def get_local_currency_amount(usd_amount, currency):
    if currency == "USD":
        return usd_amount

    try:
        response = requests.get(
            f"https://api.frankfurter.dev/v2/rate/usd/{currency}",
            timeout=5
        )

        response.raise_for_status()

        rate = Decimal(str(response.json()["rate"]))

        return usd_amount * rate

    except (requests.RequestException, KeyError, ValueError):
        return None


def home(request):
    settings = SystemSettings.objects.first()

    if settings and settings.maintenance_mode:
        return render(
            request,
            "core/maintenance.html",
            {
                "settings": settings,
            },
        )

    return render(request, "core/home.html")


def register(request):
    if request.method == "POST":
        form = SignUpForm(request.POST, request.FILES)

        if form.is_valid():
            user = form.save(commit=False)

            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]

            user.save()

            country_code = form.cleaned_data["country"]

            currencies = get_territory_currencies(
                country_code,
                tender=True
            )

            currency = currencies[0] if currencies else "USD"

            account = Account.objects.create(
                user=user,
                country=form.cleaned_data["country"],
                currency=currency,
                state=form.cleaned_data["state"],
                middle_name=form.cleaned_data["middle_name"],
                phone_number=form.cleaned_data["phone_number"],
                address=form.cleaned_data["address"],
                account_type=form.cleaned_data["account_type"],
                profile_photo=form.cleaned_data.get("profile_photo"),
                status="pending",
            )

            return render(
                request,
                "core/application_submitted.html",
                {
                    "account_number": account.account_number,
                }
            )
            

            login(request, user)
            return redirect("dashboard")
            
            
    else:
        form = SignUpForm()

    return render(request, "core/register.html", {"form": form})

@login_required
def dashboard(request):
    account, created = Account.objects.get_or_create(
        user=request.user
    )

    local_amount = get_local_currency_amount(
        account.balance,
        account.currency
    )

    return render(
        request,
        "core/dashboard.html",
        {
            "account": account,
            "local_amount": local_amount,
        }
    )

@login_required
def deposit(request):
    messages.error(
        request,
        "Deposits are handled by MyBank Account Administration."
    )
    return redirect("dashboard")
                

@login_required
def withdraw(request):
    messages.error(
        request,
        "Withdrawals are currently handled by MyBank Account Administration."
    )
    return redirect("dashboard")

            
from django.contrib.auth.models import User
from django.db import transaction


@login_required
def transfer(request):
    account, created = Account.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        account_number = request.POST.get("account_number", "").strip()
        amount_text = request.POST.get("amount", "").strip()

        try:
            amount = Decimal(amount_text)
        except (ValueError, InvalidOperation):
            return render(
                request,
                "core/transfer.html",
                {
                    "account": account,
                    "error": "Please enter a valid amount."
                }
            )

        if amount <= 0:
            return render(
                request,
                "core/transfer.html",
                {
                    "account": account,
                    "error": "Please enter a valid amount."
                }
            )

        if amount > account.balance:
            return render(
                request,
                "core/transfer.html",
                {
                    "account": account,
                    "error": "Insufficient balance."
                }
            )

        try:
            recipient_account = Account.objects.get(
                account_number=account_number
            )
        except Account.DoesNotExist:
            return render(
                request,
                "core/transfer.html",
                {
                    "account": account,
                    "error": "Recipient account number not found."
                }
            )

        recipient = recipient_account.user

        if recipient == request.user:
            return render(
                request,
                "core/transfer.html",
                {
                    "account": account,
                    "error": "You cannot transfer money to yourself."
                }
            )

        # Get recipient's name
        recipient_name = (
            f"{recipient.first_name} "
            f"{getattr(recipient_account, 'middle_name', '')} "
            f"{recipient.last_name}"
        ).strip()

        # Confirmation stage
        if request.POST.get("confirm_transfer") == "yes":

            # Generate a secure 6-digit OTP
            otp_code = str(random.randint(100000, 999999))

            # OTP expires in 10 minutes
            expires_at = timezone.now() + timedelta(minutes=10)

            # Remove previous unused OTPs
            TransferOTP.objects.filter(
                account=account,
                verified=False
            ).delete()

            # Save the pending transfer
            TransferOTP.objects.create(
                account=account,
                recipient_account=recipient_account,
                amount=amount,
                code=otp_code,
                expires_at=expires_at
            )

            # Send OTP to sender's registered email
            send_mail(
                "MyBank Transfer Verification Code",
                (
                    f"Hello {request.user.first_name},\n\n"
                    f"Your MyBank transfer verification code is: {otp_code}\n\n"
                    f"Transfer amount: ${amount:,.2f} USD\n"
                    f"Recipient account: "
                    f"{recipient_account.account_number}\n\n"
                    "This code expires in 10 minutes.\n"
                    "Do not share this code with anyone.\n\n"
                    "MyBank Security Team"
                ),
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )

            return render(
                request,
                "core/transfer_otp.html",
                {
                    "amount": amount,
                    "recipient_name": recipient_name,
                    "recipient_account_number": (
                        recipient_account.account_number
                    ),
                }
            )

        # Show recipient details before money is moved
        return render(
            request,
            "core/transfer_confirm.html",
            {
                "recipient_name": recipient_name,
                "recipient_account_number": (
                    recipient_account.account_number
                ),
                "amount": amount,
            }
        )

    return render(
        request,
        "core/transfer.html",
        {
            "account": account
        }
    )

@login_required
def transactions(request):
    account, created = Account.objects.get_or_create(
        user=request.user
    )

    transactions = account.transactions.all().order_by("-created_at")

    return render(
        request,
        "core/transactions.html",
        {
            "account": account,
            "transactions": transactions,
        }
    )

def mybank_login(request):
    if request.method == "POST":
        account_number = request.POST.get("account_number")
        password = request.POST.get("password")

        try:
            account = Account.objects.get(
                account_number=account_number
            )
        except Account.DoesNotExist:
            return render(
                request,
                "core/login.html",
                {"error": "Invalid account number or password."}
            )

        user = authenticate(
            request,
            username=account.user.username,
            password=password
        )

        if user is not None:

            if account.status == "pending":
                return render(
                    request,
                    "core/login.html",
                    {
                        "error": "Your account application is still pending approval."
                    }
                )

            if account.status == "rejected":
                return render(
                    request,
                    "core/login.html",
                    {
                        "error": "Your account application was not approved. Please contact MyBank support."
                    }
                )

            login(request, user)
            return redirect("dashboard")

        return render(
            request,
            "core/login.html",
            {"error": "Invalid account number or password."}
        )

    return render(request, "core/login.html")

@login_required
def profile(request):
    account = Account.objects.get(user=request.user)

    return render(
        request,
        "core/profile.html",
        {"account": account}
    )

@login_required
def statement(request):
    account = Account.objects.get(user=request.user)

    transactions = account.transactions.all().order_by("-created_at")

    return render(
        request,
        "core/statement.html",
        {
            "account": account,
            "transactions": transactions,
        }
    )


@login_required
def download_statement(request):
    account = Account.objects.get(user=request.user)

    transactions = account.transactions.all().order_by("-created_at")

    buffer = BytesIO()

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    pdf.setTitle("MyBank Account Statement")

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, height - 60, "MyBank")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, height - 82, "Account Statement")

    y = height - 125

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Account Holder:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        150,
        y,
        f"{account.user.first_name} {account.middle_name} {account.user.last_name}"
    )

    y -= 20
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Account Number:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(150, y, account.account_number)

    y -= 20
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Account Type:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(150, y, account.get_account_type_display())

    y -= 20
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Current Balance:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        150,
        y,
        f"${account.balance:,.2f} USD"
    )

    y -= 40

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Date")
    pdf.drawString(145, y, "Type")
    pdf.drawString(245, y, "Description")
    pdf.drawString(470, y, "Amount")

    y -= 20

    pdf.setFont("Helvetica", 9)

    for transaction in transactions:

        if y < 60:
            pdf.showPage()
            y = height - 60

            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(50, y, "Date")
            pdf.drawString(145, y, "Type")
            pdf.drawString(245, y, "Description")
            pdf.drawString(470, y, "Amount")

            y -= 20
            pdf.setFont("Helvetica", 9)

        date = transaction.created_at.strftime("%Y-%m-%d")
        transaction_type = transaction.get_transaction_type_display()
        description = transaction.description[:35]
        amount = f"${transaction.amount:,.2f}"

        pdf.drawString(50, y, date)
        pdf.drawString(145, y, transaction_type)
        pdf.drawString(245, y, description)
        pdf.drawString(470, y, amount)

        y -= 18

    pdf.save()

    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename="mybank_account_statement.pdf",
        content_type="application/pdf",
    )

@login_required
def change_password(request):
    if request.method == "POST":
        from django.contrib.auth.forms import PasswordChangeForm

        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(
                request,
                "Your password has been changed successfully."
            )

            return redirect("profile")

    else:
        from django.contrib.auth.forms import PasswordChangeForm

        form = PasswordChangeForm(request.user)

    return render(
        request,
        "core/change_password.html",
        {"form": form}
    )

@login_required
def account_settings(request):
    account = Account.objects.get(user=request.user)

    return render(
        request,
        "core/account_settings.html",
        {"account": account}
    )

@login_required
def notifications(request):
    account = Account.objects.get(user=request.user)

    notification_list = account.notifications.all().order_by("-created_at")

    return render(
        request,
        "core/notifications.html",
        {
            "notifications": notification_list,
        }
    )

@login_required
def verify_transfer_otp(request):
    account = Account.objects.get(user=request.user)

    otp_record = (
        TransferOTP.objects
        .filter(
            account=account,
            verified=False
        )
        .order_by("-created_at")
        .first()
    )

    if not otp_record:
        messages.error(
            request,
            "No pending transfer verification was found."
        )
        return redirect("transfer")

    if request.method == "POST":

        entered_code = request.POST.get("otp", "").strip()

        # Check whether the OTP has expired
        if timezone.now() > otp_record.expires_at:
            otp_record.delete()

            messages.error(
                request,
                "This verification code has expired. "
                "Please start the transfer again."
            )

            return redirect("transfer")

        # Check the OTP
        if entered_code != otp_record.code:
            return render(
                request,
                "core/transfer_otp.html",
                {
                    "amount": otp_record.amount,
                    "recipient_name": (
                        f"{otp_record.recipient_account.user.first_name} "
                        f"{otp_record.recipient_account.user.last_name}"
                    ).strip(),
                    "recipient_account_number": (
                        otp_record.recipient_account.account_number
                    ),
                    "error": "Invalid verification code. Please try again."
                }
            )

        # OTP is correct — now move the money
        with transaction.atomic():

            sender_account = Account.objects.select_for_update().get(
                pk=account.pk
            )

            recipient_account = Account.objects.select_for_update().get(
                pk=otp_record.recipient_account.pk
            )

            amount = otp_record.amount

            # Final balance check
            if amount > sender_account.balance:
                otp_record.delete()

                messages.error(
                    request,
                    "Insufficient balance. The transfer was not completed."
                )

                return redirect("transfer")

            sender = sender_account.user
            recipient = recipient_account.user

            sender_name = (
                f"{sender.first_name} "
                f"{getattr(sender_account, 'middle_name', '')} "
                f"{sender.last_name}"
            ).strip()

            recipient_name = (
                f"{recipient.first_name} "
                f"{getattr(recipient_account, 'middle_name', '')} "
                f"{recipient.last_name}"
            ).strip()

            sender_account.balance = (
                Decimal(str(sender_account.balance)) - amount
            )
            sender_account.save()

            recipient_account.balance = (
                Decimal(str(recipient_account.balance)) + amount
            )
            recipient_account.save()

            Transaction.objects.create(
                account=sender_account,
                transaction_type="transfer",
                amount=amount,
                description=f"Transfer to {recipient_name}"
            )

            Transaction.objects.create(
                account=recipient_account,
                transaction_type="transfer",
                amount=amount,
                description=f"Transfer from {sender_name}"
            )

            Notification.objects.create(
                account=recipient_account,
                title="Transfer Received",
                message=(
                    f"You have received ${amount:,.2f} USD "
                    f"from {sender_name}."
                )
            )

            otp_record.verified = True
            otp_record.save()

        messages.success(
            request,
            f"Transfer of ${amount:,.2f} USD to "
            f"{recipient_name} was successful!"
        )

        return redirect("dashboard")

    return render(
        request,
        "core/transfer_otp.html",
        {
            "amount": otp_record.amount,
            "recipient_name": (
                f"{otp_record.recipient_account.user.first_name} "
                f"{otp_record.recipient_account.user.last_name}"
            ).strip(),
            "recipient_account_number": (
                otp_record.recipient_account.account_number
            ),
        }
    )

@login_required
def external_transfer_verification(request):

    if request.method != "POST":
        return redirect("transfer")

    transfer_type = request.POST.get(
        "transfer_type",
        "External Bank Transfer"
    )

    return render(
        request,
        "core/transfer_verification.html",
        {
            "transfer_type": transfer_type,
        }
    )




@login_required
def support(request):

    account, created = Account.objects.get_or_create(
        user=request.user
    )
    if request.method == "POST":
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()
        if not subject or not message:
            return render(
                request,
                "core/support.html",
                {
                    "account": account,
                    "error": "Please select a subject and enter your message."
                }
            )
        reference_number = (
            f"MB-{timezone.now().strftime('%Y%m%d')}-"
            f"{random.randint(1000, 9999)}"
        )

        SupportRequest.objects.create(
            account=account,
            reference_number=reference_number,
            subject=subject,
            message=message,
        )
        support_message = (
            "MyBank Support Request\n\n"
            f"Reference Number: {reference_number}\n\n"
            f"Account Holder: "
            f"{request.user.first_name} {request.user.last_name}\n"
            f"Account Number: {account.account_number}\n"
            f"Registered Email: {request.user.email}\n\n"
            f"Subject: {subject}\n\n"
            "Message:\n"
            f"{message}\n\n"
            "MyBank Support Team"
        )
        send_mail(
            f"MyBank Support Request [{reference_number}] - {subject}",
            support_message,
            settings.DEFAULT_FROM_EMAIL,
            ["support@mybank.com"],
            fail_silently=False,
        )
        return render(
            request,
            "core/support_success.html",
            {
                "reference_number": reference_number,
            }
        )
    return render(
        request,
        "core/support.html",
        {
            "account": account,
            "system_settings": SystemSettings.objects.first(),
        }
    )


@login_required
def support_center(request):

    account, created = Account.objects.get_or_create(
        user=request.user
    )

    support_requests = (
        SupportRequest.objects
        .filter(account=account)
        .order_by("-created_at")
    )

    return render(
        request,
        "core/support_center.html",
        {
            "account": account,
            "support_requests": support_requests,
        }
    )

@login_required
def support_detail(request, reference_number):

    account = Account.objects.get(
        user=request.user
    )

    support_request = get_object_or_404(
        SupportRequest,
        reference_number=reference_number,
        account=account,
    )

    support_messages = (
        support_request.messages
        .select_related("sender")
        .order_by("created_at")
    )

    if request.method == "POST":

        message = request.POST.get(
            "message",
            ""
        ).strip()

        if not message:
            return render(
                request,
                "core/support_detail.html",
                {
                    "account": account,
                    "support_request": support_request,
                    "support_messages": support_messages,
                    "error": "Please enter a message.",
                }
            )

        SupportMessage.objects.create(
            support_request=support_request,
            sender=request.user,
            message=message,
        )

        if support_request.status == "Received":
            support_request.status = "In Progress"
            support_request.save(
                update_fields=["status"]
            )

        return redirect(
            "support_detail",
            reference_number=reference_number
        )

    return render(
        request,
        "core/support_detail.html",
        {
            "account": account,
            "support_request": support_request,
            "support_messages": support_messages,
        }
    )

from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse


@staff_member_required
def system_overview(request):

    context = {
        "total_customers": Account.objects.count(),

        "approved_accounts": Account.objects.filter(
            status="approved"
        ).count(),

        "pending_accounts": Account.objects.filter(
            status="pending"
        ).count(),

        "total_transactions": Transaction.objects.count(),

        "support_requests": SupportRequest.objects.count(),

        "open_support_requests": SupportRequest.objects.exclude(
            status__in=["Resolved", "Closed"]
        ).count(),
    }

    return TemplateResponse(
        request,
        "admin/system_overview.html",
        context,
    )