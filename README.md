# 🏫 Primary School Desk

**Primary School Desk** est une application de gestion scolaire dédiée aux établissements primaires (contexte Bénin/Afrique francophone). Elle permet de centraliser la gestion administrative et pédagogique, en remplaçant les processus papier par une solution numérique locale et efficace.

## 🚀 Fonctionnalités Principales

* **Gestion de l'Établissement :** Configuration des informations de l'école (EP, Public/Privé, Localisation).
* **Années Scolaires :** Création et activation de l'année en cours (ex: 2024-2025).
* **Gestion des Enseignants :** Suivi complet des carrières (AME, FE, ACDPE), diplômes, grades et affectations.
* **Gestion des Élèves :** Inscriptions, historique de scolarité, informations parents.
* **Pédagogie & Notes :**
  * Gestion des classes (CI au CM2).
  * Saisie des notes par évaluation (Étape 1, 2, 3).
  * **Calcul des résultats spécifique :** Logique basée sur l'atteinte du "Seuil" et le nombre de moyennes (pas de simple moyenne arithmétique).
* **Rapports :** Génération de bulletins et statistiques.

## 🛠️ Stack Technique

* **Langage :** Python 3.10+
* **Interface Utilisateur :** [Streamlit](https://streamlit.io/)
* **Base de Données :** SQLite (Local)
* **ORM :** [SQLModel](https://sqlmodel.tiangolo.com/)
* **Gestionnaire de paquets :** [Poetry](https://python-poetry.org/)

## 📂 Structure du Projet

```text
st_primary_desk/
├── app.py              # Point d'entrée de l'application
└── core/            
    └── database.py         # Configuration de la connexion SQLite 
├── models.py           # Définition des tables (Élèves, Enseignants, Notes...)
├── primary_school.db   # Fichier de base de données (généré au lancement)
├── pyproject.toml      # Fichier de configuration Poetry
├── README.md           # Documentation du projet
└── views/              # Dossier contenant les pages de l'interface
    └── settings.py     # Module de configuration (École & Années)
```


## ⚙️ Installation et Lancement

### Pré-requis

* Python installé sur votre machine.
* Poetry installé (`pip install poetry`).

### 1. Cloner ou télécharger le projet

Placez-vous dans le dossier du projet via votre terminal.

### 2. Installer les dépendances

**Bash**

```
poetry install
```

### 3. Activer l'environnement virtuel

**Bash**

```
poetry shell
```

### 4. Lancer l'application

**Bash**

```
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut (généralement à l'adresse `http://localhost:8501`).

## 📝 Utilisation (État actuel)

1. Au premier lancement, la base de données est créée automatiquement.
2. Accédez au menu  **Configuration** .
3. Remplissez les informations de votre école.
4. Créez une année scolaire (ex: "2024-2025") et cliquez sur  **Activer** .
5. Une fois l'année activée, les autres modules seront fonctionnels (En cours de développement).

## 🗺️ Feuille de route (Roadmap)

* [X] Configuration du projet et Base de données
* [X] Module Configuration (École / Années)
* [ ] Module Enseignants (CRUD complet)
* [ ] Module Classes (Ouverture des classes pour l'année)
* [ ] Module Élèves (Inscription / Enrôlement)
* [ ] Module Notes (Saisie et Calculs des seuils)
* [ ] Génération des Bulletins PDF
