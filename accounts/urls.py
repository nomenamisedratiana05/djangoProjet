from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", LogoutView.as_view(), name="deconnexion"),
    path("inscription/", views.InscriptionView.as_view(), name="inscription"),
]