import streamlit as st
import pandas as pd
from sqlalchemy import func, case
from sqlmodel import select, Session

from src.models import (
    Student,
    Teacher,
    ClassRoom,
    Enrollment,
    TermAverage,
    AcademicYear,
    EvaluationEtape,
)


def dashboard_view(session: Session):
    st.header("📊 Tableau de bord")

    # Année active
    active_year = session.exec(
        select(AcademicYear).where(AcademicYear.active == True)
    ).first()
    if not active_year:
        st.warning(
            "⚠️ Aucune année active — allez dans Configuration pour en créer/activer une."
        )
        return

    st.subheader(f"Année scolaire : {active_year.nom}")

    # Récupérer les classes disponibles
    classes = session.exec(
        select(ClassRoom)
        .where(ClassRoom.academic_year_id == active_year.id)
        .order_by(ClassRoom.nom_interne)
    ).all()

    if not classes:
        st.warning("⚠️ Aucune classe disponible pour cette année.")
        return

    # Selectbox pour choisir une classe
    st.subheader("Sélection de la Classe")
    class_names = [f"{c.nom_interne} ({c.niveau})" for c in classes]
    selected_class_name = st.selectbox("Choisir une classe", options=class_names)
    selected_class = next(
        (
            c
            for c in classes
            if f"{c.nom_interne} ({c.niveau})" == selected_class_name
        ),
        None,
    )

    st.markdown("---")

    # KPI: métriques pour la classe sélectionnée
    if selected_class:
        # Récupérer les inscriptions de la classe
        class_enrollments = session.exec(
            select(Enrollment).where(Enrollment.classroom_id == selected_class.id)
        ).all()

        # Compter garçons et filles
        boys_count = 0
        girls_count = 0
        for enr in class_enrollments:
            student = session.exec(
                select(Student).where(Student.id == enr.student_id)
            ).first()
            if student:
                if student.sexe == "M":
                    boys_count += 1
                else:
                    girls_count += 1

        total_class_enrollments = len(class_enrollments)

        # KPI pour la classe
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Élèves inscrits", total_class_enrollments)
        k2.metric("Garçons", boys_count)
        k3.metric("Filles", girls_count)
        k4.metric(
            "Enseignant",
            selected_class.teacher_id if selected_class.teacher_id else "Non assigné",
        )

        st.markdown("---")

    # Statistique par classe
    st.subheader("Effectifs par Classe")
    stmt = (
        select(
            ClassRoom.nom_interne,
            func.count(Enrollment.id).filter(Student.sexe == "M").label("Garçons"),
            func.count(Enrollment.id).filter(Student.sexe == "F").label("Filles"),
            func.count(Enrollment.id).label("Total"),
        )
        .join(Enrollment, Enrollment.classroom_id == ClassRoom.id)
        .join(Student, Enrollment.student_id == Student.id)
        .where(ClassRoom.academic_year_id == active_year.id)
        .group_by(ClassRoom.nom_interne)
    )
    data_rows = session.exec(stmt).all()

    st.dataframe(
        pd.DataFrame(data_rows, columns=["Classe", "Garçons", "Filles", "Total"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    # Sélection d'évaluation pour statistiques de la classe sélectionnée
    st.subheader("Résultats par Étape d'Évaluation")
    eval_choice = st.selectbox(
        "Choisir l'étape d'évaluation", [e.value for e in EvaluationEtape]
    )
    eval_enum = EvaluationEtape(eval_choice)

    # Récupérer les résultats pour la classe et l'évaluation
    results = session.exec(
        select(TermAverage, Enrollment, Student)
        .join(Enrollment, TermAverage.enrollment_id == Enrollment.id)
        .join(Student, Enrollment.student_id == Student.id)
        .where(
            Enrollment.classroom_id == selected_class.id,
            TermAverage.evaluation == eval_enum,
        )
    ).all()

    if results:
        # Top 5 élèves de la classe
        st.subheader("Top 5 élèves de la classe (par points totaux)")
        top_data = []
        for term_avg, enr, stu in sorted(
            results,
            key=lambda x: x[0].total_points if x[0].total_points else 0,
            reverse=True,
        )[:5]:
            top_data.append(
                {
                    "Rang": term_avg.rang,
                    "Matricule": stu.matricule,
                    "Nom": f"{stu.nom} {stu.prenom}",
                    "Points": (
                        round(term_avg.total_points, 2) if term_avg.total_points else 0
                    ),
                    "Décision": term_avg.decision,
                }
            )
        st.table(pd.DataFrame(top_data))

        # Statistiques de réussite
        nb_reussi = sum(
            1 for term_avg, _, _ in results if term_avg.decision == "A ATTEINT LE SEUIL"
        )
        nb_total = len(results)
        pct_reussite = (nb_reussi / nb_total * 100) if nb_total > 0 else 0
        st.info(
            f"**{nb_reussi}** élèves ({pct_reussite:.1f}%) ont atteint le seuil de réussite."
        )
    else:
        st.info("Aucun résultat pour cette évaluation dans cette classe.")
