from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from . import services
from .forms import RechercheEvenementForm
from .models import Evenement, Inscription
from .services import InscriptionError


class EvenementListView(ListView):
    template_name = "evenements/liste.html"
    context_object_name = "evenements"
    paginate_by = 9

    def get_queryset(self):
        self.form = RechercheEvenementForm(self.request.GET or None)
        qs = (
            Evenement.objects.a_venir()
            .avec_stats()
            .select_related("categorie")
        )
        if self.form.is_valid():
            categorie = self.form.cleaned_data["categorie"]
            qs = qs.recherche(
                terme=self.form.cleaned_data["q"],
                categorie_id=categorie.pk if categorie else None,
            )
        return qs

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["form"] = self.form
        # Conserve la recherche et le filtre dans les liens de pagination.
        params = self.request.GET.copy()
        params.pop("page", None)
        contexte["querystring"] = params.urlencode()
        return contexte

class EvenementDetailView(DetailView):
    template_name = "evenements/detail.html"
    context_object_name = "evenement"

    def get_queryset(self):
        return (
            Evenement.objects.avec_stats()
            .select_related("categorie", "cree_par")
        )

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        utilisateur = self.request.user
        contexte["inscription"] = None
        if utilisateur.is_authenticated:
            contexte["inscription"] = Inscription.objects.filter(
                participant=utilisateur, evenement=self.object
            ).first()
        return contexte

class InscrireView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        evenement = get_object_or_404(Evenement, pk=pk)
        try:
            services.inscrire(request.user, evenement)
        except InscriptionError as erreur:
            messages.error(request, str(erreur))
        else:
            messages.success(
                request, f"Votre inscription à « {evenement.titre} » est confirmée."
            )
        return redirect("evenements:detail", pk=evenement.pk)

class MesInscriptionsView(LoginRequiredMixin, ListView):
    template_name = "evenements/mes_inscriptions.html"
    context_object_name = "inscriptions"
    paginate_by = 10

    def get_queryset(self):
        # Filtre strict sur l'utilisateur connecté.
        return (
            Inscription.objects.filter(participant=self.request.user)
            .select_related("evenement", "evenement__categorie")
            .order_by("-evenement__date")
        )

class AnnulerInscriptionView(LoginRequiredMixin, View):
    template_name = "evenements/confirmer_annulation.html"

    def get_inscription(self, request, pk):
        # 404 si l'inscription appartient à quelqu'un d'autre :
        # on ne révèle même pas son existence.
        return get_object_or_404(
            Inscription.objects.select_related("evenement"),
            pk=pk,
            participant=request.user,
        )

    def get(self, request, pk):
        inscription = self.get_inscription(request, pk)
        if not inscription.est_annulable:
            messages.error(request, "Cette inscription ne peut plus être annulée.")
            return redirect("evenements:mes_inscriptions")
        return render(request, self.template_name, {"inscription": inscription})

    def post(self, request, pk):
        inscription = self.get_inscription(request, pk)
        try:
            services.annuler(inscription, request.user)
        except InscriptionError as erreur:
            messages.error(request, str(erreur))
        else:
            messages.success(request, "Votre inscription a été annulée.")
        return redirect("evenements:mes_inscriptions")