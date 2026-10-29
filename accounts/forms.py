from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Utilisateur


class InscriptionForm(UserCreationForm):
    """Formulaire de création de compte. Le rôle n'est PAS modifiable ici."""

    class Meta:
        model = Utilisateur
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        for champ in self.fields.values():
            champ.widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Utilisateur.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Un compte existe déjà avec cette adresse e-mail."
            )
        return email

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        # Sécurité : le rôle est toujours forcé à participant.
        utilisateur.role = Utilisateur.Role.PARTICIPANT
        if commit:
            utilisateur.save()
        return utilisateur


class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion avec classes Bootstrap."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.widget.attrs["class"] = "form-control"