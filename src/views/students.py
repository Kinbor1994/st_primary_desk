import streamlit as st
from sqlmodel import select, Session
import pandas as pd
from datetime import date
import re  # Pour les vérifications de format

from src.models import Student, Enrollment, Sexe, AcademicYear, ClassRoom


def students_view(session: Session):
    st.header("👤 Gestion des Élèves et Inscriptions")

    # 1. Vérification de l'année scolaire active (Essentiel pour l'Enrollement)
    active_year = session.exec(
        select(AcademicYear).where(AcademicYear.active == True)
    ).first()
    if not active_year:
        st.warning(
            "⚠️ Veuillez activer une année scolaire dans la section Configuration."
        )
        return

    st.info(f"Année scolaire active : **{active_year.nom}**")

    # 2. Récupération des classes ouvertes pour l'inscription
    classes = session.exec(
        select(ClassRoom).where(ClassRoom.academic_year_id == active_year.id)
    ).all()

    if not classes:
        st.error(
            "❌ Aucune classe n'est ouverte pour cette année. Veuillez créer des classes avant d'inscrire des élèves."
        )
        return

    class_map = {f"{c.niveau.value}": c.id for c in classes}
    class_names = list(class_map.keys())

    # --- ONGLET 1 : IMPORTATION EXCEL ---
    tab_import, tab_list = st.tabs(
        ["⬆️ Importer Fichier Excel", "📋 Liste et Enrôlement"]
    )

    with tab_import:
        st.subheader("Importation des Données Élèves")
        st.caption(
            "Téléchargez un fichier Excel (.xlsx ou .csv) contenant les colonnes obligatoires (MATRICULE, NOM, PRENOM, etc.)."
        )

        uploaded_file = st.file_uploader(
            "Choisir un fichier d'élèves", type=["xlsx", "csv"]
        )

        selected_class_name = st.selectbox(
            "Classe d'Inscription (Enrollment)",
            options=class_names,
            help="Tous les élèves du fichier seront inscrits dans cette classe pour l'année active.",
        )

        # Le bouton d'importation est placé après le sélecteur de classe
        if uploaded_file:
            if st.button("Lancer l'Importation et l'Inscription"):
                # Déterminer le format du fichier
                if uploaded_file.name.endswith(".csv"):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)

                # Nettoyage des noms de colonnes (majuscules pour la robustesse)
                df.columns = [col.upper().replace(" ", "_") for col in df.columns]

                required_cols = [
                    "MATRICULE",
                    "NOM",
                    "PRENOM",
                    "SEXE",
                    "DATE_NAISSANCE",
                    "LIEU_NAISSANCE",
                    "NOM_PARENT",
                    "CONTACT_PARENT",
                ]

                if not all(col in df.columns for col in required_cols):
                    st.error(
                        "Erreur: Le fichier doit contenir au moins les colonnes obligatoires."
                    )
                    return

                total_imported = 0
                total_enrolled = 0
                class_id_to_enroll = class_map[selected_class_name]

                with st.spinner("Traitement des données..."):

                    for index, row in df.iterrows():
                        matricule = str(row["MATRICULE"]).strip()

                        # 1. Vérification/Création de l'élève (Student)
                        student = session.exec(
                            select(Student).where(Student.matricule == matricule)
                        ).first()

                        is_new_student = False

                        try:
                            birth_date = pd.to_datetime(row["DATE_NAISSANCE"]).date()
                        except:
                            st.warning(
                                f"Ligne {index+2} ({matricule}) : Date de naissance invalide. Élève ignoré."
                            )
                            continue

                        if not student:
                            # Création du nouvel élève
                            is_new_student = True
                            student = Student(
                                matricule=matricule,
                                nom=str(row["NOM"]).strip().upper(),
                                prenom=str(row["PRENOM"]).strip().title(),
                                sexe=Sexe(str(row["SEXE"]).strip().upper()),
                                date_naissance=birth_date,
                                lieu_naissance=str(row["LIEU_NAISSANCE"])
                                .strip()
                                .upper(),
                                nom_parent=str(row["NOM_PARENT"]).strip(),
                                contact_parent=str(row["CONTACT_PARENT"]).strip(),
                                profession_parent=str(
                                    row.get("PROFESSION_PARENT", "N/A")
                                ).strip(),
                                est_orphelin=str(row.get("ORPHELIN", "FAUX")).upper()
                                == "VRAI",
                                est_demuni=str(row.get("DEMUNI", "FAUX")).upper()
                                == "VRAI",
                            )
                            session.add(student)
                            session.commit()
                            session.refresh(student)
                            total_imported += 1

                        # 2. Inscription (Enrollment) dans la classe et l'année active

                        # Vérifier si l'élève est déjà inscrit cette année
                        existing_enrollment = session.exec(
                            select(Enrollment).where(
                                Enrollment.student_id == student.id,
                                Enrollment.classroom_id.in_(
                                    [c.id for c in classes]
                                ),  # Vérifie dans toutes les classes de l'année
                            )
                        ).first()

                        if existing_enrollment:
                            st.warning(
                                f"Ligne {index+2} ({matricule}) : Déjà inscrit cette année. Enrollment ignoré."
                            )
                        else:
                            enrollment = Enrollment(
                                student_id=student.id,
                                classroom_id=class_id_to_enroll,
                                date_inscription=date.today(),
                            )
                            session.add(enrollment)
                            session.commit()
                            total_enrolled += 1

                st.success(
                    f"Opération terminée. **{total_imported}** nouveaux élèves créés. **{total_enrolled}** inscriptions enregistrées dans la classe **{selected_class_name}**."
                )
                st.balloons()

    # --- ONGLET 2 : LISTE ET ENRÔLEMENT MANUEL ---
    with tab_list:
        st.subheader("Liste des Inscriptions pour l'année")
        
        # Sélection de la classe
        classes = session.exec(
            select(ClassRoom).where(ClassRoom.academic_year_id == active_year.id)
        ).all()
        class_map = {f"{c.niveau.value}": c.id for c in classes}
        class_names = list(class_map.keys())

        if not classes:
            st.error(
                "❌ Aucune classe ouverte cette année. Créez des classes avant d'importer des notes."
            )
            return
        selected_class_name = st.selectbox("Classe", options=class_names)
        selected_class_id = class_map[selected_class_name]
        st.divider()
        
        st.subheader(f"Liste des élèves du {selected_class_name}")
        enrollments = session.exec(
            select(Enrollment, Student, ClassRoom)
            .join(Student)
            .join(ClassRoom)
            .where(ClassRoom.academic_year_id == active_year.id)
            .where(ClassRoom.id == selected_class_id)
            .order_by(Student.nom, Student.prenom)
        ).all()

        if enrollments:
            display_data = []

            # Parcourir les tuples (enr, stu, classroom)
            for enr, student, classroom in enrollments:

                display_data.append(
                    {
                        "Matricule": student.matricule,
                        "Nom & Prénoms": f"{student.nom} {student.prenom}",
                        "Classe": classroom.nom_interne,
                        "Niveau": classroom.niveau.value,
                        "Date Inscription": enr.date_inscription.strftime("%Y-%m-%d"),
                    }
                )

            st.dataframe(
                pd.DataFrame(display_data), use_container_width=True, hide_index=True
            )
            st.info(f"Total des élèves inscrits cette année : **{len(enrollments)}**")

        else:
            st.info("Aucun élève n'est encore inscrit pour l'année active.")
