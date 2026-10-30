from django.test import TestCase
from django.urls import reverse

from events.models import Evenement, Inscription

from .factories import (
    creer_categorie,
    creer_evenement,
    creer_gestionnaire,
    creer_inscription,
    creer_utilisateur,
)


class AccesGestionnaireTests(TestCase):
    """Les vues gestionnaire sont fermées aux participants et aux anonymes."""

    def setUp(self):
        self.evenement = creer_evenement()
        self.urls = [
            reverse("evenements:tableau_de_bord"),
            reverse("evenements:gestion_liste"),
            reverse("evenements:creer"),
            reverse("evenements:modifier", args=[self.evenement.pk]),
            reverse("evenements:supprimer", args=[self.evenement.pk]),
            reverse("evenements:inscrits", args=[self.evenement.pk]),
            reverse("evenements:export_inscrits", args=[self.evenement.pk]),
        ]

    def test_anonyme_redirige_vers_la_connexion(self):
        for url in self.urls:
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertEqual(reponse.status_code, 302)
                self.assertIn(reverse("accounts:connexion"), reponse["Location"])

    def test_participant_recoit_403(self):
        self.client.force_login(creer_utilisateur())
        for url in self.urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_participant_ne_peut_pas_creer_par_post(self):
        self.client.force_login(creer_utilisateur())
        reponse = self.client.post(reverse("evenements:creer"), {"titre": "Pirate"})
        self.assertEqual(reponse.status_code, 403)
        self.assertFalse(Evenement.objects.filter(titre="Pirate").exists())

    def test_participant_ne_peut_pas_supprimer(self):
        self.client.force_login(creer_utilisateur())
        reponse = self.client.post(
            reverse("evenements:supprimer", args=[self.evenement.pk])
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertTrue(Evenement.objects.filter(pk=self.evenement.pk).exists())

    def test_participant_ne_peut_pas_annuler_via_la_vue_gestionnaire(self):
        inscription = creer_inscription(creer_utilisateur(), self.evenement)
        self.client.force_login(creer_utilisateur())
        reponse = self.client.post(
            reverse("evenements:annuler_inscrit", args=[inscription.pk])
        )
        self.assertEqual(reponse.status_code, 403)
        inscription.refresh_from_db()
        self.assertTrue(inscription.est_confirmee)

    def test_gestionnaire_acces_autorise(self):
        self.client.force_login(creer_gestionnaire())
        for url in self.urls[:4] + self.urls[5:]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class CreationEvenementTests(TestCase):
    def test_gestionnaire_cree_un_evenement_et_devient_createur(self):
        gestionnaire = creer_gestionnaire()
        categorie = creer_categorie()
        self.client.force_login(gestionnaire)
        reponse = self.client.post(
            reverse("evenements:creer"),
            {
                "titre": "Conférence IA",
                "description": "Une conférence",
                "date": "2099-01-15T14:00",
                "lieu": "Amphi 1",
                "capacite": 50,
                "categorie": categorie.pk,
            },
        )
        evenement = Evenement.objects.get(titre="Conférence IA")
        self.assertRedirects(
            reponse, reverse("evenements:detail", args=[evenement.pk])
        )
        self.assertEqual(evenement.cree_par, gestionnaire)

    def test_createur_non_modifiable_par_le_formulaire(self):
        gestionnaire = creer_gestionnaire()
        autre = creer_gestionnaire()
        categorie = creer_categorie()
        self.client.force_login(gestionnaire)
        self.client.post(
            reverse("evenements:creer"),
            {
                "titre": "Test créateur",
                "description": "x",
                "date": "2099-01-15T14:00",
                "lieu": "Lieu",
                "capacite": 5,
                "categorie": categorie.pk,
                "cree_par": autre.pk,  # tentative d'usurpation
            },
        )
        self.assertEqual(Evenement.objects.get(titre="Test créateur").cree_par, gestionnaire)

    def test_capacite_zero_refusee_par_le_formulaire(self):
        self.client.force_login(creer_gestionnaire())
        reponse = self.client.post(
            reverse("evenements:creer"),
            {
                "titre": "Capacité nulle",
                "description": "x",
                "date": "2099-01-15T14:00",
                "lieu": "Lieu",
                "capacite": 0,
                "categorie": creer_categorie().pk,
            },
        )
        self.assertEqual(reponse.status_code, 200)  # formulaire réaffiché
        self.assertFalse(Evenement.objects.filter(titre="Capacité nulle").exists())

    def test_date_passee_refusee_par_le_formulaire(self):
        self.client.force_login(creer_gestionnaire())
        reponse = self.client.post(
            reverse("evenements:creer"),
            {
                "titre": "Date passée",
                "description": "x",
                "date": "2000-01-01T10:00",
                "lieu": "Lieu",
                "capacite": 5,
                "categorie": creer_categorie().pk,
            },
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Evenement.objects.filter(titre="Date passée").exists())


class InscriptionViewsTests(TestCase):
    def setUp(self):
        self.evenement = creer_evenement(capacite=2)
        self.participant = creer_utilisateur()

    def test_inscription_anonyme_redirigee_vers_connexion(self):
        reponse = self.client.post(
            reverse("evenements:inscrire", args=[self.evenement.pk])
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertIn(reverse("accounts:connexion"), reponse["Location"])
        self.assertEqual(Inscription.objects.count(), 0)

    def test_inscription_par_get_interdite(self):
        self.client.force_login(self.participant)
        reponse = self.client.get(
            reverse("evenements:inscrire", args=[self.evenement.pk])
        )
        self.assertEqual(reponse.status_code, 405)
        self.assertEqual(Inscription.objects.count(), 0)

    def test_inscription_par_post(self):
        self.client.force_login(self.participant)
        reponse = self.client.post(
            reverse("evenements:inscrire", args=[self.evenement.pk]), follow=True
        )
        self.assertContains(reponse, "est confirmée")
        self.assertEqual(self.evenement.nombre_inscrits, 1)

    def test_double_inscription_affiche_un_message_d_erreur(self):
        creer_inscription(self.participant, self.evenement)
        self.client.force_login(self.participant)
        reponse = self.client.post(
            reverse("evenements:inscrire", args=[self.evenement.pk]), follow=True
        )
        self.assertContains(reponse, "déjà inscrit")
        self.assertEqual(Inscription.objects.count(), 1)

    def test_utilisateur_ne_peut_pas_annuler_l_inscription_d_un_autre(self):
        inscription = creer_inscription(creer_utilisateur(), self.evenement)
        self.client.force_login(self.participant)
        url = reverse("evenements:annuler", args=[inscription.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        inscription.refresh_from_db()
        self.assertTrue(inscription.est_confirmee)

    def test_annulation_par_get_ne_modifie_rien(self):
        inscription = creer_inscription(self.participant, self.evenement)
        self.client.force_login(self.participant)
        reponse = self.client.get(reverse("evenements:annuler", args=[inscription.pk]))
        self.assertEqual(reponse.status_code, 200)  # page de confirmation
        inscription.refresh_from_db()
        self.assertTrue(inscription.est_confirmee)

    def test_annulation_par_post(self):
        inscription = creer_inscription(self.participant, self.evenement)
        self.client.force_login(self.participant)
        self.client.post(reverse("evenements:annuler", args=[inscription.pk]))
        inscription.refresh_from_db()
        self.assertEqual(inscription.statut, Inscription.Statut.ANNULEE)

    def test_mes_inscriptions_n_affiche_que_les_miennes(self):
        mienne = creer_inscription(self.participant, self.evenement)
        autre_evenement = creer_evenement(titre="Événement d'un autre")
        creer_inscription(creer_utilisateur(), autre_evenement)
        self.client.force_login(self.participant)
        reponse = self.client.get(reverse("evenements:mes_inscriptions"))
        self.assertEqual(list(reponse.context["inscriptions"]), [mienne])
        self.assertNotContains(reponse, "Événement d'un autre")


class ListePubliqueTests(TestCase):
    def test_liste_n_affiche_que_les_evenements_a_venir(self):
        creer_evenement(titre="Futur", jours=3)
        creer_evenement(titre="Passé", jours=-3)
        reponse = self.client.get(reverse("evenements:liste"))
        self.assertContains(reponse, "Futur")
        self.assertNotContains(reponse, "Passé")

    def test_recherche_par_titre(self):
        creer_evenement(titre="Atelier Python")
        creer_evenement(titre="Conférence Java")
        reponse = self.client.get(reverse("evenements:liste"), {"q": "python"})
        self.assertContains(reponse, "Atelier Python")
        self.assertNotContains(reponse, "Conférence Java")

    def test_filtre_par_categorie(self):
        cat_a, cat_b = creer_categorie("A"), creer_categorie("B")
        creer_evenement(titre="Dans A", categorie=cat_a)
        creer_evenement(titre="Dans B", categorie=cat_b)
        reponse = self.client.get(reverse("evenements:liste"), {"categorie": cat_a.pk})
        self.assertContains(reponse, "Dans A")
        self.assertNotContains(reponse, "Dans B")

    def test_pagination_par_9(self):
        for _ in range(11):
            creer_evenement()
        reponse = self.client.get(reverse("evenements:liste"))
        self.assertEqual(len(reponse.context["evenements"]), 9)
        reponse = self.client.get(reverse("evenements:liste"), {"page": 2})
        self.assertEqual(len(reponse.context["evenements"]), 2)

    def test_detail_evenement_complet_affiche_complet(self):
        evenement = creer_evenement(capacite=1)
        creer_inscription(creer_utilisateur(), evenement)
        reponse = self.client.get(reverse("evenements:detail", args=[evenement.pk]))
        self.assertContains(reponse, "Complet")


class SuppressionEtExportTests(TestCase):
    def setUp(self):
        self.gestionnaire = creer_gestionnaire()
        self.client.force_login(self.gestionnaire)

    def test_suppression_refusee_si_inscription_confirmee(self):
        evenement = creer_evenement()
        creer_inscription(creer_utilisateur(), evenement)
        self.client.post(reverse("evenements:supprimer", args=[evenement.pk]))
        self.assertTrue(Evenement.objects.filter(pk=evenement.pk).exists())

    def test_suppression_refusee_meme_si_inscription_annulee(self):
        evenement = creer_evenement()
        creer_inscription(
            creer_utilisateur(), evenement, statut=Inscription.Statut.ANNULEE
        )
        self.client.post(reverse("evenements:supprimer", args=[evenement.pk]))
        self.assertTrue(Evenement.objects.filter(pk=evenement.pk).exists())

    def test_suppression_autorisee_sans_inscription(self):
        evenement = creer_evenement()
        self.client.post(reverse("evenements:supprimer", args=[evenement.pk]))
        self.assertFalse(Evenement.objects.filter(pk=evenement.pk).exists())

    def test_suppression_par_get_ne_supprime_pas(self):
        evenement = creer_evenement()
        reponse = self.client.get(reverse("evenements:supprimer", args=[evenement.pk]))
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(Evenement.objects.filter(pk=evenement.pk).exists())

    def test_gestionnaire_annule_une_inscription(self):
        inscription = creer_inscription(creer_utilisateur(), creer_evenement())
        self.client.post(reverse("evenements:annuler_inscrit", args=[inscription.pk]))
        inscription.refresh_from_db()
        self.assertEqual(inscription.statut, Inscription.Statut.ANNULEE)

    def test_export_csv_une_ligne_par_inscription(self):
        evenement = creer_evenement()
        creer_inscription(creer_utilisateur(), evenement)
        creer_inscription(
            creer_utilisateur(), evenement, statut=Inscription.Statut.ANNULEE
        )
        reponse = self.client.get(
            reverse("evenements:export_inscrits", args=[evenement.pk])
        )
        self.assertEqual(reponse["Content-Type"], "text/csv; charset=utf-8")
        lignes = reponse.content.decode("utf-8-sig").strip().splitlines()
        self.assertEqual(len(lignes), 3)  # en-tête + 2 inscriptions

    def test_export_csv_neutralise_les_formules(self):
        evenement = creer_evenement()
        pirate = creer_utilisateur(first_name="=HYPERLINK(\"http://x\")")
        creer_inscription(pirate, evenement)
        reponse = self.client.get(
            reverse("evenements:export_inscrits", args=[evenement.pk])
        )
        contenu = reponse.content.decode("utf-8-sig")
        self.assertIn("'=HYPERLINK", contenu)
        self.assertNotIn(";=HYPERLINK", contenu)