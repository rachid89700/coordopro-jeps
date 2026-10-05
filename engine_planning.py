"""
Engine de Planification & Négociation Déterministe Formateurs (100% sans LLM)
Gère :
1. Le matching intelligent thématique <-> compétences <-> disponibilités
2. La résolution de conflits et le swap automatique (inversion 6/7)
3. La génération et le suivi des emails de sollicitation formateurs
"""

import json
from datetime import datetime
from database import get_db

JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

def get_day_name(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return JOURS_FR[dt.weekday()]
    except Exception:
        return "lundi"

def find_best_trainer_for_slot(date_str, thematique):
    """
    Algorithme déterministe qui trouve le meilleur formateur pour une date et une thématique.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM formateurs")
    formateurs = [dict(f) for f in cursor.fetchall()]
    conn.close()

    day_of_week = get_day_name(date_str)
    candidates = []

    for f in formateurs:
        comps = json.loads(f.get("competences_json", "[]"))
        dispos = json.loads(f.get("disponibilites_json", "{}"))

        # Vérifier si compétence correspond (sensible ou fuzzy matching direct)
        has_skill = any(thematique.lower() in c.lower() or c.lower() in thematique.lower() for c in comps)
        is_available = dispos.get(day_of_week, False)

        if has_skill and is_available:
            candidates.append({
                "formateur": f,
                "score": 100, # Compétent et disponible
                "match_reason": f"Compétence validée ({thematique}) et disponible le {day_of_week}"
            })
        elif has_skill and not is_available:
            candidates.append({
                "formateur": f,
                "score": 50, # Compétent mais jour théoriquement indisponible
                "match_reason": f"Compétent mais indisponible le {day_of_week} (candidat pour swap)"
            })

    # Trier par score décroissant puis tarif
    candidates.sort(key=lambda x: (-x["score"], x["formateur"]["taux_journalier"]))
    return candidates

def auto_assign_week_planning(session_id, week_slots):
    """
    Assigne automatiquement une série de créneaux hebdomadaires.
    week_slots = [
        {"date": "2026-10-05", "thematique": "IA"},
        {"date": "2026-10-06", "thematique": "Diagnostic de territoire"},
        {"date": "2026-10-07", "thematique": "Budget"},
        {"date": "2026-10-08", "thematique": "Communication & Réseaux sociaux"},
        {"date": "2026-10-09", "thematique": "Évaluation"}
    ]
    """
    conn = get_db()
    cursor = conn.cursor()
    results = []

    for slot in week_slots:
        d = slot["date"]
        th = slot["thematique"]
        candidates = find_best_trainer_for_slot(d, th)

        assigned_formateur = None
        statut = "À attribuer"
        commentaire = "Aucun formateur disponible"

        if candidates and candidates[0]["score"] == 100:
            assigned_formateur = candidates[0]["formateur"]
            statut = "Proposé"
            commentaire = candidates[0]["match_reason"]
        elif candidates:
            assigned_formateur = candidates[0]["formateur"]
            statut = "À négocier"
            commentaire = candidates[0]["match_reason"]

        formateur_id = assigned_formateur["id"] if assigned_formateur else None

        # Vérifier si slot existe déjà
        cursor.execute("SELECT id FROM planning_slots WHERE session_id = ? AND date_slot = ?", (session_id, d))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
            UPDATE planning_slots 
            SET thematique = ?, formateur_id = ?, statut_slot = ?, commentaire = ?
            WHERE id = ?
            """, (th, formateur_id, statut, commentaire, row[0]))
            slot_id = row[0]
        else:
            cursor.execute("""
            INSERT INTO planning_slots (session_id, date_slot, periode, nb_heures, thematique, formateur_id, statut_slot, commentaire)
            VALUES (?, ?, 'Journée', 7.0, ?, ?, ?, ?)
            """, (session_id, d, th, formateur_id, statut, commentaire))
            slot_id = cursor.lastrowid

        results.append({
            "slot_id": slot_id,
            "date": d,
            "thematique": th,
            "formateur": assigned_formateur,
            "statut": statut,
            "commentaire": commentaire
        })

    conn.commit()
    conn.close()
    return results

def execute_swap_slots(slot1_id, slot2_id):
    """
    Permet d'échanger deux formateurs entre deux dates (résolution de conflit 6 <-> 7).
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM planning_slots WHERE id = ?", (slot1_id,))
    s1 = cursor.fetchone()
    cursor.execute("SELECT * FROM planning_slots WHERE id = ?", (slot2_id,))
    s2 = cursor.fetchone()

    if not s1 or not s2:
        conn.close()
        return {"success": False, "message": "Créneaux introuvables."}

    s1 = dict(s1)
    s2 = dict(s2)

    # Inverser les formateurs et mettre à jour le statut en 'Proposé' ou 'Confirmé'
    cursor.execute("UPDATE planning_slots SET formateur_id = ?, statut_slot = 'Confirmé', commentaire = ? WHERE id = ?",
                   (s2['formateur_id'], f"Échangé avec le créneau du {s2['date_slot']}", slot1_id))

    cursor.execute("UPDATE planning_slots SET formateur_id = ?, statut_slot = 'Confirmé', commentaire = ? WHERE id = ?",
                   (s1['formateur_id'], f"Échangé avec le créneau du {s1['date_slot']}", slot2_id))

    # Mettre à jour la table des factures liée
    cursor.execute("UPDATE factures_formateurs SET formateur_id = ? WHERE planning_slot_id = ?", (s2['formateur_id'], slot1_id))
    cursor.execute("UPDATE factures_formateurs SET formateur_id = ? WHERE planning_slot_id = ?", (s1['formateur_id'], slot2_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Échange réussi entre le {s1['date_slot']} et le {s2['date_slot']}."
    }

def generate_solicitation_email(slot_id):
    """
    Génère l'email officiel de proposition de vacation à un formateur.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, f.nom as formateur_nom, f.prenom as formateur_prenom, f.email as formateur_email, f.taux_journalier,
           s.titre as session_titre, s.lieu_principal
    FROM planning_slots p
    JOIN formateurs f ON p.formateur_id = f.id
    JOIN sessions s ON p.session_id = s.id
    WHERE p.id = ?
    """, (slot_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    r = dict(row)
    dt_formatted = datetime.strptime(r['date_slot'], "%Y-%m-%d").strftime("%d/%m/%Y")
    day_name = get_day_name(r['date_slot']).capitalize()

    objet = f"Sollicitation d'intervention : {r['thematique']} - {r['session_titre']} le {dt_formatted}"
    corps = f"""Bonjour {r['formateur_prenom']},

Dans le cadre de la formation {r['session_titre']}, nous avons le plaisir de te solliciter pour animer le module suivant :

📌 Thématique : {r['thematique']}
📅 Date : {day_name} {dt_formatted}
⏰ Horaires : 09h00 - 12h30 / 13h30 - 17h00 (7 heures)
📍 Lieu : {r['lieu_principal']} - {r['salle']}
💰 Rémunération convenue : {r['taux_journalier']} € HT (forfait journée)

Pourrais-tu nous confirmer ta disponibilité dès que possible ?
En cas d'indisponibilité sur cette date, n'hésite pas à nous proposer un jour alternatif sur la même semaine afin d'ajuster notre calendrier.

Bien cordialement,
La Direction Pédagogique & Coordination JEPS
"""

    return {
        "destinataire_nom": f"{r['formateur_prenom']} {r['formateur_nom']}",
        "destinataire_email": r['formateur_email'],
        "objet": objet,
        "corps": corps,
        "slot_id": slot_id,
        "date_slot": r['date_slot'],
        "thematique": r['thematique']
    }

def process_trainer_response(slot_id, reponse_type):
    """
    Traite la réponse du formateur ('accepte', 'refuse', 'swap') et met à jour le planning + facturation.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.*, f.taux_journalier 
    FROM planning_slots p 
    JOIN formateurs f ON p.formateur_id = f.id 
    WHERE p.id = ?
    """, (slot_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "Créneau introuvable."}

    r = dict(row)

    if reponse_type == "accepte":
        cursor.execute("UPDATE planning_slots SET statut_slot = 'Confirmé', commentaire = 'Disponibilité confirmée par le formateur' WHERE id = ?", (slot_id,))
        # Créer ou mettre à jour la ligne de pré-facturation
        cursor.execute("SELECT id FROM factures_formateurs WHERE planning_slot_id = ?", (slot_id,))
        fac_row = cursor.fetchone()
        if not fac_row:
            cursor.execute("""
            INSERT INTO factures_formateurs (formateur_id, session_id, planning_slot_id, date_intervention, thematique, nb_heures, montant_ht, statut_intervention, statut_paiement)
            VALUES (?, ?, ?, ?, ?, 7.0, ?, 'Planifié', 'En attente facture')
            """, (r['formateur_id'], r['session_id'], slot_id, r['date_slot'], r['thematique'], r['taux_journalier']))
        msg = "Disponibilité confirmée avec succès. Créneau verrouillé."
    elif reponse_type == "refuse":
        cursor.execute("UPDATE planning_slots SET statut_slot = 'À attribuer', formateur_id = NULL, commentaire = 'Formateur indisponible - À réassigner' WHERE id = ?", (slot_id,))
        msg = "Créneau libéré pour réattribution."
    else:
        cursor.execute("UPDATE planning_slots SET statut_slot = 'À négocier', commentaire = 'Échange de date proposé' WHERE id = ?", (slot_id,))
        msg = "Statut passé en négociation."

    conn.commit()
    conn.close()
    return {"success": True, "message": msg}

def add_planning_slot(session_id, date_slot, thematique, formateur_id=None, periode="Journée", nb_heures=7.0, salle="Salle Principale A1", commentaire=""):
    """Ajoute manuellement un créneau au planning."""
    conn = get_db()
    cursor = conn.cursor()
    statut = "Confirmé" if formateur_id else "À attribuer"
    cursor.execute("""
    INSERT INTO planning_slots (session_id, date_slot, periode, nb_heures, thematique, formateur_id, statut_slot, salle, commentaire)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, date_slot, periode, nb_heures, thematique, formateur_id, statut, salle, commentaire))
    slot_id = cursor.lastrowid

    # Si formateur assigné, créer ligne facture
    if formateur_id:
        cursor.execute("SELECT taux_journalier FROM formateurs WHERE id = ?", (formateur_id,))
        f_row = cursor.fetchone()
        taux = f_row[0] if f_row else 420.0
        cursor.execute("""
        INSERT INTO factures_formateurs (formateur_id, session_id, planning_slot_id, date_intervention, thematique, nb_heures, montant_ht, statut_intervention, statut_paiement)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Planifié', 'En attente facture')
        """, (formateur_id, session_id, slot_id, date_slot, thematique, nb_heures, taux))

    conn.commit()
    conn.close()
    return {"success": True, "slot_id": slot_id, "message": "Créneau ajouté avec succès."}

def update_planning_slot(slot_id, date_slot, thematique, formateur_id, periode="Journée", nb_heures=7.0, salle="Salle Principale A1", statut_slot="Confirmé", commentaire=""):
    """Modifie un créneau existant."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE planning_slots
    SET date_slot = ?, thematique = ?, formateur_id = ?, periode = ?, nb_heures = ?, salle = ?, statut_slot = ?, commentaire = ?
    WHERE id = ?
    """, (date_slot, thematique, formateur_id, periode, nb_heures, salle, statut_slot, commentaire, slot_id))

    # Mettre à jour la facture liée
    if formateur_id:
        cursor.execute("SELECT taux_journalier FROM formateurs WHERE id = ?", (formateur_id,))
        f_row = cursor.fetchone()
        taux = f_row[0] if f_row else 420.0
        cursor.execute("SELECT id FROM factures_formateurs WHERE planning_slot_id = ?", (slot_id,))
        fac = cursor.fetchone()
        if fac:
            cursor.execute("""
            UPDATE factures_formateurs
            SET formateur_id = ?, date_intervention = ?, thematique = ?, nb_heures = ?, montant_ht = ?
            WHERE id = ?
            """, (formateur_id, date_slot, thematique, nb_heures, taux, fac[0]))
        else:
            cursor.execute("SELECT session_id FROM planning_slots WHERE id = ?", (slot_id,))
            ses_row = cursor.fetchone()
            ses_id = ses_row[0] if ses_row else 1
            cursor.execute("""
            INSERT INTO factures_formateurs (formateur_id, session_id, planning_slot_id, date_intervention, thematique, nb_heures, montant_ht, statut_intervention, statut_paiement)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Planifié', 'En attente facture')
            """, (formateur_id, ses_id, slot_id, date_slot, thematique, nb_heures, taux))

    conn.commit()
    conn.close()
    return {"success": True, "message": "Créneau mis à jour avec succès."}

def delete_planning_slot(slot_id):
    """Supprime un créneau du planning et ses liaisons comptables."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM factures_formateurs WHERE planning_slot_id = ?", (slot_id,))
    cursor.execute("DELETE FROM planning_slots WHERE id = ?", (slot_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Créneau supprimé avec succès."}

def mark_slot_completed(slot_id):
    """Marque la vacation comme effectuée et passe la ligne comptable en 'Effectué'."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE planning_slots SET statut_slot = 'Effectué' WHERE id = ?", (slot_id,))
    cursor.execute("UPDATE factures_formateurs SET statut_intervention = 'Effectué' WHERE planning_slot_id = ?", (slot_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Journée validée comme effectuée. Prête pour facturation."}

def import_persen_csv(csv_content, session_id=1):
    """
    Importe un planning ou dossier stagiaires exporté depuis l'application ministérielle PERSEN / DRAJES.
    Gère automatiquement les délimiteurs ';' ou ',' et le mapping des colonnes Persen.
    """
    import csv
    import io

    reader = csv.reader(io.StringIO(csv_content.strip()), delimiter=';')
    rows = list(reader)
    if not rows or len(rows) < 2:
        reader = csv.reader(io.StringIO(csv_content.strip()), delimiter=',')
        rows = list(reader)

    if not rows or len(rows) < 2:
        return {"success": False, "message": "Fichier CSV vide ou non reconnu."}

    header = [h.strip().lower() for h in rows[0]]
    imported_count = 0
    conn = get_db()
    cursor = conn.cursor()

    # Détecter si c'est un fichier de stagiaires ou de planning
    is_stagiaire_file = any("stagiaire" in h or "candidat" in h or "nom" in h for h in header) and any("prenom" in h for h in header)

    if is_stagiaire_file:
        col_nom = next((i for i, h in enumerate(header) if "nom" in h), 0)
        col_prenom = next((i for i, h in enumerate(header) if "prenom" in h), 1)
        col_email = next((i for i, h in enumerate(header) if "mail" in h), None)
        col_structure = next((i for i, h in enumerate(header) if "structure" in h or "employeur" in h or "club" in h), None)
        col_tuteur = next((i for i, h in enumerate(header) if "tuteur" in h), None)

        for row in rows[1:]:
            if not row or len(row) <= max(col_nom, col_prenom):
                continue
            nom = row[col_nom].strip()
            prenom = row[col_prenom].strip()
            if not nom or not prenom:
                continue
            email = row[col_email].strip() if col_email and len(row) > col_email else f"{prenom.lower()}.{nom.lower()}@persen-import.fr"
            structure = row[col_structure].strip() if col_structure and len(row) > col_structure else "Structure Partenaire Persen"
            tuteur = row[col_tuteur].strip() if col_tuteur and len(row) > col_tuteur else "Tuteur Désigné"

            cursor.execute("""
            INSERT INTO stagiaires (session_id, nom, prenom, email, telephone, statut_financement, structure_accueil, tuteur_nom, tuteur_telephone, statut_dossier_projet)
            VALUES (?, ?, ?, ?, '06 00 00 00 00', 'Apprentissage Persen', ?, ?, '01 00 00 00 00', 'En rédaction')
            """, (session_id, nom, prenom, email, structure, tuteur))
            imported_count += 1

        msg = f"Import Persen réussi : {imported_count} stagiaires importés avec succès."
    else:
        # Fichier de planning / calendrier Persen
        col_date = next((i for i, h in enumerate(header) if "date" in h or "jour" in h), 0)
        col_theme = next((i for i, h in enumerate(header) if "module" in h or "theme" in h or "intitule" in h or "uc" in h), 1)
        col_formateur = next((i for i, h in enumerate(header) if "formateur" in h or "intervenant" in h), None)
        col_salle = next((i for i, h in enumerate(header) if "salle" in h or "lieu" in h), None)

        for row in rows[1:]:
            if not row or len(row) <= max(col_date, col_theme):
                continue
            d_raw = row[col_date].strip()
            theme = row[col_theme].strip()
            if not d_raw or not theme:
                continue

            # Normaliser date JJ/MM/AAAA -> AAAA-MM-JJ
            if "/" in d_raw:
                parts = d_raw.split("/")
                if len(parts) == 3:
                    d_iso = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                else:
                    d_iso = d_raw
            else:
                d_iso = d_raw

            salle = row[col_salle].strip() if col_salle and len(row) > col_salle else "Salle Principale A1"

            # Recherche formateur si présent
            f_id = None
            if col_formateur and len(row) > col_formateur:
                f_name = row[col_formateur].strip().lower()
                cursor.execute("SELECT id FROM formateurs WHERE lower(nom) LIKE ? OR lower(prenom) LIKE ?", (f"%{f_name}%", f"%{f_name}%"))
                f_match = cursor.fetchone()
                if f_match:
                    f_id = f_match[0]

            cursor.execute("""
            INSERT INTO planning_slots (session_id, date_slot, periode, nb_heures, thematique, formateur_id, statut_slot, salle, commentaire)
            VALUES (?, ?, 'Journée', 7.0, ?, ?, ?, ?, 'Importé depuis calendrier Persen')
            """, (session_id, d_iso, theme, f_id, "Confirmé" if f_id else "À attribuer", salle))
            imported_count += 1

        msg = f"Import Persen réussi : {imported_count} créneaux de planning importés avec succès."

    conn.commit()
    conn.close()
    return {"success": True, "imported_count": imported_count, "message": msg}

