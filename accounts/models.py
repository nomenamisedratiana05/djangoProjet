from django.contrib.auth.models import AbstractUser
from django.db import models


class Utilisateur(AbstractUser):
    """Utilisateur personnalisé : participant ou gestionnaire."""

    class Role(models.TextChoices):
        PARTICIPANT = "participant", "Participant"
        GESTIONNAIRE = "gestionnaire", "Gestionnaire"

    email = models.EmailField("adresse e-mail", unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PARTICIPANT,
        db_index=True,
    )

    @property
    def est_gestionnaire(self):
        return self.is_superuser or self.role == self.Role.GESTIONNAIRE

    def __str__(self):
        return self.get_full_name() or self.username

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["username"]