# 📚 Documentation CRUD des Élèves

## Vue d'ensemble

L'implémentation CRUD des élèves fournit une gestion complète des données des élèves avec création, lecture, modification et suppression. Elle est articulée autour d'une **architecture en 2 couches** :

1. **Service Layer** (`src/services/student_service.py`) - Logique métier
2. **Presentation Layer** (`src/views/students.py`) - Interface Streamlit

---

## Architecture

### Service Class: `StudentService`

Le `StudentService` encapsule toute la logique d'accès aux données et validations métier.

#### Initialisation

```python
from sqlmodel import Session
from src.services.student_service import StudentService

# Utilisation dans une route/vue
with Session(engine) as session:
    service = StudentService(session)
    # ... utiliser le service
```

---

## Opérations CRUD

### ✨ CREATE - Créer un élève

```python
student = service.create_student(
    matricule="MAT001",
    nom="Dupont",
    prenom="Jean",
    sexe=Sexe.MASCULIN,
    date_naissance=date(2010, 5, 15),
    lieu_naissance="Cotonou",
    nom_parent="Dupont Marie",
    contact_parent="90123456",
    profession_parent="Commerçant",
    est_orphelin=False,
    est_demuni=False
)
```

**Validations** :
- ✅ Le matricule doit être unique (lève `ValueError` sinon)
- ✅ Le nom est automatiquement converti en MAJUSCULES
- ✅ Le prénom est converti en Titre Case
- ✅ Les contacts inutiles sont strippés

**Retour** : `Student` créé et persisté dans la DB

---

### 📖 READ - Lire les données

#### Récupérer un élève par ID

```python
student = service.get_student_by_id(1)
```

#### Récupérer par matricule (unique)

```python
student = service.get_student_by_matricule("MAT001")
```

#### Lister tous les élèves

```python
students = service.get_all_students(order_by="nom")
# order_by options: "nom", "matricule", "date_naissance"
```

#### Élèves par classe

```python
# Retourne des tuples (Student, Enrollment)
enrollments = service.get_students_by_classroom(
    classroom_id=5,
    academic_year_id=1  # optionnel
)
```

#### Recherche textuelle

```python
# Recherche dans matricule, nom, prénom
results = service.search_students("dupont")
```

---

### ✏️ UPDATE - Modifier un élève

```python
updated = service.update_student(
    student_id=1,
    nom="Durand",
    prenom="Jean-Pierre",
    contact_parent="91234567"
    # Les autres champs restent inchangés
)
```

**Options** :
- ✅ Mise à jour sélective (ne modifier que ce qui est fourni)
- ✅ Tous les champs sont optionnels
- ✅ Les validations de formatage s'appliquent

---

### 🗑️ DELETE - Supprimer un élève

#### Par ID

```python
success = service.delete_student(1)
# Retourne True/False
```

#### Par matricule

```python
success = service.delete_by_matricule("MAT001")
```

**Comportement** :
- ✅ Supprime l'élève ET toutes ses inscriptions (Enrollments)
- ✅ Retourne `True` si succès, `False` si élève introuvable

---

### 📊 STATISTIQUES

```python
# Nombre total d'élèves
count = service.count_students()

# Élèves dans une classe spécifique
count = service.count_students_by_classroom(classroom_id=5)
```

---

## Interface Streamlit

L'interface est organisée en **4 onglets** :

### Onglet 1️⃣ : **Ajouter Élève**

Formulaire pour créer un nouvel élève et l'inscrire dans une classe.

**Flux** :
1. Remplir le formulaire
2. Sélectionner la classe d'inscription
3. Cliquer "✅ Créer l'élève"
4. L'élève et l'inscription sont créés atomiquement

**Validations** :
- ✅ Tous les champs obligatoires doivent être remplis
- ✅ Message spécifique si matricule déjà existe

---

### Onglet 2️⃣ : **Liste des Élèves**

Affichage et recherche des élèves.

**Fonctionnalités** :
- 🔍 Recherche par nom, prénom ou matricule
- 📋 Filtrer par classe ou afficher tous
- 📊 Tableau avec colonnes : Matricule, Nom & Prénoms, Sexe, Date Naissance, Parent, Contact, Statuts (Orphelin/Démuni)

---

### Onglet 3️⃣ : **Modifier/Supprimer**

Recherche individuelle et modification d'un élève.

**Flux** :
1. Entrer le matricule de l'élève
2. Choisir l'action :
   - **Afficher** : Vue synthétique des infos
   - **Modifier** : Formulaire de modification
   - **Supprimer** : Supression avec confirmation

---

### Onglet 4️⃣ : **Importer Excel**

Import en masse depuis fichier Excel/CSV.

**Format attendu** :
Colonnes obligatoires dans le fichier :
```
MATRICULE | NOM | PRENOM | SEXE | DATE_NAISSANCE | LIEU_NAISSANCE | NOM_PARENT | CONTACT_PARENT
```

Colonnes optionnelles :
```
PROFESSION_PARENT | ORPHELIN | DEMUNI
```

**Valeurs booléennes** : "VRAI" ou "FAUX" (insensible à la casse)

**Exemple** :
| MATRICULE | NOM | PRENOM | SEXE | DATE_NAISSANCE | LIEU_NAISSANCE | NOM_PARENT | CONTACT_PARENT |
|-----------|-----|--------|----- |-----------------|----------------------|------------|------------|
| MAT001 | DUPONT | Jean | M | 2010-05-15 | Cotonou | Dupont Marie | 90123456 |
| MAT002 | MARTIN | Sophie | F | 2009-03-22 | Porto-Novo | Martin Yves | 91234567 |

**Traitement** :
- ✅ Détecte les doublons et les ignore
- ✅ Valide les dates
- ✅ Crée puis inscrit automatiquement
- ✅ Rapport détaillé avec comptages

---

## Gestion des Erreurs

Tous les services lèvent des exceptions appropriées :

```python
try:
    student = service.create_student(
        matricule="MAT001",  # Existe déjà!
        ...
    )
except ValueError as e:
    print(f"Erreur : {e}")  # "Un élève avec le matricule 'MAT001' existe déjà."
```

---

## Bonnes Pratiques

### ✅ À faire

```python
# ✅ Créer avec validation
student = service.create_student(
    matricule="MAT001",
    nom="Dupont",
    sexe=Sexe.MASCULIN,
    ...
)

# ✅ Rechercher avant de modifier
student = service.get_student_by_matricule("MAT001")
if student:
    service.update_student(student.id, nom="Durand")

# ✅ Vérifier le succès de la suppression
if service.delete_student(1):
    print("Suppression réussie")
else:
    print("Élève non trouvé")
```

### ❌ À éviter

```python
# ❌ Accès direct à la DB sans service
session.add(Student(...))  # Pas de validation!

# ❌ Créer des élèves sans les inscrire
service.create_student(...)  # OK, mais pensez à créer Enrollment après!

# ❌ Supposer que la suppression réussit
service.delete_student(999)  # Pourrait être invisible
```

---

## Extension / Personnalisation

### Ajouter une nouvelle méthode

Pour ajouter une opération personnalisée, ajoutez-la à `StudentService` :

```python
def get_students_by_status(self, est_orphelin: bool) -> List[Student]:
    """Récupère tous les élèves orphelins (ou non)."""
    return self.session.exec(
        select(Student).where(Student.est_orphelin == est_orphelin)
    ).all()
```

### Modifier la UI

Pour personnaliser l'interface, modifiez les sections correspondantes dans `views/students.py` :

```python
# Dans tab_create:
# Ajouter des champs supplémentaires
other_field = st.text_input("Mon champ personnalisé")
```

---

## Considérations de Performance

- **Indexing** : Les champs `matricule` sont indexés pour les recherches rapides
- **Query Optimization** : Les jointures utilisent `select().join()` pour l'efficacité
- **Batch Operations** : L'import traite les fichiers ligne par ligne avec commits

---

## Limitations Actuelles et Améliorations Futures

| Limitation | Solution Possible |
|-----------|-------------------|
| Pas d'historique des modifications | Ajouter `created_at`, `updated_at`, table audit |
| Pas de soft delete | Ajouter colonne `deleted_at` |
| Recherche simple (texte) | Ajouter filtres avancés/facettes |
| Bulk operations de BD | Ajouter service d'export/rapport |

---

## Support

Pour questions/bugs concernant le CRUD :
1. Consultez les logs Streamlit
2. Vérifiez le format des dates (YYYY-MM-DD)
3. Validez le fichier Excel avant l'import
