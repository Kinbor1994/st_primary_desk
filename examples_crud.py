"""
Exemples d'utilisation du StudentService CRUD

Ce fichier montre comment utiliser le StudentService dans du code.
Ces exemples ne sont pas exécutables directement mais peuvent servir de référence.
"""

from datetime import date
from sqlmodel import Session
from src.core.database import engine
from src.services.student_service import StudentService
from src.models import Student, Sexe

# ============================================================================
# EXEMPLE 1: Initialiser le service
# ============================================================================

with Session(engine) as session:
    service = StudentService(session)
    
    # ... utiliser le service


# ============================================================================
# EXEMPLE 2: CREATE - Créer des élèves
# ============================================================================

with Session(engine) as session:
    service = StudentService(session)
    
    # Créer un élève simple
    student1 = service.create_student(
        matricule="2024001",
        nom="DUPONT",
        prenom="Jean",
        sexe=Sexe.MASCULIN,
        date_naissance=date(2010, 5, 15),
        lieu_naissance="Cotonou",
        nom_parent="Dupont Marie",
        contact_parent="+229 90 12 34 56",
    )
    print(f"✅ Créé: {student1.prenom} {student1.nom} (ID: {student1.id})")
    
    # Créer un élève avec tous les champs
    student2 = service.create_student(
        matricule="2024002",
        nom="martin",  # Sera converti en MARTIN
        prenom="sophie",  # Sera converti en Sophie
        sexe=Sexe.FEMININ,
        date_naissance=date(2009, 3, 22),
        lieu_naissance="porto-novo",  # Sera converti en PORTO-NOVO
        nom_parent="Martin Yves",
        contact_parent="+229 91 23 45 67",
        profession_parent="Agriculteur",
        est_orphelin=False,
        est_demuni=True,  # Marqué comme démuni
    )
    print(f"✅ Créé: {student2.prenom} {student2.nom}")
    
    # ⚠️ Gérer les erreurs (matricule dupliqué)
    try:
        duplicate = service.create_student(
            matricule="2024001",  # Déjà utilisé!
            nom="TEST",
            prenom="Test",
            sexe=Sexe.MASCULIN,
            date_naissance=date(2008, 1, 1),
            lieu_naissance="Abomey",
            nom_parent="Test Parent",
            contact_parent="90000000",
        )
    except ValueError as e:
        print(f"❌ Erreur attendue: {e}")


# ============================================================================
# EXEMPLE 3: READ - Récupérer des élèves
# ============================================================================

with Session(engine) as session:
    service = StudentService(session)
    
    # Récupérer par ID
    student = service.get_student_by_id(1)
    if student:
        print(f"📖 Élève ID 1: {student.nom} {student.prenom}")
    
    # Récupérer par matricule (unique)
    student = service.get_student_by_matricule("2024001")
    if student:
        print(f"📖 Matricule 2024001: {student.nom} {student.prenom}")
        print(f"   Date naissance: {student.date_naissance}")
        print(f"   Parent: {student.nom_parent}")
        print(f"   Contact: {student.contact_parent}")
        print(f"   Orphelin: {'✅' if student.est_orphelin else '❌'}")
        print(f"   Démuni: {'✅' if student.est_demuni else '❌'}")
    
    # Lister TOUS les élèves (triés par nom/prénom)
    all_students = service.get_all_students(order_by="nom")
    print(f"\n📋 Total d'élèves: {len(all_students)}")
    for s in all_students[:5]:
        print(f"   - {s.matricule}: {s.nom} {s.prenom}")


# ============================================================================
# EXEMPLE 4: SEARCH - Rechercher des élèves
# ============================================================================

with Session(engine) as session:
    service = StudentService(session)
    
    # Recherche textuelle (insensible à la casse)
    results = service.search_students("dupont")
    print(f"\n🔍 Résultats pour 'dupont':")
    for s in results:
        print(f"   - {s.matricule}: {s.nom} {s.prenom}")
    
    # Recherche par prénom
    results = service.search_students("jean")
    print(f"\n🔍 Résultats pour 'jean':")
    for s in results:
        print(f"   - {s.matricule}: {s.nom} {s.prenom}")
    
    # Recherche par matricule
    results = service.search_students("2024")
    print(f"\n🔍 Résultats pour '2024':")
    for s in results:
        print(f"   - {s.matricule}: {s.nom} {s.prenom}")


# ============================================================================
# EXEMPLE 5: UPDATE - Modifier des élèves
# ============================================================================

with Session(engine) as session:
    service = StudentService(session)
    
    # Modifier un seul champ
    student = service.update_student(
        student_id=1,
        contact_parent="+229 92 34 56 78"
    )
    print(f"✏️ Contact modifié: {student.contact_parent}")
    
    # Modifier plusieurs champs
    student = service.update_student(
        student_id=1,
        nom="DURAND",
        prenom="Jean-Pierre",
        profession_parent="Commerçant",
        est_demuni=True,
    )
    print(f"✏️ Élève modifié: {student.nom} {student.prenom}")
    
    # Mettre à jour par matricule (2 étapes)
    student = service.get_student_by_matricule("2024001")
    if student:
        service.update_student(
            student_id=student.id,
            nom="NOUVEAU"
        )
        print(f"✏️ Élève {student.matricule} renommé en: NOUVEAU")


# ============================================================================
# EXEMPLE 6: DELETE - Supprimer des élèves
# ============================================================================

with Session(engine) as session:
    service = StudentService(session)
    
    # Supprimer par ID
    success = service.delete_student(999)  # Supposons que cet ID existe
    if success:
        print("🗑️ Élève supprimé par ID")
    else:
        print("❌ Élève non trouvé (ID 999)")
    
    # Supprimer par matricule
    success = service.delete_by_matricule("2024999")
    if success:
        print("🗑️ Élève supprimé par matricule")
    else:
        print("❌ Élève non trouvé (matricule 2024999)")
    
    # ⚠️ La suppression efface aussi les inscriptions
    student = service.get_student_by_matricule("2024002")
    if student:
        print(f"\n🗑️ Suppression de {student.nom} {student.prenom}")
        print("   - Cette action supprimera aussi toutes ses inscriptions!")
        service.delete_student(student.id)


# ============================================================================
# EXEMPLE 7: STATISTIQUES
# ============================================================================

with Session(engine) as session:
    service = StudentService(session)
    
    # Nombre total d'élèves
    total = service.count_students()
    print(f"📊 Total d'élèves: {total}")
    
    # Élèves dans une classe
    classroom_count = service.count_students_by_classroom(classroom_id=1)
    print(f"📊 Élèves dans la classe 1: {classroom_count}")


# ============================================================================
# EXEMPLE 8: CAS D'USAGE RÉALISTE
# ============================================================================

def bulk_import_from_list(students_data):
    """
    Importe une liste d'élèves et les inscrit.
    
    Args:
        students_data: List[dict] avec clés matricule, nom, prenom, etc.
    """
    with Session(engine) as session:
        service = StudentService(session)
        
        imported = 0
        failed = 0
        
        for data in students_data:
            try:
                # Créer l'élève
                student = service.create_student(
                    matricule=data["matricule"],
                    nom=data["nom"],
                    prenom=data["prenom"],
                    sexe=Sexe(data.get("sexe", "M")),
                    date_naissance=date.fromisoformat(data["dob"]),
                    lieu_naissance=data["place_of_birth"],
                    nom_parent=data["parent_name"],
                    contact_parent=data["parent_contact"],
                    profession_parent=data.get("parent_profession"),
                    est_orphelin=data.get("orphan", False),
                    est_demuni=data.get("needy", False),
                )
                imported += 1
                print(f"✅ {data['nom']} {data['prenom']}")
                
            except ValueError as e:
                failed += 1
                print(f"❌ {data['matricule']}: {e}")
        
        print(f"\n📊 Résumé: {imported} importés, {failed} échoués")


# Utilisation
if __name__ == "__main__":
    sample_students = [
        {
            "matricule": "2024001",
            "nom": "DUPONT",
            "prenom": "Jean",
            "sexe": "M",
            "dob": "2010-05-15",
            "place_of_birth": "Cotonou",
            "parent_name": "Dupont Marie",
            "parent_contact": "90123456",
            "parent_profession": "Commerçant",
            "orphan": False,
            "needy": False,
        },
        {
            "matricule": "2024002",
            "nom": "MARTIN",
            "prenom": "Sophie",
            "sexe": "F",
            "dob": "2009-03-22",
            "place_of_birth": "Porto-Novo",
            "parent_name": "Martin Yves",
            "parent_contact": "91234567",
            "parent_profession": "Agriculteur",
            "orphan": False,
            "needy": True,
        },
    ]
    
    # bulk_import_from_list(sample_students)
