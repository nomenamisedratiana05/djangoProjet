import csv

from django.contrib import messages
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from . import services
from .forms import EvenementForm
from .models import Evenement, Inscription
from .permissions import GestionnaireRequisMixin
from .services import InscriptionError


class GestionEvenementListView(GestionnaireRequisMixin, ListView):
    """Tous les événements (passés et à venir) pour le gestionnaire."""

    template_name = "evenements/gestion/liste.html"
    context_object_name = "evenements"
    paginate_by = 15

    def get_queryset(self):
        return (
            Evenement.objects.avec_stats()
            .select_related("categorie")
            .order_by("-date")
        )


class EvenementFormMixin(GestionnaireRequisMixin):
    """Comportement commun à la création et à la modification."""

    model = Evenement
    form_class = EvenementForm
    template_name = "evenements/gestion/formulaire.html"
    titre_page = ""
    message_succes = ""

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["titre_page"] = self.titre_page
        return contexte

    def form_valid(self, form):
        reponse = super().form_valid(form)
        messages.success(self.request, self.message_succes)
        return reponse

    def get_success_url(self):
        return reverse("evenements:detail", args=[self.object.pk])


class EvenementCreateView(EvenementFormMixin, CreateView):
    titre_page = "Créer un événement"
    message_succes = "L'événement a été créé."

    def form_valid(self, form):
        # Le créateur est toujours l'utilisateur connecté, jamais une donnée du formulaire.
        form.instance.cree_par = self.request.user
        return super().form_valid(form)


class EvenementUpdateView(EvenementFormMixin, UpdateView):
    titre_page = "Modifier l'événement"
    message_succes = "L'événement a été modifié."


class InscritsEvenementView(GestionnaireRequisMixin, DetailView):
    template_name = "evenements/gestion/inscrits.html"
    context_object_name = "evenement"

    def get_queryset(self):
        return Evenement.objects.avec_stats().select_related("categorie")

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        statut = self.request.GET.get("statut", "")

        inscriptions = (
            self.object.inscriptions.select_related("participant")
            .order_by("date_creation")
        )
        # Le filtre n'accepte que des statuts connus.
        if statut in Inscription.Statut.values:
            inscriptions = inscriptions.filter(statut=statut)
        else:
            statut = ""

        contexte["inscriptions"] = inscriptions
        contexte["statut"] = statut
        contexte["nb_annulees"] = self.object.inscriptions.filter(
            statut=Inscription.Statut.ANNULEE
        ).count()
        return contexte


def _proteger_csv(valeur):
    """
    Neutralise l'injection de formules : une cellule commençant par
    = + - @ serait exécutée par Excel ou LibreOffice.
    """
    valeur = str(valeur)
    if valeur and valeur[0] in "=+-@\t\r":
        return "'" + valeur
    return valeur


class ExportInscritsCSVView(GestionnaireRequisMixin, View):
    """Export en lecture seule : GET suffit."""

    def get(self, request, pk):
        evenement = get_object_or_404(Evenement, pk=pk)

        reponse = HttpResponse(content_type="text/csv; charset=utf-8")
        reponse["Content-Disposition"] = (
            f'attachment; filename="inscrits_evenement_{evenement.pk}.csv"'
        )
        reponse.write("\ufeff")  # BOM : accents corrects dans Excel
        ecrivain = csv.writer(reponse, delimiter=";")
        ecrivain.writerow(
            ["Nom d'utilisateur", "Prénom", "Nom", "E-mail", "Statut", "Date d'inscription"]
        )

        inscriptions = (
            evenement.inscriptions.select_related("participant")
            .order_by("date_creation")
        )
        for inscription in inscriptions:
            participant = inscription.participant
            ecrivain.writerow(
                [
                    _proteger_csv(participant.username),
                    _proteger_csv(participant.first_name),
                    _proteger_csv(participant.last_name),
                    _proteger_csv(participant.email),
                    inscription.get_statut_display(),
                    timezone.localtime(inscription.date_creation).strftime("%d/%m/%Y %H:%M"),
                ]
            )
        return reponse


class AnnulerInscriptionGestionnaireView(GestionnaireRequisMixin, View):
    """Traitement gestionnaire : confirmation (GET), puis annulation (POST)."""

    template_name = "evenements/gestion/confirmer.html"

    def get_inscription(self, pk):
        return get_object_or_404(
            Inscription.objects.select_related("evenement", "participant"),
            pk=pk,
        )

    def get(self, request, pk):
        inscription = self.get_inscription(pk)
        if not inscription.est_annulable:
            messages.error(request, "Cette inscription ne peut plus être annulée.")
            return redirect("evenements:inscrits", pk=inscription.evenement_id)
        return render(
            request,
            self.template_name,
            {
                "titre": "Annuler cette inscription ?",
                "message": (
                    f"L'inscription de {inscription.participant} à "
                    f"« {inscription.evenement.titre} » sera annulée "
                    f"et la place libérée."
                ),
                "bouton": "Oui, annuler l'inscription",
                "retour_url": reverse(
                    "evenements:inscrits", args=[inscription.evenement_id]
                ),
            },
        )

    def post(self, request, pk):
        inscription = self.get_inscription(pk)
        try:
            services.annuler_par_gestionnaire(inscription, request.user)
        except InscriptionError as erreur:
            messages.error(request, str(erreur))
        else:
            messages.success(
                request, f"L'inscription de {inscription.participant} a été annulée."
            )
        return redirect("evenements:inscrits", pk=inscription.evenement_id)

class EvenementSupprimerView(GestionnaireRequisMixin, View):
    template_name = "evenements/gestion/confirmer.html"

    MESSAGE_REFUS = (
        "Suppression impossible : cet événement a des inscriptions "
        "(confirmées ou annulées)."
    )

    def get(self, request, pk):
        evenement = get_object_or_404(Evenement, pk=pk)
        if not evenement.peut_etre_supprime:
            messages.error(request, self.MESSAGE_REFUS)
            return redirect("evenements:gestion_liste")
        return render(
            request,
            self.template_name,
            {
                "titre": "Supprimer cet événement ?",
                "message": f"« {evenement.titre} » sera supprimé définitivement.",
                "bouton": "Oui, supprimer",
                "retour_url": reverse("evenements:gestion_liste"),
            },
        )

    def post(self, request, pk):
        evenement = get_object_or_404(Evenement, pk=pk)
        if not evenement.peut_etre_supprime:
            messages.error(request, self.MESSAGE_REFUS)
            return redirect("evenements:gestion_liste")
        try:
            evenement.delete()
        except ProtectedError:
            # Filet de sécurité si une inscription est apparue entre-temps.
            messages.error(request, self.MESSAGE_REFUS)
        else:
            messages.success(request, "L'événement a été supprimé.")
        return redirect("evenements:gestion_liste")

class TableauDeBordView(GestionnaireRequisMixin, TemplateView):
    template_name = "evenements/gestion/tableau_de_bord.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)

        a_venir = list(
            Evenement.objects.a_venir().avec_stats().select_related("categorie")
        )
        capacite_totale = sum(e.capacite for e in a_venir)
        inscrits_total = sum(e.nombre_inscrits for e in a_venir)

        contexte.update(
            {
                "nb_evenements": Evenement.objects.count(),
                "nb_a_venir": len(a_venir),
                "nb_inscriptions_confirmees": Inscription.objects.filter(
                    statut=Inscription.Statut.CONFIRMEE
                ).count(),
                "taux_global": (
                    round(100 * inscrits_total / capacite_totale)
                    if capacite_totale
                    else 0
                ),
                "evenements": a_venir,
            }
        )
        return contexte