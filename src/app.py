import streamlit as st
import sys
from pathlib import Path
from sqlmodel import Session, select

# Assure que le dossier racine du projet est dans sys.path afin que
# l'import absolu `src.core.database` fonctionne lors de l'exécution
# via `streamlit run src/app.py` (Streamlit lance le script comme __main__).
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.database import create_db_and_tables, engine
from src.models import SchoolInfo, AcademicYear

# Import des vues (pages)
from src.views.settings import settings_view

# Configuration de la page
st.set_page_config(page_title="Primary School Desk", layout="wide", page_icon="🏫")

# Initialisation de la DB
create_db_and_tables()


# Fonction pour récupérer la session DB
def get_session():
    return Session(engine)


# --- SIDEBAR (Navigation) ---
st.sidebar.title("🏫 Primary Desk")

# Vérification rapide : A-t-on une école et une année active ?
with Session(engine) as session:
    school = session.exec(select(SchoolInfo)).first()
    active_year = session.exec(
        select(AcademicYear).where(AcademicYear.active == True)
    ).first()

    # Affichage contextuel dans la sidebar
    if school:
        st.sidebar.info(f"📍 {school.nom}")
    if active_year:
        st.sidebar.success(f"📅 Année : {active_year.nom}")
    else:
        st.sidebar.warning("⚠️ Aucune année active")

    st.sidebar.divider()

    # Menu
    menu = st.sidebar.radio(
        "Navigation",
        ["Tableau de bord", "Élèves", "Enseignants", "Evaluations", "Configuration"],
    )

# --- CORPS DE LA PAGE ---
with Session(engine) as session:
    if menu == "Configuration":
        settings_view(session)

    elif menu == "Tableau de bord":
        st.title("Tableau de bord")
        st.write("Bienvenue dans le gestionnaire scolaire.")
        if not active_year:
            st.warning(
                "👉 Veuillez aller dans 'Configuration' pour activer une année scolaire."
            )
        else:
            st.write("Sélectionnez un menu à gauche pour commencer.")

    elif menu == "Élèves":
        st.title("Gestion des Élèves")
        st.info("Module en construction...")

    elif menu == "Enseignants":
        st.title("Gestion des Enseignants")
        st.info("Module en construction...")

    elif menu == "Evaluations":
        st.title("Gestion des Notes")
        st.info("Module en construction...")
