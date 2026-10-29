from django.db import transaction
from django.utils import timezone

from .models import Evenement, Inscription


class InscriptionError(Exception):
    """Erreur métier affichable à l'utilisateur."""


@transaction.atomic
def inscrire(utilisateur, evenement):
    # Verrouille la ligne de l'événement (effectif sur PostgreSQL/MySQL,
    # sans effet sur SQLite qui sérialise déjà les écritures).
    evenement = Evenement.objects.select_for_update().get(pk=evenement.pk)

    if not evenement.est_a_venir:
        raise InscriptionError("Cet événement est déjà commencé ou terminé.")

    inscription = Inscription.objects.filter(
        participant=utilisateur, evenement=evenement
    ).first()

    if inscription and inscription.est_confirmee:
        raise InscriptionError("Vous êtes déjà inscrit à cet événement.")

    # La capacité est vérifiée AVANT de créer ou réactiver l'inscription.
    if evenement.est_complet:
        raise InscriptionError("Cet événement a atteint sa capacité maximale.")

    if inscription is None:
        inscription = Inscription(participant=utilisateur, evenement=evenement)

    inscription.statut = Inscription.Statut.CONFIRMEE
    inscription.date_annulation = None
    inscription.save()
    return inscription


@transaction.atomic
def _marquer_annulee(inscription):
    """Règle commune : passe l'inscription à « annulée »."""
    if not inscription.est_confirmee:
        raise InscriptionError("Cette inscription est déjà annulée.")
    if not inscription.evenement.est_a_venir:
        raise InscriptionError("Impossible d'annuler : l'événement a commencé.")

    inscription.statut = Inscription.Statut.ANNULEE
    inscription.date_annulation = timezone.now()
    inscription.save()
    return inscription


@transaction.atomic
def annuler(inscription, utilisateur):
    """Annulation par le participant lui-même."""
    if inscription.participant_id != utilisateur.pk:
        raise InscriptionError("Vous ne pouvez pas annuler cette inscription.")
    return _marquer_annulee(inscription)


@transaction.atomic
def annuler_par_gestionnaire(inscription, gestionnaire):
    """Annulation d'une inscription par un gestionnaire."""
    if not gestionnaire.est_gestionnaire:
        raise InscriptionError("Action réservée aux gestionnaires.")
    return _marquer_annulee(inscription)