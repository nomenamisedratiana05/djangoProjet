# EventHub – Gestion des inscriptions à des événements

Application web Django permettant à une association de publier ses événements
(ateliers, conférences, rencontres), aux participants de s'y inscrire et aux
gestionnaires de suivre les inscriptions.

Projet pratique Django – Université de Vakinankaratra, Mention Automatisme et
Informatique, M1 GL. Thème 1 : gestion des inscriptions à des événements.

**Auteur(s) :** [Nom Prénom]

## Fonctionnalités

**Visiteur**
- Liste des événements à venir (date, lieu, capacité, places restantes),
  recherche par titre, filtre par catégorie, pagination.
- Page détail d'un événement. Création de compte et connexion.

**Participant**
- Inscription à un événement tant qu'il reste des places et qu'il n'a pas commencé.
- Page « Mes inscriptions » avec statut (confirmée / annulée).
- Annulation (avec confirmation) avant le début de l'événement. Réinscription possible.

**Gestionnaire**
- Création, modification et suppression d'événements.
- Liste des inscrits par événement (filtre par statut), export CSV.
- Annulation d'une inscription. Tableau de bord (nombre d'événements, taux de remplissage).

## Prérequis

- Python 3.12 ou plus récent
- Aucun service externe : base SQLite, Bootstrap fourni en local (`static/`).

## Installation

```bash
# 1. Se placer dans le dossier du projet (celui qui contient manage.py)
cd gestion_evenements

# 2. Créer et activer l'environnement virtuel
python3 -m venv env
source env/bin/activate            # Windows : env\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Créer la base de données (SQLite : db.sqlite3)
python manage.py migrate
```

## Données de démonstration

```bash
python manage.py charger_demo
```

La commande crée 3 catégories, 6 événements, 1 gestionnaire et 5 participants.
**Aucun mot de passe n'est écrit dans le code** : un mot de passe aléatoire est
généré et affiché une seule fois à la fin de la commande. Pour choisir le vôtre :

```bash
EVENTHUB_DEMO_PASSWORD='votre-mot-de-passe' python manage.py charger_demo
```

| Compte | Rôle |
|---|---|
| `demo_organisateur` | Gestionnaire |
| `demo_alice`, `demo_bob`, `demo_claire`, `demo_david`, `demo_emma` | Participants |

La commande peut être relancée sans créer de doublons.
`python manage.py charger_demo --reset` supprime puis recrée uniquement les
données `demo_*`.

## Créer un compte administrateur

```bash
python manage.py createsuperuser
```

Un superutilisateur a automatiquement les droits de gestionnaire sur le site
et accède à l'administration Django : http://127.0.0.1:8000/admin/

## Passer un compte en gestionnaire

Tout compte créé via la page d'inscription est un **participant** (le rôle ne
peut pas être choisi à l'inscription). Pour le promouvoir :

1. Se connecter à `/admin/` avec un superutilisateur.
2. Ouvrir **Utilisateurs**, puis le compte concerné.
3. Dans la section **Rôle EventHub**, choisir **Gestionnaire** et enregistrer.

## Lancer le serveur

```bash
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000/

## Lancer les tests

```bash
python manage.py test
```

Les tests utilisent une base temporaire et ne modifient pas `db.sqlite3`.
Ils couvrent la validation des données, les règles métier (capacité, double
inscription, annulation, réinscription) et les restrictions d'accès.

## Structure du projet

```
config/            réglages et URLs du projet
accounts/          utilisateur personnalisé, inscription, connexion
events/
  models.py        Categorie, Evenement, Inscription
  services.py      règles métier (inscrire, annuler)
  permissions.py   accès réservé aux gestionnaires
  views.py         espace public et participant
  views_gestion.py espace gestionnaire
  management/      commande charger_demo
  tests/           tests automatisés
templates/         gabarits (héritage depuis base.html)
static/            Bootstrap local
docs/              note de conception et captures d'écran
```

## Règles métier principales

- Les places restantes = capacité − inscriptions **confirmées** (les annulées ne comptent pas).
- Une seule inscription par participant et par événement (contrainte en base).
- Pas d'inscription ni d'annulation une fois l'événement commencé.
- Inscription refusée si l'événement est complet.
- Après annulation, le participant peut se réinscrire (l'inscription est réactivée, si une place existe).
- Un événement ayant des inscriptions (même annulées) ne peut pas être supprimé.
- Un participant ne peut agir que sur ses propres inscriptions.
- Toute modification de données se fait en POST avec protection CSRF.