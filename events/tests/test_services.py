from django.test import TestCase

from events import services
from events.models import Inscription
from events.services import InscriptionError

from .factories import (
    creer_evenement,
    creer_gestionnaire,
    creer_inscription,
    creer_utilisateur,
)


class InscrireTests(TestCase):
    def test_inscription_reussie(self):
        participant = creer_utilisateur()
        evenement = creer_evenement(capacite=2)
        inscription = services.inscrire(participant, evenement)
        self.assertEqual(inscription.statut, Inscription.Statut.CONFIRMEE)
        self.assertEqual(evenement.places_restantes, 1)

    def test_double_inscription_refusee(self):
        participant = creer_utilisateur()
        evenement = creer_evenement()
        services.inscrire(participant, evenement)
        with self.assertRaisesMessage(InscriptionError, "déjà inscrit"):
            services.inscrire(participant, evenement)
        self.assertEqual(Inscription.objects.count(), 1)

    def test_inscription_refusee_si_evenement_complet(self):
        evenement = creer_evenement(capacite=1)
        services.inscrire(creer_utilisateur(), evenement)
        with self.assertRaisesMessage(InscriptionError, "capacité maximale"):
            services.inscrire(creer_utilisateur(), evenement)
        self.assertEqual(evenement.nombre_inscrits, 1)

    def test_derniere_place_est_attribuable(self):
        """Non-régression : une inscription ne doit pas se compter elle-même."""
        evenement = creer_evenement(capacite=2)
        services.inscrire(creer_utilisateur(), evenement)
        services.inscrire(creer_utilisateur(), evenement)  # ne doit pas lever
        self.assertTrue(evenement.est_complet)

    def test_inscription_refusee_apres_la_date(self):
        evenement = creer_evenement(jours=-1)
        with self.assertRaisesMessage(InscriptionError, "commencé ou terminé"):
            services.inscrire(creer_utilisateur(), evenement)
        self.assertEqual(Inscription.objects.count(), 0)

    def test_reinscription_possible_apres_annulation(self):
        participant = creer_utilisateur()
        evenement = creer_evenement()
        inscription = services.inscrire(participant, evenement)
        services.annuler(inscription, participant)

        nouvelle = services.inscrire(participant, evenement)

        self.assertEqual(nouvelle.pk, inscription.pk)  # même ligne réactivée
        self.assertEqual(nouvelle.statut, Inscription.Statut.CONFIRMEE)
        self.assertIsNone(nouvelle.date_annulation)
        self.assertEqual(Inscription.objects.count(), 1)

    def test_reinscription_refusee_si_la_place_a_ete_prise(self):
        evenement = creer_evenement(capacite=1)
        premier = creer_utilisateur()
        inscription = services.inscrire(premier, evenement)
        services.annuler(inscription, premier)
        services.inscrire(creer_utilisateur(), evenement)  # un autre prend la place
        with self.assertRaisesMessage(InscriptionError, "capacité maximale"):
            services.inscrire(premier, evenement)


class AnnulerTests(TestCase):
    def test_annulation_libere_la_place(self):
        participant = creer_utilisateur()
        evenement = creer_evenement(capacite=1)
        inscription = services.inscrire(participant, evenement)
        services.annuler(inscription, participant)
        inscription.refresh_from_db()
        self.assertEqual(inscription.statut, Inscription.Statut.ANNULEE)
        self.assertIsNotNone(inscription.date_annulation)
        self.assertEqual(evenement.places_restantes, 1)

    def test_annulation_refusee_apres_le_debut(self):
        participant = creer_utilisateur()
        evenement = creer_evenement(jours=-1)
        inscription = creer_inscription(participant, evenement)
        with self.assertRaisesMessage(InscriptionError, "a commencé"):
            services.annuler(inscription, participant)
        inscription.refresh_from_db()
        self.assertEqual(inscription.statut, Inscription.Statut.CONFIRMEE)

    def test_annulation_refusee_pour_un_autre_utilisateur(self):
        proprietaire = creer_utilisateur()
        intrus = creer_utilisateur()
        inscription = creer_inscription(proprietaire, creer_evenement())
        with self.assertRaises(InscriptionError):
            services.annuler(inscription, intrus)
        inscription.refresh_from_db()
        self.assertTrue(inscription.est_confirmee)

    def test_double_annulation_refusee(self):
        participant = creer_utilisateur()
        inscription = services.inscrire(participant, creer_evenement())
        services.annuler(inscription, participant)
        with self.assertRaisesMessage(InscriptionError, "déjà annulée"):
            services.annuler(inscription, participant)


class AnnulerParGestionnaireTests(TestCase):
    def test_gestionnaire_peut_annuler(self):
        inscription = creer_inscription(creer_utilisateur(), creer_evenement())
        services.annuler_par_gestionnaire(inscription, creer_gestionnaire())
        inscription.refresh_from_db()
        self.assertEqual(inscription.statut, Inscription.Statut.ANNULEE)

    def test_non_gestionnaire_refuse(self):
        inscription = creer_inscription(creer_utilisateur(), creer_evenement())
        with self.assertRaisesMessage(InscriptionError, "réservée aux gestionnaires"):
            services.annuler_par_gestionnaire(inscription, creer_utilisateur())
        inscription.refresh_from_db()
        self.assertTrue(inscription.est_confirmee)