import streamlit as st
import pandas as pd
from sqlalchemy import func
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

    # KPI: totaux
    total_students = session.exec(select(func.count()).select_from(Student)).one()
    total_teachers = session.exec(select(func.count()).select_from(Teacher)).one()
    total_classes = session.exec(
        select(func.count())
        .select_from(ClassRoom)
        .where(ClassRoom.academic_year_id == active_year.id)
    ).one()
    total_enrollments = session.exec(
        select(func.count())
        .select_from(Enrollment)
        .join(ClassRoom)
        .where(ClassRoom.academic_year_id == active_year.id)
    ).one()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Élèves", int(total_students))
    k2.metric("Enseignants", int(total_teachers))
    k3.metric("Classes ouvertes", int(total_classes))
    k4.metric("Inscriptions (cette année)", int(total_enrollments))

    st.markdown("---")

    # Sélection d'évaluation pour statistiques
    eval_choice = st.selectbox(
        "Choisir l'étape d'évaluation", [e.value for e in EvaluationEtape]
    )
    eval_enum = EvaluationEtape(eval_choice)

    # Moyenne des points par classe pour cette évaluation
    rows = session.exec(
        select(ClassRoom.nom_interne, TermAverage.total_points)
        .join(Enrollment, Enrollment.classroom_id == ClassRoom.id)
        .join(TermAverage, TermAverage.enrollment_id == Enrollment.id)
        .where(
            ClassRoom.academic_year_id == active_year.id,
            TermAverage.evaluation == eval_enum,
        )
    ).all()

    if rows:
        df = pd.DataFrame(rows, columns=["Classe", "TotalPoints"])
        cls_avg = df.groupby("Classe")["TotalPoints"].mean().reset_index()
        cls_avg = cls_avg.sort_values("TotalPoints", ascending=False)
        st.subheader("Moyenne des points par classe")
        st.bar_chart(cls_avg.set_index("Classe"))

        # Top 5 élèves
        st.subheader("Top 5 élèves (par points totaux)")
        top_rows = session.exec(
            select(TermAverage, Enrollment, ClassRoom, Student)
            .join(Enrollment, TermAverage.enrollment_id == Enrollment.id)
            .join(ClassRoom, Enrollment.classroom_id == ClassRoom.id)
            .join(Student, Enrollment.student_id == Student.id)
            .where(
                ClassRoom.academic_year_id == active_year.id,
                TermAverage.evaluation == eval_enum,
            )
            .order_by(TermAverage.total_points.desc())
        ).all()

        if top_rows:
            top_data = []
            for term_avg, enr, cls, stu in top_rows[:5]:
                top_data.append(
                    {
                        "Matricule": stu.matricule,
                        "Nom": f"{stu.nom} {stu.prenom}",
                        "Classe": cls.nom_interne,
                        "Points": (
                            round(term_avg.total_points, 2)
                            if term_avg.total_points is not None
                            else None
                        ),
                    }
                )
            st.table(pd.DataFrame(top_data))
    else:
        st.info(
            "Aucune donnée de résultat pour cette évaluation. Importez des notes pour voir les statistiques."
        )
