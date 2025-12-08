import streamlit as st
from sqlmodel import select, Session
import pandas as pd # <-- NOUVEL IMPORT
from io import BytesIO # <-- NOUVEL IMPORT

from src.models import SchoolInfo, AcademicYear, NiveauEcole, StatutEcole

# --- FONCTION DE GESTION DES FICHIERS ---

def download_import_template():
    """Crée et propose au téléchargement un fichier Excel modèle pour l'importation des élèves."""
    
    # Définition des entêtes de colonnes exactes
    columns = [
        "MATRICULE", 
        "NOM", 
        "PRENOM", 
        "SEXE (M/F)", 
        "DATE_NAISSANCE (YYYY-MM-DD)", 
        "LIEU_NAISSANCE", 
        "NOM_PARENT", 
        "CONTACT_PARENT", 
        "PROFESSION_PARENT", 
        "ORPHELIN (VRAI/FAUX)", 
        "DEMUNI (VRAI/FAUX)"
    ]
    
    # Création d'un DataFrame vide
    df = pd.DataFrame(columns=columns)
    
    # Création du buffer pour le fichier
    output = BytesIO()
    # Utilisation de XlsxWriter comme moteur pour gérer les fichiers Excel (.xlsx)
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Eleves')
    
    processed_data = output.getvalue()
    
    return processed_data


def settings_view(session: Session):
    st.header("⚙️ Configuration de l'établissement")

    # On utilise des onglets pour séparer les infos de l'école et les années scolaires et l'outil
    # AJOUT DU NOUVEL ONGLETS: OUTILS
    tab1, tab2, tab3 = st.tabs(["🏫 Informations École", "📅 Années Scolaires", "🔗 Outils d'Importation"]) 

    # --- ONGLET 1 : INFOS ÉCOLE ---
    with tab1:
        # ... (Le code existant pour SchoolInfo) ...
        school_info = session.exec(select(SchoolInfo)).first()
        
        # Si ça n'existe pas, on crée une instance vide pour le formulaire
        if not school_info:
            school_info = SchoolInfo(
                nom="", departement="", commune="", arrondissement="", village="", 
                statut=StatutEcole.PUBLIC, niveau=NiveauEcole.EP
            )

        with st.form("school_info_form"):
            col1, col2 = st.columns(2)
            # ... (Le reste du formulaire) ...
            with col1:
                nom = st.text_input("Nom de l'école", value=school_info.nom)
                niveau = st.selectbox("Niveau", [e.value for e in NiveauEcole], index=[e.value for e in NiveauEcole].index(school_info.niveau.value) if school_info.niveau else 0)
                statut = st.selectbox("Statut", [e.value for e in StatutEcole], index=[e.value for e in StatutEcole].index(school_info.statut.value) if school_info.statut else 0)
                handicap = st.checkbox("École pour handicapés", value=school_info.est_ecole_handicape)
                contact = st.text_input("Contact Directeur", value=school_info.contact_directeur or "")
            
            with col2:
                dept = st.text_input("Département", value=school_info.departement)
                commune = st.text_input("Commune", value=school_info.commune)
                arrond = st.text_input("Arrondissement", value=school_info.arrondissement)
                village = st.text_input("Village", value=school_info.village)

            submitted = st.form_submit_button("Enregistrer les informations")

            if submitted:
                # Mise à jour des champs de l'objet
                school_info.nom = nom
                school_info.niveau = NiveauEcole(niveau)
                school_info.statut = StatutEcole(statut)
                school_info.est_ecole_handicape = handicap
                school_info.departement = dept
                school_info.commune = commune
                school_info.arrondissement = arrond
                school_info.village = village
                school_info.contact_directeur = contact

                session.add(school_info)
                session.commit()
                session.refresh(school_info)
                st.success("Informations de l'école mises à jour avec succès !")
                
    # --- ONGLET 2 : ANNÉES SCOLAIRES ---
    with tab2:
        # ... (Le code existant pour AcademicYear) ...
        st.subheader("Gestion des années scolaires")
        
        # 1. Formulaire d'ajout (inchangé)
        with st.form("add_year_form", clear_on_submit=True):
            new_year_name = st.text_input("Nouvelle année scolaire (ex: 2024-2025)")
            submitted_year = st.form_submit_button("Ajouter l'année")
            
            if submitted_year and new_year_name:
                existing = session.exec(select(AcademicYear).where(AcademicYear.nom == new_year_name)).first()
                if existing:
                    st.error("Cette année existe déjà.")
                else:
                    new_year = AcademicYear(nom=new_year_name, active=False)
                    session.add(new_year)
                    session.commit()
                    st.success(f"Année {new_year_name} ajoutée.")
                    st.rerun()

        st.divider()

        # 2. Liste et Activation (inchangée)
        years = session.exec(select(AcademicYear).order_by(AcademicYear.nom.desc())).all()
        
        if years:
            st.write("Liste des années enregistrées :")
            for year in years:
                col_a, col_b, col_c = st.columns([3, 2, 2])
                with col_a:
                    st.write(f"**{year.nom}**")
                with col_b:
                    if year.active:
                        st.success("✅ ACTIVE")
                    else:
                        st.write("Inactif")
                with col_c:
                    if not year.active:
                        if st.button(f"Activer {year.nom}", key=f"btn_{year.id}"):
                            # Désactiver toutes les années
                            all_years = session.exec(select(AcademicYear)).all()
                            for y in all_years:
                                y.active = False
                                session.add(y)
                            
                            # Activer l'année choisie
                            year.active = True
                            session.add(year)
                            session.commit()
                            st.rerun()
        else:
            st.info("Aucune année scolaire configurée pour le moment.")
            
            
    # --- NOUVEL ONGLET 3 : OUTILS D'IMPORTATION ---
    with tab3:
        st.subheader("Téléchargement du Modèle d'Importation Élèves")
        st.write("Utilisez ce modèle pour garantir la bonne structure de votre fichier Excel avant l'importation.")
        
        template_file = download_import_template()
        
        st.download_button(
            label="Télécharger le Modèle Élèves (.xlsx)",
            data=template_file,
            file_name="modele_importation_eleves.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Ce fichier contient les en-têtes exacts requis par l'application."
        )