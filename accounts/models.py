
from django.conf import settings
from django.db import models


class Inscription(models.Model):
    """
    Inscription d'un utilisateur à un événement.
    """

    class Statut(models.TextChoices):
        # L'inscription est active et occupe une place.
        CONFIRMEE = "confirmed", "Confirmée"

        # L'inscription a été annulée et ne compte plus
        # dans le nombre de places occupées.
        ANNULEE = "cancelled", "Annulée"

    # Utilisateur inscrit à l'événement.
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inscriptions",
    )

    # Référence vers l'événement de l'application events.
    evenement = models.ForeignKey(
        "events.Evenement",
        on_delete=models.PROTECT,
        related_name="inscriptions",
    )

    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.CONFIRMEE,
    )

    date_inscription = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.participant} - "
            f"{self.evenement} - "
            f"{self.get_statut_display()}"
        )

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        ordering = ["-date_inscription"]

        # Un utilisateur ne peut avoir qu'une seule inscription
        # pour un événement, même si elle a été annulée.
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "evenement"],
                name="unique_inscription_participant_evenement",
            )
        ]
