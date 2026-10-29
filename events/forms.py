from django import forms

from .models import Categorie,Evenement


class RechercheEvenementForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Recherche",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Rechercher par titre"}
        ),
    )
    categorie = forms.ModelChoiceField(
        queryset=Categorie.objects.all(),
        required=False,
        label="Catégorie",
        empty_label="Toutes les catégories",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

class EvenementForm(forms.ModelForm):
    class Meta:
        model = Evenement
        fields = ["titre", "description", "date", "lieu", "capacite", "categorie"]
        labels = {
            "date": "Date et heure",
            "capacite": "Capacité",
            "categorie": "Catégorie",
        }
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "lieu": forms.TextInput(attrs={"class": "form-control"}),
            "capacite": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "categorie": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Format envoyé par le champ HTML datetime-local.
        self.fields["date"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]