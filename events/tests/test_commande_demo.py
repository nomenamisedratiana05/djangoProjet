import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from events.models import Categorie, Evenement, Inscription

from .factories import creer_utilisateur

Utilisateur = get_user_model()


class ChargerDemoTests(TestCase):
    def lancer(self, *args, mot_de_passe=None):
        sortie = StringIO()
        with mock.patch.dict(os.environ):
            os.environ.pop("EVENTHUB_DEMO_PASSWORD", None)
            if mot_de_passe:
                os.environ["EVENTHUB_DEMO_PASSWORD"] = mot_de_passe
            call_command("charger_demo", *args, stdout=sortie)
        return sortie.getvalue()

    def test_cree_les_donnees_attendues(self):
        self.lancer()
        self.assertEqual(Categorie.objects.count(), 3)
        self.assertEqual(Evenement.objects.count(), 6)
        self.assertEqual(Utilisateur.objects.filter(username__startswith="demo_").count(), 6)
        self.assertTrue(Utilisateur.objects.get(username="demo_organisateur").est_gestionnaire)
        self.assertFalse(Utilisateur.objects.get(username="demo_alice").est_gestionnaire)

    def test_les_cas_de_demonstration_existent(self):
        self.lancer()
        evenements = list(Evenement.objects.avec_stats())
        self.assertTrue(any(e.est_complet for e in evenements))
        self.assertTrue(any(e.peut_etre_supprime for e in evenements))
        self.assertTrue(any(not e.est_a_venir for e in evenements))
        self.assertTrue(
            Inscription.objects.filter(statut=Inscription.Statut.ANNULEE).exists()
        )

    def test_relancer_ne_cree_pas_de_doublons(self):
        self.lancer()
        compteurs = (
            Categorie.objects.count(),
            Evenement.objects.count(),
            Inscription.objects.count(),
            Utilisateur.objects.count(),
        )
        sortie = self.lancer()
        self.assertEqual(
            compteurs,
            (
                Categorie.objects.count(),
                Evenement.objects.count(),
                Inscription.objects.count(),
                Utilisateur.objects.count(),
            ),
        )
        self.assertNotIn("Mot de passe généré", sortie)

    def test_mot_de_passe_genere_est_affiche_et_valide(self):
        sortie = self.lancer()
        mot_de_passe = sortie.split("Mot de passe généré :")[1].split()[0]
        self.assertGreaterEqual(len(mot_de_passe), 12)
        self.assertTrue(Utilisateur.objects.get(username="demo_alice").check_password(mot_de_passe))

    def test_mot_de_passe_depuis_la_variable_d_environnement(self):
        secret = "Secret-De-Test-2026!"
        sortie = self.lancer(mot_de_passe=secret)
        self.assertTrue(Utilisateur.objects.get(username="demo_bob").check_password(secret))
        self.assertNotIn(secret, sortie)  # jamais réaffiché

    def test_reset_conserve_les_comptes_non_demo(self):
        reel = creer_utilisateur(username="vrai_compte")
        self.lancer()
        self.lancer("--reset")
        self.assertTrue(Utilisateur.objects.filter(pk=reel.pk).exists())
        self.assertEqual(Evenement.objects.count(), 6)
        self.assertEqual(Utilisateur.objects.filter(username__startswith="demo_").count(), 6)