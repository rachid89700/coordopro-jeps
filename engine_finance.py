"""
Engine Comptable & Suivi Budgétaire Formateurs :
Matrice interactive de facturation et de paiement, indicateurs de trésorerie, export Excel/CSV.
"""

import csv
import io
from datetime import datetime
from database import get_db

def get_finance_matrix(session_id=None):
    """
    Renvoie la matrice complète de suivi des interventions, factures et règlements formateurs.
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT f.*, form.nom as formateur_nom, form.prenom as formateur_prenom, form.statut as formateur_statut,
           s.titre as session_titre, s.code_session, s.budget_prev_formateurs
    FROM factures_formateurs f
    JOIN formateurs form ON f.formateur_id = form.id
    JOIN sessions s ON f.session_id = s.id
    """
    params = []
    if session_id:
        query += " WHERE f.session_id = ?"
        params.append(session_id)

    query += " ORDER BY f.date_intervention DESC"
    cursor.execute(query, tuple(params))
    rows = [dict(r) for r in cursor.fetchall()]

    # Calculs de synthèse budgétaire
    if session_id:
        cursor.execute("SELECT SUM(budget_prev_formateurs) FROM sessions WHERE id = ?", (session_id,))
    else:
        cursor.execute("SELECT SUM(budget_prev_formateurs) FROM sessions")
    budget_prev = cursor.fetchone()[0] or 0.0

    total_engage = sum(r['montant_ht'] for r in rows)
    total_facture_recue = sum(r['montant_ht'] for r in rows if r['statut_paiement'] in ['Facture reçue', 'Transmis en paiement', 'Payé'])
    total_paye = sum(r['montant_ht'] for r in rows if r['statut_paiement'] == 'Payé')
    reste_a_payer = total_engage - total_paye
    marge_budgetaire = budget_prev - total_engage

    conn.close()

    return {
        "items": rows,
        "kpis": {
            "budget_previsionnel": round(budget_prev, 2),
            "total_engage": round(total_engage, 2),
            "total_facture_recue": round(total_facture_recue, 2),
            "total_paye": round(total_paye, 2),
            "reste_a_payer": round(reste_a_payer, 2),
            "marge_budgetaire": round(marge_budgetaire, 2),
            "taux_consommation_budget": round((total_engage / budget_prev * 100), 1) if budget_prev > 0 else 0
        }
    }

def update_facture_status(facture_id, statut_paiement, numero_facture=None, date_reception=None, date_transmission=None, date_paiement=None):
    """
    Met à jour une ligne de facture formateur dans la matrice.
    """
    conn = get_db()
    cursor = conn.cursor()

    fields = ["statut_paiement = ?"]
    params = [statut_paiement]

    if numero_facture is not None:
        fields.append("numero_facture = ?")
        params.append(numero_facture)
    if date_reception is not None:
        fields.append("date_reception_facture = ?")
        params.append(date_reception)
    if date_transmission is not None:
        fields.append("date_transmission_compta = ?")
        params.append(date_transmission)
    if date_paiement is not None:
        fields.append("date_paiement = ?")
        params.append(date_paiement)

    params.append(facture_id)
    query = f"UPDATE factures_formateurs SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()

    return {"success": True, "message": "Statut de facturation mis à jour avec succès."}

def export_finance_csv(session_id=None):
    """
    Exporte la matrice financière en fichier CSV compatible Microsoft Excel.
    """
    data = get_finance_matrix(session_id)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # En-têtes CSV
    writer.writerow([
        "ID", "Session", "Formateur", "Date Intervention", "Thématique",
        "Heures", "Montant HT (€)", "Statut Intervention", "Numéro Facture",
        "Date Réception Facture", "Date Transmission Compta", "Statut Paiement",
        "Date Paiement", "Mode Règlement"
    ])

    for item in data['items']:
        writer.writerow([
            item['id'],
            item['code_session'],
            f"{item['formateur_prenom']} {item['formateur_nom']}",
            item['date_intervention'],
            item['thematique'],
            item['nb_heures'],
            f"{item['montant_ht']:.2f}",
            item['statut_intervention'],
            item.get('numero_facture') or '',
            item.get('date_reception_facture') or '',
            item.get('date_transmission_compta') or '',
            item['statut_paiement'],
            item.get('date_paiement') or '',
            item.get('mode_reglement') or 'Virement bancaire'
        ])

    return output.getvalue()
