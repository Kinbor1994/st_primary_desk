import streamlit as st
from sqlmodel import select, Session
import pandas as pd
from datetime import date
import re  # Pour les vérifications de format

from src.models import Student, Enrollment, Sexe, AcademicYear, ClassRoom
from src.services.student_service import StudentService


def students_view(session: Session):
    st.header("👤 Gestion des Élèves et Inscriptions")

    service = StudentService(session)

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

    class_map = {f"{c.niveau}": c.id for c in classes}
    class_names = list(class_map.keys())

    # --- TABS CRUD ---
    tab_create, tab_list, tab_update, tab_import = st.tabs(
        [
            "➕ Ajouter Élève",
            "📋 Liste des Élèves",
            "✏️ Modifier/Supprimer",
            "⬆️ Importer Excel",
        ]
    )

    # ======================
    # TAB 1 : CREATE (Ajouter un élève)
    # ======================
    with tab_create:
        st.subheader("Ajouter un nouvel élève")

        col1, col2 = st.columns(2)
        with col1:
            matricule = st.text_input(
                "Matricule *",
                key="create_matricule",
                help="Identifiant unique de l'élève",
            )
            nom = st.text_input("Nom *", key="create_nom")
            prenom = st.text_input("Prénom *", key="create_prenom")
            sexe = st.selectbox(
                "Sexe *", options=[Sexe.MASCULIN, Sexe.FEMININ], key="create_sexe"
            )

        with col2:
            date_naissance = st.date_input("Date de naissance *", key="create_dob")
            lieu_naissance = st.text_input("Lieu de naissance *", key="create_lob")
            nom_parent = st.text_input(
                "Nom du parent/tuteur *", key="create_parent_name"
            )
            contact_parent = st.text_input(
                "Contact du parent/tuteur *", key="create_parent_contact"
            )

        col3, col4 = st.columns(2)
        with col3:
            profession_parent = st.text_input(
                "Profession du parent (optionnel)",
                key="create_parent_prof",
                placeholder="Ex: Commerçant, Agriculteur...",
            )
            est_orphelin = st.checkbox("Est orphelin", key="create_orphelin")

        with col4:
            est_demuni = st.checkbox("Est démuni", key="create_demuni")
            selected_class = st.selectbox(
                "Classe d'inscription *",
                options=class_names,
                key="create_class",
                help="Sélectionnez la classe pour l'inscription",
            )

        if st.button("✅ Créer l'élève", key="btn_create_student"):
            # Validation
            if not all(
                [
                    matricule,
                    nom,
                    prenom,
                    date_naissance,
                    lieu_naissance,
                    nom_parent,
                    contact_parent,
                ]
            ):
                st.error("❌ Tous les champs obligatoires (*) doivent être remplis")
            else:
                try:
                    # Créer l'élève
                    student = service.create_student(
                        matricule=matricule,
                        nom=nom,
                        prenom=prenom,
                        sexe=sexe,
                        date_naissance=date_naissance,
                        lieu_naissance=lieu_naissance,
                        nom_parent=nom_parent,
                        contact_parent=contact_parent,
                        profession_parent=(
                            profession_parent if profession_parent else None
                        ),
                        est_orphelin=est_orphelin,
                        est_demuni=est_demuni,
                    )

                    # Créer l'inscription (enrollment)
                    classroom_id = class_map[selected_class]
                    enrollment = Enrollment(
                        student_id=student.id,
                        classroom_id=classroom_id,
                        date_inscription=date.today(),
                    )
                    session.add(enrollment)
                    session.commit()

                    st.success(
                        f"✅ Élève **{nom} {prenom}** créé et inscrit avec succès!"
                    )
                    st.balloons()

                except ValueError as e:
                    st.error(f"❌ Erreur: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Une erreur est survenue: {str(e)}")

    # ======================
    # TAB 2 : READ (Liste des élèves)
    # ======================
    with tab_list:
        st.subheader("Liste des élèves")

        col_search, col_class = st.columns([2, 1])
        with col_search:
            search_term = st.text_input("🔍 Rechercher par nom, prénom ou matricule")

        with col_class:
            selected_class_list = st.selectbox(
                "Filtrer par classe",
                options=["Tous"] + class_names,
                key="list_class_filter",
            )

        st.divider()

        # Récupérer les données selon les filtres
        if selected_class_list == "Tous":
            # Afficher tous les élèves
            if search_term:
                students = service.search_students(search_term)
                display_title = (
                    f"Résultats pour '{search_term}' ({len(students)} élève(s))"
                )
            else:
                students = service.get_all_students()
                display_title = f"Liste de tous les élèves ({len(students)} élève(s))"

            if students:
                display_data = []
                for student in students:
                    display_data.append(
                        {
                            "Matricule": student.matricule,
                            "Nom & Prénoms": f"{student.nom} {student.prenom}",
                            "Sexe": (
                                "Masculin"
                                if student.sexe == Sexe.MASCULIN
                                else "Féminin"
                            ),
                            "Date Naissance": student.date_naissance.strftime(
                                "%d/%m/%Y"
                            ),
                            "Parent": student.nom_parent,
                            "Contact": student.contact_parent,
                            "Orphelin": "✅" if student.est_orphelin else "❌",
                            "Démuni": "✅" if student.est_demuni else "❌",
                        }
                    )

                st.write(f"**{display_title}**")
                st.dataframe(
                    pd.DataFrame(display_data),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Aucun élève trouvé")

        else:
            # Afficher par classe
            classroom_id = class_map[selected_class_list]
            enrollments = session.exec(
                select(Enrollment, Student)
                .join(Student)
                .where(Enrollment.classroom_id == classroom_id)
                .order_by(Student.nom, Student.prenom)
            ).all()

            if enrollments:
                display_data = []
                for enrollment, student in enrollments:
                    if (
                        not search_term
                        or search_term.upper() in student.nom.upper()
                        or search_term.upper() in student.prenom.upper()
                        or search_term.upper() in student.matricule.upper()
                    ):
                        display_data.append(
                            {
                                "Matricule": student.matricule,
                                "Nom & Prénoms": f"{student.nom} {student.prenom}",
                                "Sexe": (
                                    "Masculin"
                                    if student.sexe == Sexe.MASCULIN
                                    else "Féminin"
                                ),
                                "Date Naissance": student.date_naissance.strftime(
                                    "%d/%m/%Y"
                                ),
                                "Parent": student.nom_parent,
                                "Contact": student.contact_parent,
                                "Orphelin": "✅" if student.est_orphelin else "❌",
                                "Démuni": "✅" if student.est_demuni else "❌",
                                "Date Inscription": enrollment.date_inscription.strftime(
                                    "%d/%m/%Y"
                                ),
                            }
                        )

                st.write(
                    f"**Classe {selected_class_list} - {len(display_data)} élève(s)**"
                )
                st.dataframe(
                    pd.DataFrame(display_data),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Aucun élève inscrit dans cette classe")

    # ======================
    # TAB 3 : UPDATE & DELETE
    # ======================
    with tab_update:
        st.subheader("Modifier ou Supprimer un élève")

        # Rechercher l'élève par nom, prénom ou matricule
        search_query = st.text_input(
            "🔍 Rechercher par nom, prénom ou matricule",
            key="update_search",
            placeholder="Ex: DUPONT, Jean, ou MAT001",
        )

        student = None
        if search_query:
            results = service.search_students(search_query)

            if results:
                student_options = {
                    f"{s.matricule} — {s.nom} {s.prenom}": s for s in results
                }
                selected_key = st.selectbox(
                    f"📋 {len(results)} élève(s) trouvé(s) — sélectionnez :",
                    options=list(student_options.keys()),
                    key="update_student_select",
                )
                student = student_options[selected_key]
                st.success(f"✅ Élève sélectionné : **{student.nom} {student.prenom}**")
                st.divider()

                # Choix de l'action
                action = st.radio(
                    "Action",
                    options=["Afficher", "Modifier", "Supprimer"],
                    key="action_choice",
                )

                if action == "Afficher":
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Matricule:** {student.matricule}")
                        st.write(f"**Nom:** {student.nom}")
                        st.write(f"**Prénom:** {student.prenom}")
                        st.write(
                            f"**Sexe:** {'Masculin' if student.sexe == Sexe.MASCULIN else 'Féminin'}"
                        )
                        st.write(
                            f"**Date Naissance:** {student.date_naissance.strftime('%d/%m/%Y')}"
                        )
                        st.write(f"**Lieu Naissance:** {student.lieu_naissance}")

                    with col2:
                        st.write(f"**Parent:** {student.nom_parent}")
                        st.write(f"**Contact Parent:** {student.contact_parent}")
                        st.write(
                            f"**Profession Parent:** {student.profession_parent or 'N/A'}"
                        )
                        st.write(
                            f"**Orphelin:** {'✅ Oui' if student.est_orphelin else '❌ Non'}"
                        )
                        st.write(
                            f"**Démuni:** {'✅ Oui' if student.est_demuni else '❌ Non'}"
                        )

                elif action == "Modifier":
                    st.subheader("Modifier les informations")

                    col1, col2 = st.columns(2)
                    with col1:
                        new_nom = st.text_input(
                            "Nom", value=student.nom, key="update_nom"
                        )
                        new_prenom = st.text_input(
                            "Prénom", value=student.prenom, key="update_prenom"
                        )
                        new_sexe = st.selectbox(
                            "Sexe",
                            options=[Sexe.MASCULIN, Sexe.FEMININ],
                            index=0 if student.sexe == Sexe.MASCULIN else 1,
                            key="update_sexe",
                        )
                        new_date_naissance = st.date_input(
                            "Date de naissance",
                            value=student.date_naissance,
                            key="update_dob",
                        )
                        new_lieu_naissance = st.text_input(
                            "Lieu de naissance",
                            value=student.lieu_naissance,
                            key="update_lob",
                        )

                    with col2:
                        new_nom_parent = st.text_input(
                            "Nom du parent/tuteur",
                            value=student.nom_parent,
                            key="update_parent_name",
                        )
                        new_contact_parent = st.text_input(
                            "Contact du parent/tuteur",
                            value=student.contact_parent,
                            key="update_parent_contact",
                        )
                        new_profession_parent = st.text_input(
                            "Profession du parent",
                            value=student.profession_parent or "",
                            key="update_parent_prof",
                        )
                        new_est_orphelin = st.checkbox(
                            "Est orphelin",
                            value=student.est_orphelin,
                            key="update_orphelin",
                        )
                        new_est_demuni = st.checkbox(
                            "Est démuni", value=student.est_demuni, key="update_demuni"
                        )

                    if st.button("💾 Enregistrer les modifications", key="btn_update"):
                        try:
                            service.update_student(
                                student_id=student.id,
                                nom=new_nom,
                                prenom=new_prenom,
                                sexe=new_sexe,
                                date_naissance=new_date_naissance,
                                lieu_naissance=new_lieu_naissance,
                                nom_parent=new_nom_parent,
                                contact_parent=new_contact_parent,
                                profession_parent=new_profession_parent or None,
                                est_orphelin=new_est_orphelin,
                                est_demuni=new_est_demuni,
                            )
                            st.success("✅ Élève modifié avec succès!")
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la modification: {str(e)}")

                elif action == "Supprimer":
                    st.warning(
                        f"⚠️ Attention! Cette action supprimera définitivement l'élève **{student.nom} {student.prenom}** et toutes ses inscriptions."
                    )

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("🗑️ Confirmer la suppression", key="btn_delete"):
                            try:
                                service.delete_student(student.id)
                                st.success("✅ Élève supprimé avec succès!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erreur lors de la suppression: {str(e)}")

                    with col2:
                        st.info("Cliquez sur 'Confirmer' pour supprimer")

            else:
                st.error(
                    f"❌ Aucun élève trouvé avec le matricule '{search_matricule}'"
                )

    # ======================
    # TAB 4 : IMPORT (Importer un fichier Excel)
    # ======================
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
            key="import_class",
            help="Tous les élèves du fichier seront inscrits dans cette classe pour l'année active.",
        )

        # Le bouton d'importation est placé après le sélecteur de classe
        if uploaded_file:
            if st.button("Lancer l'Importation et l'Inscription", key="btn_import"):
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
                else:
                    total_imported = 0
                    total_enrolled = 0
                    total_skipped = 0
                    class_id_to_enroll = class_map[selected_class_name]

                    with st.spinner("Traitement des données..."):
                        for index, row in df.iterrows():
                            matricule = str(row["MATRICULE"]).strip()

                            # Vérifier si l'élève existe déjà
                            student = service.get_student_by_matricule(matricule)

                            try:
                                birth_date = pd.to_datetime(
                                    row["DATE_NAISSANCE"]
                                ).date()
                            except:
                                st.warning(
                                    f"Ligne {index+2} ({matricule}) : Date de naissance invalide. Élève ignoré."
                                )
                                total_skipped += 1
                                continue

                            if not student:
                                # Création du nouvel élève
                                try:
                                    student = service.create_student(
                                        matricule=matricule,
                                        nom=str(row["NOM"]).strip(),
                                        prenom=str(row["PRENOM"]).strip(),
                                        sexe=Sexe(str(row["SEXE"]).strip().upper()),
                                        date_naissance=birth_date,
                                        lieu_naissance=str(
                                            row["LIEU_NAISSANCE"]
                                        ).strip(),
                                        nom_parent=str(row["NOM_PARENT"]).strip(),
                                        contact_parent=str(
                                            row["CONTACT_PARENT"]
                                        ).strip(),
                                        profession_parent=str(
                                            row.get("PROFESSION_PARENT", "")
                                        ).strip()
                                        or None,
                                        est_orphelin=str(
                                            row.get("ORPHELIN", "FAUX")
                                        ).upper()
                                        == "VRAI",
                                        est_demuni=str(
                                            row.get("DEMUNI", "FAUX")
                                        ).upper()
                                        == "VRAI",
                                    )
                                    total_imported += 1
                                except ValueError as e:
                                    st.warning(
                                        f"Ligne {index+2} ({matricule}): {str(e)}"
                                    )
                                    total_skipped += 1
                                    continue
                            else:
                                total_skipped += 1

                            # Inscription (Enrollment) dans la classe et l'année active
                            existing_enrollment = session.exec(
                                select(Enrollment).where(
                                    Enrollment.student_id == student.id,
                                    Enrollment.classroom_id == class_id_to_enroll,
                                )
                            ).first()

                            if not existing_enrollment:
                                enrollment = Enrollment(
                                    student_id=student.id,
                                    classroom_id=class_id_to_enroll,
                                    date_inscription=date.today(),
                                )
                                session.add(enrollment)
                                session.commit()
                                total_enrolled += 1

                    st.success(
                        f"""
                        ✅ Opération terminée!
                        - **{total_imported}** nouveaux élèves créés
                        - **{total_enrolled}** inscriptions enregistrées dans la classe **{selected_class_name}**
                        - **{total_skipped}** élève(s) ignorés (déjà existants ou erreurs)
                        """
                    )
                    st.balloons()
