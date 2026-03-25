from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import date
from enum import Enum

# --- ENUMS (Listes de choix fixes) ---


class Sexe(str, Enum):
    MASCULIN = "M"
    FEMININ = "F"


class NiveauEcole(str, Enum):
    EP = "EP"  # Ecole Primaire
    EM = "EM"  # Ecole Maternelle


class StatutEcole(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVE = "PRIVE"


class StatutEnseignant(str, Enum):
    AME = "AME"
    ACDPE = "ACDPE"
    FE = "FE"
    VACATAIRE = "VACATAIRE"


class FonctionEnseignant(str, Enum):
    DIRECTEUR = "Directeur/Directrice"
    ADJOINT = "Adjoint/Adjointe"


class ClasseNiveau(str, Enum):
    CI = "CI"
    CP = "CP"
    CE1 = "CE1"
    CE2 = "CE2"
    CM1 = "CM1"
    CM2 = "CM2"


class EvaluationEtape(str, Enum):
    ETAPE_1 = "Etape 1"
    ETAPE_2 = "Etape 2"
    ETAPE_3 = "Etape 3"


# --- MODÈLES (Tables) ---


class SchoolInfo(SQLModel, table=True):
    """Informations générales de l'établissement (Ligne unique en théorie)"""

    __tablename__ = "schoolinfo"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
    niveau: str = Field(default="EP")
    statut: str
    est_ecole_handicape: bool = Field(default=False)
    departement: str
    commune: str
    arrondissement: str
    village: str
    contact_directeur: Optional[str] = None


class AcademicYear(SQLModel, table=True):
    """Gestion des années scolaires (ex: 2024-2025)"""

    __tablename__ = "academicyear"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str = Field(unique=True)  # ex: "2024-2025"
    active: bool = Field(default=False)  # Une seule active à la fois


class Teacher(SQLModel, table=True):
    """Dossier complet de l'enseignant"""

    __tablename__ = "teacher"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    matricule: str = Field(unique=True, index=True)
    id_anpe: Optional[str] = None  # Pour les AME
    nom: str
    prenom: str
    sexe: str
    date_naissance: date
    lieu_naissance: str
    adresse: Optional[str] = None
    telephone: str
    nationalite: str = "Béninoise"
    ifu: Optional[str] = None
    date_prise_service: Optional[date] = None

    # Carrière
    statut: str
    corps_actuel: str  # Instituteur, etc.
    diplome_académique: str  # BAC, Licence...
    annee_obtention_diplome: Optional[int] = None
    grade: Optional[str] = None  # B1-4

    # Situation
    situation_matrimoniale: str = "Célibataire"
    anciennete_fonction_publique: int = 0
    anciennete_ecole: int = 0


class Student(SQLModel, table=True):
    """Dossier de l'élève"""

    __tablename__ = "student"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    matricule: str = Field(unique=True, index=True)
    nom: str
    prenom: str
    sexe: str
    date_naissance: date
    lieu_naissance: str
    nom_parent: str
    contact_parent: str
    profession_parent: Optional[str] = None
    est_orphelin: bool = Field(default=False)
    est_demuni: bool = Field(default=False)


class ClassRoom(SQLModel, table=True):
    """Une classe ouverte pour une année spécifique (ex: Le CI de 2024-2025)"""

    __tablename__ = "classroom"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    academic_year_id: int = Field(foreign_key="academicyear.id")
    teacher_id: Optional[int] = Field(foreign_key="teacher.id", default=None)
    niveau: str

    # Nom customisable si besoin (ex: CI A, CI B) sinon juste "CI"
    nom_interne: str


class Enrollment(SQLModel, table=True):
    """L'inscription d'un élève dans une classe pour une année (Enrolement)"""

    __tablename__ = "enrollment"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    classroom_id: int = Field(foreign_key="classroom.id")
    date_inscription: date = Field(default_factory=date.today)


class Grade(SQLModel, table=True):
    """Notes pour une évaluation spécifique"""

    __tablename__ = "grade"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    enrollment_id: int = Field(foreign_key="enrollment.id")
    evaluation: str

    # Matières (Structure plate comme demandée)
    note_ce: Optional[float] = None  # Compréhension Ecrit
    note_ee: Optional[float] = None  # Expression Ecrite
    note_co: Optional[float] = None  # Communication Orale
    note_dictee: Optional[float] = None  # Dictée
    note_dessin: Optional[float] = None  # Dessin
    note_ea_oral: Optional[float] = None  # Chant/Poésie/Conte
    note_eps: Optional[float] = None  # EPS
    note_es: Optional[float] = None  # Education Sociale
    note_est: Optional[float] = None  # EST
    note_math: Optional[float] = None  # Mathématique


class TermAverage(SQLModel, table=True):
    """Résultats calculés par période"""

    __tablename__ = "termaverage"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    enrollment_id: int = Field(foreign_key="enrollment.id")
    evaluation: str

    total_moyenne: int  # Nb matières >= 10
    total_note: int  # Nb total matières (souvent 9)
    total_points: float  # Somme des notes
    rang: int
    decision: str  # A ATTEINT LE SEUIL / N'A PAS ATTEINT


class FinalResult(SQLModel, table=True):
    """Résultat de fin d'année"""

    __tablename__ = "finalresult"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    enrollment_id: int = Field(foreign_key="enrollment.id")

    moyenne_1: int  # Total moyenne Etape 1
    rang_1: int
    moyenne_2: int
    rang_2: int
    moyenne_3: int
    rang_3: int

    moyenne_final: int  # Nb de fois seuil atteint (0, 1, 2 ou 3)
    rang_final: int
    decision_finale: str  # PASSE / REDOUBLE
