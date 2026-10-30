import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string

from events import services
from events.models import Categorie, Evenement, Inscription

Utilisateur = get_user_model()

VARIABLE_MOT_DE_PASSE = "EVENTHUB_DEMO_PASSWORD"

GESTIONNAIRE = ("demo_organisateur", "Olivier", "Rabe")

PARTICIPANTS = [
    ("demo_alice", "Alice", "Rakoto"),
    ("demo_bob", "Bob", "Randria"),
    ("demo_claire", "Claire", "Rasoamanana"),
    ("demo_david", "David", "Andrianjafy"),
    ("demo_emma", "Emma", "Razafy"),
]

CATEGORIES = [
    ("Atelier", "Sessions pratiques pour apprendre en faisant."),
    ("Conférence", "Présentations et échanges avec des intervenants."),
    ("Rencontre", "Moments de convivialité et de réseautage."),
]

# jours : décalage par rapport à aujourd'hui (négatif = événement passé)
EVENEMENTS = [
    {
        "titre": "Atelier : initiation à Django",
        "categorie": "Atelier",
        "jours": 5,
        "heure": 14,
        "lieu": "Salle informatique B",
        "capacite": 20,
        "description": "Construisez votre première application web avec Django, "
        "des modèles jusqu'aux templates. Apportez votre ordinateur.",
        "inscrits": ["demo_alice", "demo_bob", "demo_david"],
        "annules": ["demo_emma"],
    },
    {
        "titre": "Conférence : intelligence artificielle et société",
        "categorie": "Conférence",
        "jours": 12,
        "heure": 9,
        "lieu": "Amphithéâtre principal",
        "capacite": 100,
        "description": "Panorama des usages de l'IA et débat sur ses enjeux "
        "éthiques, économiques et éducatifs.",
        "inscrits": ["demo_bob", "demo_claire", "demo_david", "demo_emma"],
        "annules": [],
    },
    {
        "titre": "Rencontre des anciens étudiants",
        "categorie": "Rencontre",
        "jours": 20,
        "heure": 17,
        "lieu": "Jardin de l'université",
        "capacite": 40,
        "description": "Retrouvailles, partage d'expériences professionnelles "
        "et buffet convivial.",
        "inscrits": ["demo_alice"],
        "annules": [],
    },
    {
        "titre": "Atelier : Git et GitHub en équipe",
        "categorie": "Atelier",
        "jours": 8,
        "heure": 10,
        "lieu": "Salle informatique A",
        "capacite": 3,  # volontairement petit : l'événement sera complet
        "description": "Branches, pull requests et résolution de conflits. "
        "Places très limitées.",
        "inscrits": ["demo_alice", "demo_bob", "demo_claire"],
        "annules": ["demo_david"],
    },
    {
        "titre": "Conférence : cybersécurité pour tous",
        "categorie": "Conférence",
        "jours": 30,
        "heure": 15,
        "lieu": "Salle de conférence 2",
        "capacite": 60,
        "description": "Les bonnes pratiques pour protéger ses comptes et ses "
        "données au quotidien.",
        "inscrits": [],  # aucun inscrit : permet de démontrer la suppression
        "annules": [],
    },
    {
        "titre": "Rencontre de rentrée (terminée)",
        "categorie": "Rencontre",
        "jours": -10,
        "heure": 16,
        "lieu": "Hall d'accueil",
        "capacite": 15,
        "description": "Événement passé, conservé pour montrer l'état « Terminé ».",
        "inscrits": ["demo_alice", "demo_claire"],
        "annules": [],
    },
]


def _date(jours, heure):
    base = timezone.localtime() + timedelta(days=jours)
    return base.replace(hour=heure, minute=0, second=0, microsecond=0)


class Command(BaseCommand):
    help = (
        "Crée des données de démonstration : catégories, événements, "
        "un gestionnaire, des participants et des inscriptions."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime d'abord les données de démonstration "
            "(comptes demo_*, leurs événements et inscriptions), puis les recrée.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._supprimer_donnees_demo()
            self.stdout.write("Anciennes données de démonstration supprimées.")

        mot_de_passe, depuis_env = self._mot_de_passe()
        utilisateurs, nouveaux = self._creer_comptes(mot_de_passe)
        categories = self._creer_categories()
        nb_evenements = self._creer_evenements(
            utilisateurs[GESTIONNAIRE[0]], categories, utilisateurs
        )

        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes."))
        self.stdout.write(f"  Catégories : {len(categories)}")
        self.stdout.write(f"  Événements créés : {nb_evenements}")
        self.stdout.write(f"  Comptes créés : {len(nouveaux)}")
        self.stdout.write("")
        self.stdout.write(f"  Gestionnaire : {GESTIONNAIRE[0]}")
        self.stdout.write(
            "  Participants : " + ", ".join(p[0] for p in PARTICIPANTS)
        )

        if not nouveaux:
            self.stdout.write(
                "\nTous les comptes existaient déjà : leurs mots de passe sont "
                "inchangés. Utilisez --reset pour tout recréer."
            )
        elif depuis_env:
            self.stdout.write(
                f"\nMot de passe des comptes créés : valeur de {VARIABLE_MOT_DE_PASSE}."
            )
        else:
            self.stdout.write(f"\nMot de passe généré : {mot_de_passe}")
            self.stdout.write(
                "(affiché une seule fois, commun aux comptes créés "
                "pendant cette exécution)"
            )

    # ------------------------------------------------------------------
    def _mot_de_passe(self):
        valeur = os.environ.get(VARIABLE_MOT_DE_PASSE, "").strip()
        if valeur:
            return valeur, True
        return get_random_string(16), False

    def _supprimer_donnees_demo(self):
        noms = [GESTIONNAIRE[0]] + [p[0] for p in PARTICIPANTS]
        utilisateurs = Utilisateur.objects.filter(username__in=noms)
        evenements = Evenement.objects.filter(cree_par__in=utilisateurs)
        # Ordre imposé par les clés étrangères en PROTECT.
        Inscription.objects.filter(
            Q(evenement__in=evenements) | Q(participant__in=utilisateurs)
        ).delete()
        evenements.delete()
        utilisateurs.delete()

    def _creer_comptes(self, mot_de_passe):
        comptes = [(GESTIONNAIRE, Utilisateur.Role.GESTIONNAIRE)] + [
            (p, Utilisateur.Role.PARTICIPANT) for p in PARTICIPANTS
        ]
        utilisateurs, nouveaux = {}, []
        for (username, prenom, nom), role in comptes:
            utilisateur = Utilisateur.objects.filter(username=username).first()
            if utilisateur is None:
                utilisateur = Utilisateur.objects.create_user(
                    username=username,
                    email=f"{username}@demo.example.com",
                    password=mot_de_passe,
                    first_name=prenom,
                    last_name=nom,
                    role=role,
                )
                nouveaux.append(username)
            utilisateurs[username] = utilisateur
        return utilisateurs, nouveaux

    def _creer_categories(self):
        categories = {}
        for nom, description in CATEGORIES:
            categorie, _ = Categorie.objects.get_or_create(
                nom=nom, defaults={"description": description}
            )
            categories[nom] = categorie
        return categories

    def _creer_evenements(self, gestionnaire, categories, utilisateurs):
        crees = 0
        for donnees in EVENEMENTS:
            evenement, cree = Evenement.objects.get_or_create(
                titre=donnees["titre"],
                cree_par=gestionnaire,
                defaults={
                    "description": donnees["description"],
                    "date": _date(donnees["jours"], donnees["heure"]),
                    "lieu": donnees["lieu"],
                    "capacite": donnees["capacite"],
                    "categorie": categories[donnees["categorie"]],
                },
            )
            if cree:
                crees += 1
                self._creer_inscriptions(evenement, donnees, utilisateurs)
        return crees

    def _creer_inscriptions(self, evenement, donnees, utilisateurs):
        passe = not evenement.est_a_venir

        # Les annulations d'abord : la place est libérée avant les inscrits finaux.
        for username in donnees["annules"]:
            participant = utilisateurs[username]
            if passe:
                Inscription.objects.create(
                    participant=participant,
                    evenement=evenement,
                    statut=Inscription.Statut.ANNULEE,
                    date_annulation=timezone.now(),
                )
            else:
                inscription = services.inscrire(participant, evenement)
                services.annuler(inscription, participant)

        for username in donnees["inscrits"]:
            participant = utilisateurs[username]
            if passe:
                # Les services refusent d'inscrire à un événement passé :
                # insertion directe, uniquement pour les données de démo.
                Inscription.objects.create(participant=participant, evenement=evenement)
            else:
                services.inscrire(participant, evenement)