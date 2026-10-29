from django.contrib import admin

from .models import Categorie, Evenement, Inscription


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ("nom", "description")
    search_fields = ("nom",)


class InscriptionInline(admin.TabularInline):
    """Affiche les inscrits directement dans la page d'un événement."""

    model = Inscription
    extra = 0
    fields = ("participant", "statut", "date_creation", "date_annulation")
    readonly_fields = ("date_creation", "date_annulation")
    autocomplete_fields = ("participant",)


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    list_display = (
        "titre",
        "date",
        "lieu",
        "categorie",
        "capacite",
        "inscrits",
        "places",
        "cree_par",
    )
    list_filter = ("categorie", "date")
    search_fields = ("titre", "lieu", "description")
    date_hierarchy = "date"
    list_select_related = ("categorie", "cree_par")
    readonly_fields = ("date_creation", "date_modification")
    inlines = [InscriptionInline]

    def get_queryset(self, request):
        # Une seule requête SQL pour compter les inscrits de toute la liste.
        return super().get_queryset(request).avec_stats()

    @admin.display(description="Inscrits", ordering="nb_inscrits")
    def inscrits(self, obj):
        return obj.nombre_inscrits

    @admin.display(description="Places restantes")
    def places(self, obj):
        return obj.places_restantes

    def save_model(self, request, obj, form, change):
        # Renseigne automatiquement le créateur lors de la création.
        if not change:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Le créateur est automatique : on le rend optionnel dans le formulaire.
        if "cree_par" in form.base_fields:
            form.base_fields["cree_par"].required = False
        return form


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ("participant", "evenement", "statut", "date_creation")
    list_filter = ("statut", "evenement__categorie")
    search_fields = (
        "participant__username",
        "participant__email",
        "evenement__titre",
    )
    list_select_related = ("participant", "evenement")
    autocomplete_fields = ("participant", "evenement")
    readonly_fields = ("date_creation", "date_modification", "date_annulation")