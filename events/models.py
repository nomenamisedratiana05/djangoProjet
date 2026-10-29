from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


class HorodatageModel(models.Model):
    """Classe abstraite réutilisable : dates de création/modification."""

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Categorie(HorodatageModel):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class EvenementQuerySet(models.QuerySet):
    def a_venir(self):
        return self.filter(date__gt=timezone.now())

    def avec_stats(self):
        """Ajoute nb_inscrits en une seule requête SQL."""
        return self.annotate(
            nb_inscrits=Count(
                "inscriptions",
                filter=Q(inscriptions__statut="confirmed"),
            )
        )

    def recherche(self, terme=None, categorie_id=None):
        qs = self
        if terme:
            qs = qs.filter(titre__icontains=terme)
        if categorie_id:
            qs = qs.filter(categorie_id=categorie_id)
        return qs


class Evenement(HorodatageModel):
    titre = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField(db_index=True)
    lieu = models.CharField(max_length=255)
    capacite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    categorie = models.ForeignKey(
        Categorie, on_delete=models.PROTECT, related_name="evenements"
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evenements_crees",
    )

    objects = EvenementQuerySet.as_manager()

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ["date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(capacite__gte=1),
                name="evenement_capacite_positive",
            )
        ]

    def __str__(self):
        return self.titre

    # --- Calculs -----------------------------------------------------
    @property
    def nombre_inscrits(self):
        # Utilise l'annotation si disponible (évite une requête).
        if hasattr(self, "nb_inscrits"):
            return self.nb_inscrits
        return self.inscriptions.filter(
            statut=Inscription.Statut.CONFIRMEE
        ).count()

    @property
    def places_restantes(self):
        return max(0, self.capacite - self.nombre_inscrits)

    @property
    def est_a_venir(self):
        return self.date > timezone.now()

    @property
    def est_complet(self):
        return self.places_restantes == 0

    def peut_recevoir_inscription(self):
        return self.est_a_venir and not self.est_complet

    # --- Validation --------------------------------------------------
    def clean(self):
        super().clean()

        # Date future exigée seulement à la création ou si la date change.
        if self.date:
            ancienne_date = None
            if self.pk:
                ancienne_date = (
                    Evenement.objects.filter(pk=self.pk)
                    .values_list("date", flat=True)
                    .first()
                )
            if (self.pk is None or self.date != ancienne_date) \
                    and self.date <= timezone.now():
                raise ValidationError(
                    {"date": "La date de l'événement doit être dans le futur."}
                )

        # Ne pas réduire la capacité sous le nombre d'inscrits confirmés.
        if self.pk and self.capacite is not None:
            confirmes = self.inscriptions.filter(
                statut=Inscription.Statut.CONFIRMEE
            ).count()
            if self.capacite < confirmes:
                raise ValidationError(
                    {
                        "capacite": (
                            f"La capacité ne peut pas être inférieure au "
                            f"nombre d'inscrits confirmés ({confirmes})."
                        )
                    }
                )


class Inscription(HorodatageModel):
    class Statut(models.TextChoices):
        CONFIRMEE = "confirmed", "Confirmée"
        ANNULEE = "cancelled", "Annulée"

    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inscriptions",
    )
    evenement = models.ForeignKey(
        Evenement, on_delete=models.PROTECT, related_name="inscriptions"
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.CONFIRMEE,
        db_index=True,
    )
    date_annulation = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        ordering = ["-date_creation"]
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "evenement"],
                name="unique_inscription_participant_evenement",
            )
        ]
        indexes = [
            models.Index(fields=["evenement", "statut"]),
        ]

    def __str__(self):
        return f"{self.participant} – {self.evenement} – {self.get_statut_display()}"

    @property
    def est_confirmee(self):
        return self.statut == self.Statut.CONFIRMEE

    @property
    def est_annulable(self):
        return self.est_confirmee and self.evenement.est_a_venir