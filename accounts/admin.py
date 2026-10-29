from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    # Ajoute une section « Rôle EventHub » à la page de modification.
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle EventHub", {"fields": ("role",)}),
    )

    # Ajoute e-mail et rôle à la page de création.
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informations EventHub", {"fields": ("email", "role")}),
    )