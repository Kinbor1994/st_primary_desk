import streamlit as st
from sqlmodel import select, Session
import pandas as pd
from src.models import ClassRoom, ClasseNiveau, Teacher, AcademicYear

def classes_view(session: Session):
    st.header("📚 Gestion des Classes et Affectations")
    
    active_year = session.exec(select(AcademicYear).where(AcademicYear.active == True)).first()
    
    if not active_year:
        st.warning("⚠️ Veuillez activer une année scolaire dans la section Configuration avant de gérer les classes.")
        return

    st.info(f"Année scolaire active : **{active_year.nom}**")
    
    # Récupérer tous les enseignants
    all_teachers = session.exec(select(Teacher)).all()
    # Dictionnaire de mapping {ID: Nom Prénom (Matricule)} pour le selectbox
    teacher_options = {t.id: f"{t.nom} {t.prenom} ({t.matricule})" for t in all_teachers}
    
    # Enseignants déjà affectés cette année (pour l'exclusion)
    affected_teachers_ids = [c.teacher_id for c in session.exec(
        select(ClassRoom).where(ClassRoom.academic_year_id == active_year.id)
    ).all()]

    # Création des options d'enseignants disponibles pour une nouvelle affectation
    available_teachers_options = {
        tid: name for tid, name in teacher_options.items() if tid not in affected_teachers_ids
    }
    
    # --- FORMULAIRE D'OUVERTURE DE CLASSE ---
    st.subheader("Ouverture d'une Nouvelle Classe")
    with st.form("open_class_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Niveau de classe (CI, CP, etc.)
            niveau = st.selectbox("Niveau de la classe", [e.value for e in ClasseNiveau])
            # Nom interne (pour différencier CI A de CI B si nécessaire, par défaut = niveau)
            nom_interne = st.text_input("Nom Interne (optionnel)", value=niveau, help="Ex: 'CI A' ou juste 'CI'")

        with col2:
            # Sélecteur d'enseignant
            # Ajout d'une option pour choisir 'Aucun enseignant'
            teachers_list_keys = list(available_teachers_options.keys())
            teachers_list_names = list(available_teachers_options.values())
            
            # Index 0 pour "Choisir un enseignant..."
            teachers_list_names.insert(0, "--- Choisir un enseignant (Principal) ---")
            
            selected_teacher_name = st.selectbox(
                "Enseignant responsable (Affectation)", 
                options=teachers_list_names
            )
            
            # Récupération de l'ID de l'enseignant sélectionné
            selected_teacher_id = None
            if selected_teacher_name != "--- Choisir un enseignant (Principal) ---":
                # Trouver l'ID correspondant au nom sélectionné
                selected_teacher_id = next((tid for tid, name in available_teachers_options.items() if name == selected_teacher_name), None)

        submitted = st.form_submit_button("Créer et Affecter la Classe")

        if submitted:
            # Vérification de l'unicité (on ne peut avoir qu'une seule instance de CI A par an)
            existing_class = session.exec(
                select(ClassRoom).where(
                    ClassRoom.academic_year_id == active_year.id,
                    ClassRoom.nom_interne == nom_interne.upper()
                )
            ).first()

            if existing_class:
                st.error(f"Une classe nommée '{nom_interne}' existe déjà pour l'année {active_year.nom}.")
            else:
                new_class = ClassRoom(
                    academic_year_id=active_year.id,
                    niveau=ClasseNiveau(niveau),
                    nom_interne=nom_interne.upper(),
                    teacher_id=selected_teacher_id # Peut être None si pas d'affectation
                )
                session.add(new_class)
                session.commit()
                st.success(f"La classe **{nom_interne.upper()}** a été créée et affectée.")
                st.rerun()

    st.divider()

    # --- LISTE DES CLASSES OUVERTES ---
    st.subheader(f"Liste des classes ouvertes pour l'année {active_year.nom}")
    
    classes = session.exec(
        select(ClassRoom).where(ClassRoom.academic_year_id == active_year.id)
    ).all()
    
    if classes:
        # Construction des données d'affichage
        display_data = []
        for class_item in classes:
            teacher_name = "NON AFFECTÉ"
            if class_item.teacher_id:
                # Jointure manuelle pour obtenir le nom de l'enseignant
                teacher = session.get(Teacher, class_item.teacher_id)
                if teacher:
                    teacher_name = f"{teacher.nom} {teacher.prenom}"
                    
            display_data.append({
                "Nom Interne": class_item.nom_interne,
                "Enseignant Responsable": teacher_name,
            })

        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    else:
        st.info("Aucune classe n'a été ouverte pour cette année scolaire.")