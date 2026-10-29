
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Categorie(models.Model):
    """
    Catégorie permettant de classer les événements.
    Exemple : Informatique, Sport, Culture, Formation.
    """

    nom = models.CharField(
        max_length=100,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    # Affichage dans l'interface d'administration Django.
    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["nom"]


class Evenement(models.Model):
    """
    Événement auquel les utilisateurs peuvent s'inscrire.
    """

    titre = models.CharField(
        max_length=200,
    )

    description = models.TextField()

    date = models.DateTimeField()

    lieu = models.CharField(
        max_length=255,
    )

    # La capacité doit être au minimum égale à 1.
    capacite = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    # Chaque événement appartient à une catégorie.
    # PROTECT empêche la suppression d'une catégorie
    # tant qu'elle est utilisée par un événement.
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.PROTECT,
        related_name="evenements",
    )

    # Utilisateur ayant créé l'événement.
    # On utilise le modèle User configuré dans Django.
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evenements_crees",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.titre

    @property
    def nombre_inscrits(self):
        """
        Nombre de participants ayant une inscription confirmée.
        Les inscriptions annulées ne sont pas comptées.
        """
        return self.inscriptions.filter(
            statut="confirmed"
        ).count()

    @property
    def places_restantes(self):
        """
        Calcule le nombre de places encore disponibles.
        """
        return max(
            0,
            self.capacite - self.nombre_inscrits,
        )

    def peut_recevoir_inscription(self):
        """
        Indique si l'événement accepte encore des inscriptions.
        """
        return (
            self.date > timezone.now()
            and self.places_restantes > 0
        )

    def clean(self):
        """
        Vérifications métier sur l'événement.
        Cette méthode doit être appelée par la validation
        du formulaire ou explicitement avec full_clean().
        """
        super().clean()

        if self.date and self.date <= timezone.now():
            raise ValidationError({
                "date": "La date de l'événement doit être dans le futur."
            })

        if self.pk and self.capacite is not None:
            inscriptions_confirmees = self.inscriptions.filter(
                statut="confirmed"
            ).count()

            if self.capacite < inscriptions_confirmees:
                raise ValidationError({
                    "capacite": (
                        "La capacité ne peut pas être inférieure "
                        "au nombre d'inscriptions confirmées."
                    )
                })

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ["date"]
