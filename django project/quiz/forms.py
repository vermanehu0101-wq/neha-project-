from django import forms
from django.contrib.auth.models import User


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        min_length=8,
        help_text="Password must contain at least 8 characters.",
        widget=forms.PasswordInput,
        label="Password",
    )

    class Meta:
        model = User
        fields = ["username", "password"]
        labels = {"username": "Name"}

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
