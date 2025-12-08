import streamlit as st
from sqlmodel import select, Session, col
import pandas as pd
from io import BytesIO
from typing import List

from src.models import (
    Grade,
    TermAverage,
    Enrollment,
    Student,
    ClassRoom,
    AcademicYear,
    EvaluationEtape,
)

# Définition des matières pour le calcul et les colonnes du modèle
MATIERES = [
    ("note_ce", "Français/Compréhension de l'Ecrit"),
    ("note_ee", "Français/Expression Ecrite"),
    ("note_co", "Français/Communication Orale"),
    ("note_dictee", "Français/Dictée"),
    ("note_dessin", "EA/Dessin"),
    ("note_ea_oral", "EA/Oral (Chant/Poésie/Conte)"),
    ("note_eps", "EPS"),
    ("note_es", "Education Sociale"),
    ("note_est", "Education Scientifique et Technologique"),
    ("note_math", "Mathématique"),
]
NOMBRE_TOTAL_MATIERES = len(MATIERES)
SEUIL_PASSAGE = 6  # Seuil défini par le cahier des charges (6 matières >= 10)


def generate_notes_template(session: Session, class_id: int) -> bytes:
    """Génère le modèle Excel de notes pour une classe donnée."""

    # 1. Récupérer les élèves inscrits dans cette classe
    enrollments = session.exec(
        select(Enrollment, Student)
        .join(Student)
        .where(Enrollment.classroom_id == class_id)
        .order_by(Student.nom)
    ).all()

    data = []
    for enr, stu in enrollments:
        row = {
            "ENROLEMENT_ID (NE PAS TOUCHER)": enr.id,
            "MATRICULE": stu.matricule,
            "NOM & PRÉNOM": f"{stu.nom} {stu.prenom}",
        }
        # Ajouter les colonnes de notes
        for code, name in MATIERES:
            row[name] = ""  # Valeur vide à remplir par l'enseignant
        data.append(row)

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Notes")

        # Ajout d'une protection sur les colonnes clés (ID, Nom)
        workbook = writer.book
        worksheet = writer.sheets["Notes"]

        # Format de protection pour les colonnes non modifiables
        locked_format = workbook.add_format({"locked": True})

        # Verrouiller les 3 premières colonnes (ID, Matricule, Nom & Prénom)
        for col_num in range(3):
            worksheet.set_column(col_num, col_num, None, locked_format)

        # Protéger la feuille (sans mot de passe pour la simplicité, mais nécessaire pour l'activation des verrous)
        worksheet.protect()

    return output.getvalue()


def calculate_and_save_results(
    session: Session, df: pd.DataFrame, evaluation_step: EvaluationEtape
):
    """Calcule le TermAverage, sauvegarde les notes (Grade) et les résultats."""

    success_count = 0
    # Normaliser les noms de colonnes reçues (comme fait côté upload)
    df.columns = [col.upper().replace(" ", "_") for col in df.columns]
    key_col = "ENROLEMENT_ID_(NE_PAS_TOUCHER)"

    for index, row in df.iterrows():
        enrolement_id = None
        try:
            enrolement_id = int(row[key_col])

            # --- 1. SAUVEGARDE DES NOTES (GRADE) ---

            # Récupérer ou créer l'objet Grade pour cet élève et cette étape
            grade_instance = session.exec(
                select(Grade).where(
                    Grade.enrollment_id == enrolement_id,
                    Grade.evaluation == evaluation_step,
                )
            ).first()

            if not grade_instance:
                grade_instance = Grade(
                    enrollment_id=enrolement_id, evaluation=evaluation_step
                )

            total_points = 0
            moyennes_atteintes = 0

            # Parcourir les colonnes de notes (MATIERES)
            for i, (code, name) in enumerate(MATIERES):
                note = row.iloc[
                    3 + i
                ]  # Les notes commencent après la 3ème colonne (ID, Matricule, Nom)

                # Validation et mise à jour de l'instance Grade
                if pd.notna(note) and 0 <= note <= 20:
                    setattr(grade_instance, code, float(note))
                    total_points += float(note)
                    if float(note) >= 10:
                        moyennes_atteintes += 1
                else:
                    # Si la note est manquante ou invalide, ne pas la compter comme un échec, mais la laisser NULL
                    setattr(grade_instance, code, None)

            # Sauvegarder l'instance Grade (ajout sans commit pour éviter flush prématuré)
            session.add(grade_instance)

            # --- 2. CALCUL ET SAUVEGARDE DU RÉSULTAT PÉRIODIQUE (TERMAVERAGE) ---

            decision_txt = (
                "A ATTEINT LE SEUIL"
                if moyennes_atteintes >= SEUIL_PASSAGE
                else "N'A PAS ATTEINT LE SEUIL"
            )

            term_average = session.exec(
                select(TermAverage).where(
                    TermAverage.enrollment_id == enrolement_id,
                    TermAverage.evaluation == evaluation_step,
                )
            ).first()

            if not term_average:
                # Initialiser `rang` à 0 pour satisfaire la contrainte NOT NULL
                term_average = TermAverage(
                    enrollment_id=enrolement_id,
                    evaluation=evaluation_step,
                    total_note=NOMBRE_TOTAL_MATIERES,
                    rang=0,
                )

            term_average.total_moyenne = moyennes_atteintes
            term_average.total_points = total_points
            term_average.decision = decision_txt

            # Ajouter/mettre à jour le TermAverage (le commit sera fait après le traitement de toutes les lignes)
            session.add(term_average)
            success_count += 1

        except Exception as e:
            display_id = enrolement_id if enrolement_id is not None else "N/A"
            st.error(f"Erreur à la ligne {index + 2} (ID {display_id}) : {e}")

    session.commit()

    # --- 3. CALCUL DU RANG (DOIT ÊTRE FAIT APRÈS LA SAUVEGARDE DE TOUS LES TOTAUX) ---

    # Récupérer tous les résultats de l'évaluation dans la classe concernée (par l'enrollment_id)
    class_enrollments = session.exec(
        select(Enrollment).where(col(Enrollment.id).in_(df[key_col]))
    ).all()

    # 3.1 Récupérer les ID des élèves concernés par cette classe
    enrollment_ids = [e.id for e in class_enrollments]

    # 3.2 Récupérer les TermAverage correspondants, triés par points décroissants
    results_to_rank = session.exec(
        select(TermAverage)
        .where(
            col(TermAverage.enrollment_id).in_(enrollment_ids),
            TermAverage.evaluation == evaluation_step,
        )
        .order_by(
            TermAverage.total_moyenne.desc(), TermAverage.total_points.desc()
        )  # Priorité au Seuil atteint, puis aux points totaux
    ).all()

    # 3.3 Assigner le rang
    current_rank = 1

    for i, res in enumerate(results_to_rank):
        if i > 0:
            prev_res = results_to_rank[i - 1]
            # Vérifier l'égalité pour ex aequo
            if (
                res.total_moyenne == prev_res.total_moyenne
                and res.total_points == prev_res.total_points
            ):
                res.rang = prev_res.rang  # Même rang que le précédent
            else:
                current_rank = i + 1  # Nouveau rang

        res.rang = current_rank
        session.add(res)

    session.commit()
    return success_count


def grades_view(session: Session):
    st.header("📝 Gestion des Évaluations")

    active_year = session.exec(
        select(AcademicYear).where(AcademicYear.active == True)
    ).first()
    if not active_year:
        st.warning("⚠️ Veuillez activer une année scolaire.")
        return

    st.info(f"Année scolaire active : **{active_year.nom}**")

    # 1. Sélection de la classe et de l'étape d'évaluation
    classes = session.exec(
        select(ClassRoom).where(ClassRoom.academic_year_id == active_year.id)
    ).all()
    class_map = {f"{c.nom_interne} ({c.niveau.value})": c.id for c in classes}
    class_names = list(class_map.keys())

    if not classes:
        st.error(
            "❌ Aucune classe ouverte cette année. Créez des classes avant d'importer des notes."
        )
        return

    # Formulaire de sélection principal
    st.subheader("Sélection de l'Évaluation")
    col_select_class, col_select_eval = st.columns(2)
    with col_select_class:
        selected_class_name = st.selectbox("Classe concernée", options=class_names)
    with col_select_eval:
        evaluation_step = st.selectbox(
            "Étape d'Évaluation", [e.value for e in EvaluationEtape]
        )

    selected_class_id = class_map[selected_class_name]
    selected_eval_enum = EvaluationEtape(evaluation_step)
    st.divider()

    tab_dl, tab_upload, tab_results = st.tabs(
        ["⬇️ Modèle de Notes", "⬆️ Importer les Notes", "📊 Résultats"]
    )

    # --- ONGLET 1 : TÉLÉCHARGEMENT DU MODÈLE ---
    with tab_dl:
        st.subheader(
            f"Télécharger le modèle de notes pour {selected_class_name} ({evaluation_step})"
        )
        st.write(
            "Ce fichier contient la liste des élèves de cette classe. Remplissez uniquement les colonnes de notes (entre 0 et 20)."
        )

        template_file = generate_notes_template(session, selected_class_id)

        st.download_button(
            label=f"Télécharger Modèle {selected_class_name} - {evaluation_step}",
            data=template_file,
            file_name=f"notes_{selected_class_name}_{evaluation_step.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Ce fichier est personnalisé pour la classe et l'évaluation sélectionnées.",
        )

    # --- ONGLET 2 : IMPORTATION DES NOTES ---
    with tab_upload:
        st.subheader("Importation du fichier rempli")
        uploaded_file = st.file_uploader(
            "Charger le fichier de notes Excel (.xlsx)", type=["xlsx"]
        )

        if uploaded_file and st.button(
            f"Importer et Calculer les Résultats pour {evaluation_step}"
        ):
            try:
                df_notes = pd.read_excel(uploaded_file)
                df_notes.columns = [
                    col.upper().replace(" ", "_") for col in df_notes.columns
                ]

                # Vérification rapide de la colonne clé
                if "ENROLEMENT_ID_(NE_PAS_TOUCHER)" not in df_notes.columns:
                    st.error(
                        "Erreur de format : La colonne 'ENROLEMENT_ID (NE PAS TOUCHER)' est manquante ou mal nommée."
                    )
                else:
                    count = calculate_and_save_results(
                        session, df_notes, selected_eval_enum
                    )
                    st.success(
                        f"Opération réussie ! {count} élèves mis à jour. Les résultats et rangs sont calculés."
                    )
                    st.rerun()

            except Exception as e:
                st.error(f"Erreur lors de l'importation ou du calcul : {e}")

    # --- ONGLET 3 : CONSULTATION DES RÉSULTATS ---
    with tab_results:
        st.subheader(f"Résultats de {selected_class_name} ({evaluation_step})")

        # Récupération des résultats calculés pour l'affichage
        # On inclut la table `Grade` via un left outer join pour afficher les notes
        results = session.exec(
            select(TermAverage, Enrollment, Student, Grade)
            .join(Enrollment, TermAverage.enrollment_id == Enrollment.id)
            .join(ClassRoom, Enrollment.classroom_id == ClassRoom.id)
            .join(Student, Enrollment.student_id == Student.id)
            .join(Grade, Grade.enrollment_id == Enrollment.id, isouter=True)
            .where(
                TermAverage.evaluation == selected_eval_enum,
                ClassRoom.id == selected_class_id,
            )
            .order_by(TermAverage.rang)
        ).all()

        if results:
            display_data = []
            for term_avg, enr, stu, grade in results:
                # Colonnes de base (rang, id élève)
                row = {
                    "Rang": term_avg.rang,
                    "Matricule": stu.matricule,
                    "Nom & Prénom": f"{stu.nom} {stu.prenom}",
                }

                # Ensuite, ajouter toutes les notes en utilisant les libellés humains définis dans MATIERES
                for code, human_name in MATIERES:
                    note_val = None
                    if grade is not None:
                        note_val = getattr(grade, code, None)
                    row[human_name] = (
                        round(note_val, 2)
                        if isinstance(note_val, (int, float))
                        else note_val
                    )

                # Enfin, ajouter les colonnes de synthèse à la fin : Seuil, Total Points, Décision
                row["Seuil Atteint (Nb >= 10)"] = (
                    f"{term_avg.total_moyenne} / {term_avg.total_note}"
                )
                row["Total Points"] = (
                    round(term_avg.total_points, 2)
                    if term_avg.total_points is not None
                    else None
                )
                row["Décision"] = term_avg.decision

                display_data.append(row)

            # Construire le DataFrame dans l'ordre voulu et afficher
            df_display = pd.DataFrame(display_data)
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Ajouter des boutons d'export (CSV et XLSX) conservant l'ordre des colonnes
            col_csv, col_xlsx = st.columns(2)
            with col_csv:
                csv_data = df_display.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Exporter CSV",
                    data=csv_data,
                    file_name=f"results_{selected_class_name}_{evaluation_step.replace(' ', '_')}.csv",
                    mime="text/csv",
                )
            with col_xlsx:
                output = BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_display.to_excel(writer, index=False, sheet_name="Résultats")
                xlsx_data = output.getvalue()
                st.download_button(
                    label="Exporter XLSX",
                    data=xlsx_data,
                    file_name=f"results_{selected_class_name}_{evaluation_step.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            # Afficher le nombre d'élèves ayant atteint le seuil
            nb_atteint = sum(
                1 for d in display_data if d["Décision"] == "A ATTEINT LE SEUIL"
            )
            st.info(
                f"**{nb_atteint}** élèves ({nb_atteint/len(results)*100:.1f}%) ont atteint le seuil de {SEUIL_PASSAGE} matières."
            )

        else:
            st.info("Aucun résultat enregistré pour cette évaluation.")
