import streamlit as st
from sqlmodel import select, Session
from datetime import date
from src.models import Teacher, Sexe, StatutEnseignant, FonctionEnseignant

def teachers_view(session: Session):
    st.header("🧑‍🏫 Gestion des Enseignants")

    # Utilisation d'onglets pour séparer l'ajout de la liste
    tab_add, tab_list = st.tabs(["➕ Ajouter un Enseignant", "📋 Liste des Enseignants"])

    # --- ONGLET 1 : AJOUTER UN ENSEIGNANT ---
    with tab_add:
        st.subheader("Fiche de Renseignement")
        
        with st.form("teacher_form", clear_on_submit=True):
            
            # --- SECTION 1 : IDENTITÉ ET CONTACTS ---
            st.markdown("#### Identité et Contacts")
            col1, col2, col3 = st.columns(3)
            with col1:
                matricule = st.text_input("Matricule", help="Matricule unique de l'enseignant")
                nom = st.text_input("Nom")
                prenom = st.text_input("Prénom")
            with col2:
                id_anpe = st.text_input("ID ANPE (si AME)", help="Laisser vide si non AME")
                sexe = st.selectbox("Sexe", [e.value for e in Sexe])
                nationalite = st.text_input("Nationalité", value="Béninoise")
            with col3:
                date_naissance = st.date_input("Date de naissance", value=date(1990, 1, 1))
                lieu_naissance = st.text_input("Lieu de naissance")
                telephone = st.text_input("Téléphone")
            
            adresse = st.text_area("Adresse (complète)", height=50)
            ifu = st.text_input("IFU (Identifiant Fiscal Unique)")
            st.divider()

            # --- SECTION 2 : CARRIÈRE ET STATUT ---
            st.markdown("#### Carrière et Statut")
            col_statut, col_fonction, col_grade = st.columns(3)
            with col_statut:
                statut = st.selectbox("Statut", [e.value for e in StatutEnseignant])
                date_prise_service = st.date_input("Date de première prise de service", value=date.today())
            with col_fonction:
                # La fonction principale sera la position dans l'école (directeur, adjoint, enseignant)
                fonction = st.selectbox("Fonction actuelle", [e.value for e in FonctionEnseignant] + ["Enseignant"])
                situation_matrimoniale = st.text_input("Situation Sociale", value="Célibataire")
            with col_grade:
                corps_actuel = st.text_input("Corps actuel (ex: Instituteur)")
                grade = st.text_input("Grade (ex: B1-4)", help="Catégorie-Échelle-Échelon")

            st.divider()

            # --- SECTION 3 : DIPLÔMES ET ANCIENNETÉ ---
            st.markdown("#### Diplômes et Ancienneté")
            col_diplome, col_annee, col_anciennete = st.columns(3)
            with col_diplome:
                diplome_académique = st.text_input("Diplôme Académique (ex: Licence)")
            with col_annee:
                annee_obtention_diplome = st.number_input("Année d'obtention du diplôme", min_value=1950, max_value=date.today().year, step=1, value=date.today().year)
            with col_anciennete:
                anciennete_fp = st.number_input("Ancienneté dans la fonction publique (années)", min_value=0, value=0)
                anciennete_ecole = st.number_input("Ancienneté dans l'école (années)", min_value=0, value=0)

            submitted = st.form_submit_button("✅ Enregistrer l'enseignant")

            if submitted:
                new_teacher = Teacher(
                    matricule=matricule, 
                    id_anpe=id_anpe if statut == StatutEnseignant.AME.value else None,
                    nom=nom, prenom=prenom, sexe=Sexe(sexe), date_naissance=date_naissance, 
                    lieu_naissance=lieu_naissance, telephone=telephone, adresse=adresse, 
                    ifu=ifu, nationalite=nationalite, statut=StatutEnseignant(statut),
                    date_prise_service=date_prise_service, corps_actuel=corps_actuel,
                    diplome_académique=diplome_académique, annee_obtention_diplome=annee_obtention_diplome,
                    grade=grade, situation_matrimoniale=situation_matrimoniale,
                    anciennete_fonction_publique=anciennete_fp, anciennete_ecole=anciennete_ecole
                )
                
                # Vérification d'unicité (matricule)
                existing = session.exec(select(Teacher).where(Teacher.matricule == matricule)).first()
                if existing:
                    st.error(f"Erreur : Le matricule {matricule} existe déjà.")
                else:
                    session.add(new_teacher)
                    session.commit()
                    st.success(f"Enseignant {nom} {prenom} enregistré avec succès !")
                    st.rerun()

    # --- ONGLET 2 : LISTE DES ENSEIGNANTS ---
    with tab_list:
        st.subheader("Effectif actuel")
        
        teachers = session.exec(select(Teacher).order_by(Teacher.nom)).all()
        
        if teachers:
            # Création d'un dictionnaire pour afficher les données proprement
            data = [{
                "Matricule": t.matricule,
                "Nom et Prénom": f"{t.nom} {t.prenom}",
                "Sexe": t.sexe,
                "Statut": t.statut,
                "Téléphone": t.telephone,
                "Grade": t.grade if t.grade else "N/A",
            } for t in teachers]
            
            st.dataframe(data, use_container_width=True, hide_index=True)
            st.info(f"Nombre total d'enseignants : **{len(teachers)}**")

            # Option future : Boutons pour éditer/supprimer ou voir le détail
            # st.write("Ajouter ici les boutons d'édition ou de suppression...")
        else:
            st.info("Aucun enseignant n'a été enregistré pour le moment.")