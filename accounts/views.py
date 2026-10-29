from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import ConnexionForm, InscriptionForm


class ConnexionView(LoginView):
    template_name = "accounts/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Bienvenue, {form.get_user()} !")
        return super().form_valid(form)


class InscriptionView(CreateView):
    form_class = InscriptionForm
    template_name = "accounts/inscription.html"
    success_url = reverse_lazy("evenements:liste")

    def dispatch(self, request, *args, **kwargs):
        # Un utilisateur déjà connecté n'a pas besoin de s'inscrire.
        if request.user.is_authenticated:
            return redirect("evenements:liste")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        reponse = super().form_valid(form)
        # Connexion automatique après la création du compte.
        login(
            self.request,
            self.object,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        messages.success(
            self.request, "Votre compte a été créé. Bienvenue sur EventHub !"
        )
        return reponse