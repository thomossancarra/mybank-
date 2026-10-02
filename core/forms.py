import uuid
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from babel import Locale

COUNTRIES = [
    (code, Locale("en").territories.get(code, code))
    for code in Locale("en").territories
    if len(code) == 2
]

class SignUpForm(UserCreationForm):
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists. "
                "Please use another email address."
            )

        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].required = False
        self.fields["username"].widget = forms.HiddenInput()

    def clean_username(self):
        return f"customer_{uuid.uuid4().hex[:12]}" 
      
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    middle_name = forms.CharField(
         
        max_length=150,
        required=True,
        label="Middle Name"
    )

    phone_number = forms.CharField(
        max_length=30,
        required=True,
        label="Phone Number"
    )

    email = forms.EmailField(

        required=True,
        label="Email Address"
    )

    country = forms.ChoiceField(
        choices=COUNTRIES,
        required=True,
        label="Country"
    ) 
    state = forms.CharField(
        max_length=100,
        required=True,
        label="State / Province / Region"
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True
    )

    account_type = forms.ChoiceField(
        choices=[
            ("savings", "Savings"),
            ("current", "Current"),
        ],
        required=True
    )

    profile_photo = forms.ImageField(required=False)

class Meta:
        model = User
        fields = (
            "first_name",
            "middle_name",
            "last_name",
            "phone_number",
            "email",
            "username",
            "password1",
            "password2",
        )


class DepositForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        label="Deposit Amount"
    )