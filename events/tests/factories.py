import itertools
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string

from events.models import Categorie, Evenement, Inscription

Utilisateur = get_user_model()
_compteur = itertools.count(1)


def creer_utilisateur(role=Utilisateur.Role.PARTICIPANT, **kwargs):
    n = next(_compteur)
    return Utilisateur.objects.create_user(
        username=kwargs.pop("username", f"user{n}"),
        email=kwargs.pop("email", f"user{n}@example.com"),
        password=get_random_string(20),
        role=role,
        **kwargs,
    )


def creer_gestionnaire(**kwargs):
    return creer_utilisateur(role=Utilisateur.Role.GESTIONNAIRE, **kwargs)


def creer_categorie(nom=None):
    nom = nom or f"Catégorie {next(_compteur)}"
    return Categorie.objects.create(nom=nom)


def creer_evenement(capacite=10, jours=7, createur=None, categorie=None, **kwargs):
    """`jours` négatif = événement passé (insertion directe, sans clean())."""
    return Evenement.objects.create(
        titre=kwargs.pop("titre", f"Événement {next(_compteur)}"),
        description=kwargs.pop("description", "Description"),
        date=kwargs.pop("date", timezone.now() + timedelta(days=jours)),
        lieu=kwargs.pop("lieu", "Antananarivo"),
        capacite=capacite,
        categorie=categorie or creer_categorie(),
        cree_par=createur or creer_gestionnaire(),
        **kwargs,
    )


def creer_inscription(participant, evenement, statut=Inscription.Statut.CONFIRMEE):
    return Inscription.objects.create(
        participant=participant, evenement=evenement, statut=statut
    )