from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.crypto import get_random_string

Utilisateur = get_user_model()


class InscriptionCompteTests(TestCase):
    def donnees(self, **surcharge):
        mot_de_passe = get_random_string(20)
        base = {
            "username": "nouveau",
            "first_name": "Jean",
            "last_name": "Rakoto",
            "email": "nouveau@example.com",
            "password1": mot_de_passe,
            "password2": mot_de_passe,
        }
        base.update(surcharge)
        return base

    def test_creation_de_compte(self):
        reponse = self.client.post(reverse("accounts:inscription"), self.donnees())
        self.assertRedirects(reponse, reverse("evenements:liste"))
        self.assertTrue(Utilisateur.objects.filter(username="nouveau").exists())

    def test_role_gestionnaire_injecte_est_ignore(self):
        self.client.post(
            reverse("accounts:inscription"),
            self.donnees(role="gestionnaire", is_staff="on", is_superuser="on"),
        )
        utilisateur = Utilisateur.objects.get(username="nouveau")
        self.assertEqual(utilisateur.role, Utilisateur.Role.PARTICIPANT)
        self.assertFalse(utilisateur.est_gestionnaire)
        self.assertFalse(utilisateur.is_staff)
        self.assertFalse(utilisateur.is_superuser)

    def test_email_deja_utilise_refuse(self):
        Utilisateur.objects.create_user(
            "existant", "nouveau@example.com", get_random_string(20)
        )
        reponse = self.client.post(reverse("accounts:inscription"), self.donnees())
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Utilisateur.objects.filter(username="nouveau").exists())

    def test_mots_de_passe_differents_refuses(self):
        reponse = self.client.post(
            reverse("accounts:inscription"),
            self.donnees(password2=get_random_string(20)),
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Utilisateur.objects.filter(username="nouveau").exists())

    def test_deconnexion_par_get_refusee(self):
        self.client.force_login(
            Utilisateur.objects.create_user(
                "u", "u@example.com", get_random_string(20)
            )
        )
        reponse = self.client.get(reverse("accounts:deconnexion"))
        self.assertEqual(reponse.status_code, 405)