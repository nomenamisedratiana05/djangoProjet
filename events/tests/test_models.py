from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from events.models import Evenement, Inscription

from .factories import (
    creer_categorie,
    creer_evenement,
    creer_gestionnaire,
    creer_inscription,
    creer_utilisateur,
)


class EvenementValidationTests(TestCase):
    def donnees(self, **surcharge):
        base = {
            "titre": "Atelier Django",
            "description": "Description",
            "date": timezone.now() + timedelta(days=3),
            "lieu": "Salle A",
            "capacite": 20,
            "categorie": creer_categorie(),
            "cree_par": creer_gestionnaire(),
        }
        base.update(surcharge)
        return base

    def test_capacite_zero_refusee(self):
        evenement = Evenement(**self.donnees(capacite=0))
        with self.assertRaises(ValidationError) as ctx:
            evenement.full_clean()
        self.assertIn("capacite", ctx.exception.message_dict)

    def test_date_passee_refusee_a_la_creation(self):
        evenement = Evenement(
            **self.donnees(date=timezone.now() - timedelta(days=1))
        )
        with self.assertRaises(ValidationError) as ctx:
            evenement.full_clean()
        self.assertIn("date", ctx.exception.message_dict)

    def test_evenement_valide_accepte(self):
        Evenement(**self.donnees()).full_clean()  # ne doit pas lever

    def test_modifier_description_d_un_evenement_passe_est_possible(self):
        passe = creer_evenement(jours=-2)
        passe.description = "Description corrigée"
        passe.full_clean()  # la date n'a pas changé : pas d'erreur

    def test_changer_la_date_vers_le_passe_est_refuse(self):
        evenement = creer_evenement(jours=5)
        evenement.date = timezone.now() - timedelta(days=1)
        with self.assertRaises(ValidationError) as ctx:
            evenement.full_clean()
        self.assertIn("date", ctx.exception.message_dict)

    def test_capacite_inferieure_aux_inscrits_refusee(self):
        evenement = creer_evenement(capacite=5)
        for _ in range(3):
            creer_inscription(creer_utilisateur(), evenement)
        evenement.capacite = 2
        with self.assertRaises(ValidationError) as ctx:
            evenement.full_clean()
        self.assertIn("capacite", ctx.exception.message_dict)

    def test_contrainte_base_capacite_positive(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                creer_evenement(capacite=0)


class CalculPlacesTests(TestCase):
    def test_places_restantes_ignore_les_annulees(self):
        evenement = creer_evenement(capacite=3)
        creer_inscription(creer_utilisateur(), evenement)
        creer_inscription(
            creer_utilisateur(), evenement, statut=Inscription.Statut.ANNULEE
        )
        self.assertEqual(evenement.nombre_inscrits, 1)
        self.assertEqual(evenement.places_restantes, 2)

    def test_annotation_donne_le_meme_resultat_que_la_propriete(self):
        evenement = creer_evenement(capacite=4)
        creer_inscription(creer_utilisateur(), evenement)
        creer_inscription(
            creer_utilisateur(), evenement, statut=Inscription.Statut.ANNULEE
        )
        annote = Evenement.objects.avec_stats().get(pk=evenement.pk)
        self.assertEqual(annote.nombre_inscrits, 1)
        self.assertEqual(annote.nb_inscriptions_total, 2)
        self.assertEqual(annote.places_restantes, 3)

    def test_a_venir_exclut_les_evenements_passes(self):
        futur = creer_evenement(jours=3)
        creer_evenement(jours=-3)
        self.assertEqual(list(Evenement.objects.a_venir()), [futur])

    def test_unicite_participant_evenement(self):
        evenement = creer_evenement()
        participant = creer_utilisateur()
        creer_inscription(participant, evenement)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                creer_inscription(participant, evenement)