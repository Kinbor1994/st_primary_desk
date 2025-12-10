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
    class_map = {f"{c.niveau.value}": c.id for c in classes}
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

    tab_dl, tab_upload, tab_results, tab_stats, tab_eval_results = st.tabs(
        [
            "⬇️ Modèle de Notes",
            "⬆️ Importer les Notes",
            "📊 Résultats",
            "📈 Statistiques",
            "Résultats de l'évaluation",
        ]
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
                row["Rang"] = term_avg.rang
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

    # --- ONGLET 4 : STATISTIQUES ---
    with tab_stats:
        st.subheader(f"Statistiques de {selected_class_name} ({evaluation_step})")

        # Récupérer tous les enrollments et grades pour cette classe et évaluation
        enrollments_for_stats = session.exec(
            select(Enrollment, Student, Grade)
            .join(Student, Enrollment.student_id == Student.id)
            .join(ClassRoom, Enrollment.classroom_id == ClassRoom.id)
            .join(Grade, Grade.enrollment_id == Enrollment.id, isouter=True)
            .where(
                ClassRoom.id == selected_class_id,
                Grade.evaluation == selected_eval_enum,
            )
        ).all()

        if not enrollments_for_stats:
            st.info(
                "Aucune donnée d'évaluation pour cette classe. Importez des notes d'abord."
            )
        else:
            # Calculer les stats pour chaque matière
            stats_data = []

            for code, human_name in MATIERES:
                inscrits_g = 0
                inscrits_f = 0
                presents_g = 0  # Élève a une note (non None)
                presents_f = 0
                absents_g = 0  # Élève inscrit mais pas de note
                absents_f = 0
                notes_g = []
                notes_f = []

                for enr, stu, grade in enrollments_for_stats:
                    if stu.sexe == "M":
                        inscrits_g += 1
                        if grade is not None:
                            note_val = getattr(grade, code, None)
                            if note_val is not None:
                                presents_g += 1
                                notes_g.append(note_val)
                            else:
                                absents_g += 1
                        else:
                            absents_g += 1
                    else:  # F
                        inscrits_f += 1
                        if grade is not None:
                            note_val = getattr(grade, code, None)
                            if note_val is not None:
                                presents_f += 1
                                notes_f.append(note_val)
                            else:
                                absents_f += 1
                        else:
                            absents_f += 1

                inscrits_t = inscrits_g + inscrits_f
                presents_t = presents_g + presents_f
                absents_t = absents_g + absents_f

                # Calculer moyenne, seuil atteint, taux réussite
                all_notes = notes_g + notes_f
                avg_note = sum(all_notes) / len(all_notes) if all_notes else 0
                seuil_atteint_g = sum(1 for n in notes_g if n >= 10)
                seuil_atteint_f = sum(1 for n in notes_f if n >= 10)
                seuil_atteint_t = seuil_atteint_g + seuil_atteint_f

                taux_reussite_g = (
                    (seuil_atteint_g / presents_g * 100) if presents_g > 0 else 0
                )
                taux_reussite_f = (
                    (seuil_atteint_f / presents_f * 100) if presents_f > 0 else 0
                )
                taux_reussite_t = (
                    (seuil_atteint_t / presents_t * 100) if presents_t > 0 else 0
                )

                stats_data.append(
                    {
                        "Matière": human_name,
                        "Inscrits G": inscrits_g,
                        "Inscrits F": inscrits_f,
                        "Inscrits T": inscrits_t,
                        "Absents G": absents_g,
                        "Absents F": absents_f,
                        "Absents T": absents_t,
                        "Présents G": presents_g,
                        "Présents F": presents_f,
                        "Présents T": presents_t,
                        "Note G": (
                            round(sum(notes_g) / len(notes_g), 2) if notes_g else 0
                        ),
                        "Note F": (
                            round(sum(notes_f) / len(notes_f), 2) if notes_f else 0
                        ),
                        "Note T": round(avg_note, 2),
                        "Seuil G": seuil_atteint_g,
                        "Seuil F": seuil_atteint_f,
                        "Seuil T": seuil_atteint_t,
                        "Taux G %": f"{taux_reussite_g:.1f}%",
                        "Taux F %": f"{taux_reussite_f:.1f}%",
                        "Taux T %": f"{taux_reussite_t:.1f}%",
                    }
                )

            # Restructurer le DataFrame avec colonnes groupées par section (G/F/T)
            df_stats = pd.DataFrame(stats_data)

            # Créer une structure multi-niveaux pour l'affichage groupé
            display_cols = ["Matière"]
            for col in [
                "Inscrits",
                "Présents",
                "Absents",
                "Ont atteint le seuil de réussite",
                "n'ont pas atteint le seuil de réussite",
                "% Pourcentage réussite",
                "% Pourcentage échec",
            ]:
                for sub in ["G", "F", "T"]:
                    if col == "Inscrits":
                        display_cols.append(f"Inscrits {sub}")
                    elif col == "Présents":
                        display_cols.append(f"Présents {sub}")
                    elif col == "Absents":
                        display_cols.append(f"Absents {sub}")
                    elif col == "Ont atteint le seuil de réussite":
                        display_cols.append(f"Seuil {sub}")
                    elif col == "n'ont pas atteint le seuil de réussite":
                        # Calculer nombre n'ayant pas atteint le seuil
                        pass
                    elif col == "% Pourcentage réussite":
                        display_cols.append(f"Taux {sub} %")
                    elif col == "% Pourcentage échec":
                        # Calculer pourcentage d'échec
                        pass

            # Réorganiser les colonnes dans l'ordre demandé
            display_order = ["Matière"]
            for sub in ["G", "F", "T"]:
                display_order.append(f"Inscrits {sub}")
            for sub in ["G", "F", "T"]:
                display_order.append(f"Présents {sub}")
            for sub in ["G", "F", "T"]:
                display_order.append(f"Absents {sub}")
            for sub in ["G", "F", "T"]:
                display_order.append(f"Seuil {sub}")
            for sub in ["G", "F", "T"]:
                display_order.append(f"Taux {sub} %")

            df_display = df_stats[display_order]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Bouton d'export pour les stats
            col_csv_stats, col_xlsx_stats = st.columns(2)
            with col_csv_stats:
                csv_stats = df_display.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Exporter Stats CSV",
                    data=csv_stats,
                    file_name=f"stats_{selected_class_name}_{evaluation_step.replace(' ', '_')}.csv",
                    mime="text/csv",
                )
            with col_xlsx_stats:
                output_stats = BytesIO()
                with pd.ExcelWriter(output_stats, engine="xlsxwriter") as writer:
                    df_display.to_excel(writer, index=False, sheet_name="Statistiques")
                xlsx_stats = output_stats.getvalue()
                st.download_button(
                    label="Exporter Stats XLSX",
                    data=xlsx_stats,
                    file_name=f"stats_{selected_class_name}_{evaluation_step.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    # --- ONGLET 5 : RÉSULTATS DE L'ÉVALUATION (SYNTHÈSE) ---
    with tab_eval_results:
        st.subheader(
            f"Synthèse de l'évaluation de {selected_class_name} ({evaluation_step})"
        )

        # Récupérer tous les enrollments et TermAverage pour cette classe et évaluation
        eval_results = session.exec(
            select(Enrollment, Student, TermAverage)
            .join(Student, Enrollment.student_id == Student.id)
            .join(ClassRoom, Enrollment.classroom_id == ClassRoom.id)
            .join(TermAverage, TermAverage.enrollment_id == Enrollment.id)
            .where(
                ClassRoom.id == selected_class_id,
                TermAverage.evaluation == selected_eval_enum,
            )
        ).all()

        if not eval_results:
            st.info(
                "Aucun résultat d'évaluation pour cette classe. Importez des notes d'abord."
            )
        else:
            # Calculer les stats synthétiques globales
            inscrits_g = 0
            inscrits_f = 0
            presents_g = 0
            presents_f = 0
            absents_g = 0
            absents_f = 0
            seuil_g = 0
            seuil_f = 0
            non_seuil_g = 0
            non_seuil_f = 0

            for enr, stu, term_avg in eval_results:
                if stu.sexe == "M":
                    inscrits_g += 1
                    # Vérifier si l'élève a au moins une note (présent)
                    grade_data = session.exec(
                        select(Grade).where(
                            Grade.enrollment_id == enr.id,
                            Grade.evaluation == selected_eval_enum,
                        )
                    ).first()
                    if grade_data is not None:
                        presents_g += 1
                    else:
                        absents_g += 1

                    # Compter seuil atteint/non atteint
                    if term_avg.decision == "A ATTEINT LE SEUIL":
                        seuil_g += 1
                    else:
                        non_seuil_g += 1
                else:  # F
                    inscrits_f += 1
                    grade_data = session.exec(
                        select(Grade).where(
                            Grade.enrollment_id == enr.id,
                            Grade.evaluation == selected_eval_enum,
                        )
                    ).first()
                    if grade_data is not None:
                        presents_f += 1
                    else:
                        absents_f += 1

                    if term_avg.decision == "A ATTEINT LE SEUIL":
                        seuil_f += 1
                    else:
                        non_seuil_f += 1

            # Totaux
            inscrits_t = inscrits_g + inscrits_f
            presents_t = presents_g + presents_f
            absents_t = absents_g + absents_f
            seuil_t = seuil_g + seuil_f
            non_seuil_t = non_seuil_g + non_seuil_f

            # Pourcentages (éviter division par 0)
            pct_seuil_g = (seuil_g / inscrits_g * 100) if inscrits_g > 0 else 0
            pct_seuil_f = (seuil_f / inscrits_f * 100) if inscrits_f > 0 else 0
            pct_seuil_t = (seuil_t / inscrits_t * 100) if inscrits_t > 0 else 0

            pct_non_seuil_g = (non_seuil_g / inscrits_g * 100) if inscrits_g > 0 else 0
            pct_non_seuil_f = (non_seuil_f / inscrits_f * 100) if inscrits_f > 0 else 0
            pct_non_seuil_t = (non_seuil_t / inscrits_t * 100) if inscrits_t > 0 else 0

            # Construire le DataFrame synthèse
            synthesis_data = {
                "Métrique": [
                    "INSCRITS",
                    "PRÉSENTS",
                    "ABSENTS",
                    "Ont atteint le seuil de réussite",
                    "% Pourcentage",
                    "n'ont pas atteint le seuil de réussite",
                    "% Pourcentage",
                ],
                "G": [
                    inscrits_g,
                    presents_g,
                    absents_g,
                    seuil_g,
                    f"{pct_seuil_g:.1f}%",
                    non_seuil_g,
                    f"{pct_non_seuil_g:.1f}%",
                ],
                "F": [
                    inscrits_f,
                    presents_f,
                    absents_f,
                    seuil_f,
                    f"{pct_seuil_f:.1f}%",
                    non_seuil_f,
                    f"{pct_non_seuil_f:.1f}%",
                ],
                "T": [
                    inscrits_t,
                    presents_t,
                    absents_t,
                    seuil_t,
                    f"{pct_seuil_t:.1f}%",
                    non_seuil_t,
                    f"{pct_non_seuil_t:.1f}%",
                ],
            }

            df_synthesis = pd.DataFrame(synthesis_data)
            st.dataframe(df_synthesis, use_container_width=True, hide_index=True)

            # Boutons d'export synthèse
            col_csv_syn, col_xlsx_syn = st.columns(2)
            with col_csv_syn:
                csv_syn = df_synthesis.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Exporter Synthèse CSV",
                    data=csv_syn,
                    file_name=f"synthesis_{selected_class_name}_{evaluation_step.replace(' ', '_')}.csv",
                    mime="text/csv",
                )
            with col_xlsx_syn:
                output_syn = BytesIO()
                with pd.ExcelWriter(output_syn, engine="xlsxwriter") as writer:
                    df_synthesis.to_excel(writer, index=False, sheet_name="Synthèse")
                xlsx_syn = output_syn.getvalue()
                st.download_button(
                    label="Exporter Synthèse XLSX",
                    data=xlsx_syn,
                    file_name=f"synthesis_{selected_class_name}_{evaluation_step.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
