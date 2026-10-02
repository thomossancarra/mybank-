from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from core.views import (
    home,
    register,
    dashboard,
    deposit,
    withdraw,
    transfer,
    transactions,
    mybank_login,
    profile,
    statement,
    download_statement,
    change_password,
    account_settings,
    notifications,
    verify_transfer_otp,
    external_transfer_verification,
    support,
    support_center,
    support_detail,
    system_overview,
)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path(
        "admin/system-overview/",
        system_overview,
        name="system_overview"
    ),
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("register/", register, name="register"),
    path("login/", mybank_login, name="login"),
    path(
        "password-reset/",
        PasswordResetView.as_view(
            template_name="core/password_reset.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        PasswordResetDoneView.as_view(
            template_name="core/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="core/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),

    path(
    "reset/done/",
    PasswordResetCompleteView.as_view(
        template_name="core/password_reset_complete.html"
    ),
    name="password_reset_complete",
),
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/", profile, name="profile"),
    path("account-settings/", account_settings, name="account_settings"),
    path("notifications/", notifications, name="notifications"),
    path("statement/", statement, name="statement"),
    path(
        "transfer/verification/",
        external_transfer_verification,
        name="external_transfer_verification"
    ),
    path(
        "support/",
        support,
        name="support"
    ),

    path(
        "support/center/",
        support_center,
        name="support_center"
    ),
    path(
        "support/<str:reference_number>/",
        support_detail,
        name="support_detail"
    ),
    path("statement/download/", download_statement, name="download_statement"),
    path("deposit/", deposit, name="deposit"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("withdraw/", withdraw, name="withdraw"),
    path("transfer/", transfer, name="transfer"),
    path(
      "transfer/verify/",
      verify_transfer_otp,
      name="verify_transfer_otp"
    ),
    path("transactions/", transactions, name="transactions"),
    path("change-password/", change_password, name="change_password"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)