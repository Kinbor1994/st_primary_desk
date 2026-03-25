"""
Service CRUD pour la gestion des élèves.

Ce module encapsule toutes les opérations de base de données
pour les élèves (Create, Read, Update, Delete) en utilisant SQLModel.
"""

from sqlmodel import Session, select
from typing import Optional, List
from datetime import date
from src.models import Student, Enrollment, ClassRoom, AcademicYear, Sexe


class StudentService:
    """Service pour la gestion CRUD des élèves."""

    def __init__(self, session: Session):
        """Initialise le service avec une session de base de données.

        Args:
            session: Session SQLModel pour interagir avec la BD
        """
        self.session = session

    # ===== CREATE =====
    def create_student(
        self,
        matricule: str,
        nom: str,
        prenom: str,
        sexe: Sexe,
        date_naissance: date,
        lieu_naissance: str,
        nom_parent: str,
        contact_parent: str,
        profession_parent: Optional[str] = None,
        est_orphelin: bool = False,
        est_demuni: bool = False,
    ) -> Student:
        """Crée un nouvel élève.

        Args:
            matricule: Matricule unique de l'élève
            nom: Nom de l'élève
            prenom: Prénom de l'élève
            sexe: Sexe (M ou F)
            date_naissance: Date de naissance
            lieu_naissance: Lieu de naissance
            nom_parent: Nom du parent/tuteur
            contact_parent: Contact du parent/tuteur
            profession_parent: Profession du parent (optionnel)
            est_orphelin: Booléen indiquant si l'élève est orphelin
            est_demuni: Booléen indiquant si l'élève est démuni

        Returns:
            L'objet Student créé

        Raises:
            ValueError: Si le matricule existe déjà
        """
        # Vérifier que le matricule est unique
        existing = self.session.exec(
            select(Student).where(Student.matricule == matricule)
        ).first()
        if existing:
            raise ValueError(f"Un élève avec le matricule '{matricule}' existe déjà.")

        student = Student(
            matricule=matricule,
            nom=nom.strip().upper(),
            prenom=prenom.strip().title(),
            sexe=sexe,
            date_naissance=date_naissance,
            lieu_naissance=lieu_naissance.strip().upper(),
            nom_parent=nom_parent.strip(),
            contact_parent=contact_parent.strip(),
            profession_parent=profession_parent.strip() if profession_parent else None,
            est_orphelin=est_orphelin,
            est_demuni=est_demuni,
        )
        self.session.add(student)
        self.session.commit()
        self.session.refresh(student)
        return student

    # ===== READ =====
    def get_student_by_id(self, student_id: int) -> Optional[Student]:
        """Récupère un élève par son ID.

        Args:
            student_id: ID de l'élève

        Returns:
            L'objet Student ou None s'il n'existe pas
        """
        return self.session.exec(
            select(Student).where(Student.id == student_id)
        ).first()

    def get_student_by_matricule(self, matricule: str) -> Optional[Student]:
        """Récupère un élève par son matricule.

        Args:
            matricule: Matricule de l'élève

        Returns:
            L'objet Student ou None s'il n'existe pas
        """
        return self.session.exec(
            select(Student).where(Student.matricule == matricule)
        ).first()

    def get_all_students(self, order_by: str = "nom") -> List[Student]:
        """Récupère tous les élèves.

        Args:
            order_by: Colonne pour le tri (par défaut: nom)

        Returns:
            Liste de tous les élèves triés
        """
        query = select(Student)

        if order_by == "nom":
            query = query.order_by(Student.nom, Student.prenom)
        elif order_by == "matricule":
            query = query.order_by(Student.matricule)
        elif order_by == "date_naissance":
            query = query.order_by(Student.date_naissance)

        return self.session.exec(query).all()

    def get_students_by_classroom(
        self, classroom_id: int, academic_year_id: Optional[int] = None
    ) -> List[tuple]:
        """Récupère tous les élèves inscrits dans une classe.

        Args:
            classroom_id: ID de la classe
            academic_year_id: ID de l'année scolaire (optionnel, pour filtrage)

        Returns:
            Liste de tuples (Student, Enrollment)
        """
        query = (
            select(Student, Enrollment)
            .join(Enrollment)
            .where(Enrollment.classroom_id == classroom_id)
        )

        if academic_year_id:
            query = query.join(ClassRoom).where(
                ClassRoom.academic_year_id == academic_year_id
            )

        return self.session.exec(query).all()

    def search_students(self, search_term: str) -> List[Student]:
        """Recherche des élèves par nom, prénom ou matricule.

        Args:
            search_term: Terme de recherche

        Returns:
            Liste des élèves correspondant à la recherche
        """
        search_term = f"%{search_term.strip().upper()}%"
        return self.session.exec(
            select(Student).where(
                (Student.matricule.ilike(search_term))
                | (Student.nom.ilike(search_term))
                | (Student.prenom.ilike(search_term))
            )
        ).all()

    # ===== UPDATE =====
    def update_student(
        self,
        student_id: int,
        nom: Optional[str] = None,
        prenom: Optional[str] = None,
        sexe: Optional[Sexe] = None,
        date_naissance: Optional[date] = None,
        lieu_naissance: Optional[str] = None,
        nom_parent: Optional[str] = None,
        contact_parent: Optional[str] = None,
        profession_parent: Optional[str] = None,
        est_orphelin: Optional[bool] = None,
        est_demuni: Optional[bool] = None,
    ) -> Optional[Student]:
        """Met à jour les informations d'un élève.

        Args:
            student_id: ID de l'élève à modifier
            nom: Nouveau nom (optionnel)
            prenom: Nouveau prénom (optionnel)
            sexe: Nouveau sexe (optionnel)
            date_naissance: Nouvelle date de naissance (optionnel)
            lieu_naissance: Nouveau lieu de naissance (optionnel)
            nom_parent: Nouveau nom du parent (optionnel)
            contact_parent: Nouveau contact du parent (optionnel)
            profession_parent: Nouvelle profession du parent (optionnel)
            est_orphelin: Mise à jour du statut orphelin (optionnel)
            est_demuni: Mise à jour du statut demuni (optionnel)

        Returns:
            L'objet Student mis à jour ou None s'il n'existe pas
        """
        student = self.get_student_by_id(student_id)
        if not student:
            return None

        # Mise à jour des champs fournis
        if nom is not None:
            student.nom = nom.strip().upper()
        if prenom is not None:
            student.prenom = prenom.strip().title()
        if sexe is not None:
            student.sexe = sexe
        if date_naissance is not None:
            student.date_naissance = date_naissance
        if lieu_naissance is not None:
            student.lieu_naissance = lieu_naissance.strip().upper()
        if nom_parent is not None:
            student.nom_parent = nom_parent.strip()
        if contact_parent is not None:
            student.contact_parent = contact_parent.strip()
        if profession_parent is not None:
            student.profession_parent = (
                profession_parent.strip() if profession_parent else None
            )
        if est_orphelin is not None:
            student.est_orphelin = est_orphelin
        if est_demuni is not None:
            student.est_demuni = est_demuni

        self.session.add(student)
        self.session.commit()
        self.session.refresh(student)
        return student

    # ===== DELETE =====
    def delete_student(self, student_id: int) -> bool:
        """Supprime un élève et ses inscriptions.

        Args:
            student_id: ID de l'élève à supprimer

        Returns:
            True si la suppression a réussi, False sinon
        """
        student = self.get_student_by_id(student_id)
        if not student:
            return False

        # Supprimer les inscriptions associées
        enrollments = self.session.exec(
            select(Enrollment).where(Enrollment.student_id == student_id)
        ).all()
        for enrollment in enrollments:
            self.session.delete(enrollment)

        # Supprimer l'élève
        self.session.delete(student)
        self.session.commit()
        return True

    def delete_by_matricule(self, matricule: str) -> bool:
        """Supprime un élève par son matricule.

        Args:
            matricule: Matricule de l'élève à supprimer

        Returns:
            True si la suppression a réussi, False sinon
        """
        student = self.get_student_by_matricule(matricule)
        if not student:
            return False
        return self.delete_student(student.id)

    # ===== STATISTIQUES =====
    def count_students(self) -> int:
        """Compte le nombre total d'élèves.

        Returns:
            Nombre d'élèves
        """
        return self.session.exec(select(Student)).all().__len__()

    def count_students_by_classroom(self, classroom_id: int) -> int:
        """Compte le nombre d'élèves dans une classe.

        Args:
            classroom_id: ID de la classe

        Returns:
            Nombre d'élèves inscrits
        """
        return (
            self.session.exec(
                select(Enrollment).where(Enrollment.classroom_id == classroom_id)
            )
            .all()
            .__len__()
        )
