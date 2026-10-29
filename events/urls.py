from django.urls import path

from . import views, views_gestion

app_name = "evenements"

urlpatterns = [
    # Espace public et participant
    path("", views.EvenementListView.as_view(), name="liste"),
    path("evenements/<int:pk>/", views.EvenementDetailView.as_view(), name="detail"),
    path("evenements/<int:pk>/inscrire/", views.InscrireView.as_view(), name="inscrire"),
    path("mes-inscriptions/", views.MesInscriptionsView.as_view(), name="mes_inscriptions"),
    path("inscriptions/<int:pk>/annuler/", views.AnnulerInscriptionView.as_view(), name="annuler"),

    # Espace gestionnaire
    path("gestion/", views_gestion.TableauDeBordView.as_view(), name="tableau_de_bord"),
    path("gestion/evenements/", views_gestion.GestionEvenementListView.as_view(), name="gestion_liste"),
    path("gestion/evenements/creer/", views_gestion.EvenementCreateView.as_view(), name="creer"),
    path("gestion/evenements/<int:pk>/modifier/", views_gestion.EvenementUpdateView.as_view(), name="modifier"),
    path("gestion/evenements/<int:pk>/supprimer/", views_gestion.EvenementSupprimerView.as_view(), name="supprimer"),
    path("gestion/evenements/<int:pk>/inscrits/", views_gestion.InscritsEvenementView.as_view(), name="inscrits"),
    path("gestion/evenements/<int:pk>/inscrits/export/", views_gestion.ExportInscritsCSVView.as_view(), name="export_inscrits"),
    path("gestion/inscriptions/<int:pk>/annuler/", views_gestion.AnnulerInscriptionGestionnaireView.as_view(), name="annuler_inscrit"),
]