"""
Engine Stagiaires & Certifications :
1. Générateur de Convocations Certificatives Officielles (individuelles ou groupe)
2. Générateur de Planning Mensuel Stagiaire (envoi anticipé)
3. Suivi des Livrables & Relances Automatiques
"""

from datetime import datetime
from database import get_db

def get_organisme_header():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM organisme LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def generate_convocations_html(session_id, stagiaire_id=None):
    """
    Génère les convocations officielles imprimables conformes DRAJES.
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT c.*, s.nom as stg_nom, s.prenom as stg_prenom, s.date_naissance, s.structure_accueil, s.email as stg_email,
           ses.titre as session_titre, ses.lieu_principal, r.intitule as diplome_titre, r.code_rncp
    FROM convocations c
    JOIN stagiaires s ON c.stagiaire_id = s.id
    JOIN sessions ses ON c.session_id = ses.id
    JOIN referentiels r ON ses.diplome_code = r.code_diplome
    WHERE c.session_id = ?
    """
    params = [session_id]
    if stagiaire_id:
        query += " AND c.stagiaire_id = ?"
        params.append(stagiaire_id)

    query += " ORDER BY c.date_epreuve, c.heure_passage"
    cursor.execute(query, tuple(params))
    convs = [dict(c) for c in cursor.fetchall()]
    org = get_organisme_header()
    conn.close()

    if not convs:
        return "<p>Aucune convocation trouvée.</p>"

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Convocations Officielles aux Certifications DRAJES</title>
        <style>
            @page {{ size: A4; margin: 15mm; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1e293b; line-height: 1.4; font-size: 13px; background: #fff; margin: 0; padding: 20px; }}
            .convocation-page {{ border: 2px solid #0f172a; padding: 25px; border-radius: 8px; margin-bottom: 30px; page-break-after: always; min-height: 900px; box-sizing: border-box; position: relative; }}
            .convocation-page:last-child {{ page-break-after: avoid; }}
            .header-table {{ width: 100%; border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px; }}
            .rf-flag {{ font-size: 11px; font-weight: bold; text-transform: uppercase; color: #1e3a8a; }}
            .of-info {{ text-align: right; font-size: 11px; color: #475569; }}
            .conv-title {{ text-align: center; font-size: 18px; font-weight: bold; text-transform: uppercase; color: #0f172a; margin: 25px 0 10px 0; border: 1px solid #cbd5e1; background: #f8fafc; padding: 10px; border-radius: 6px; }}
            .stg-card {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 15px; margin: 20px 0; }}
            .stg-card table {{ width: 100%; border: none; }}
            .stg-card td {{ border: none; padding: 4px 6px; font-size: 13px; }}
            .epreuve-box {{ border: 1px solid #cbd5e1; border-radius: 6px; padding: 15px; margin: 20px 0; }}
            .epreuve-box table {{ width: 100%; border-collapse: collapse; }}
            .epreuve-box th, .epreuve-box td {{ border: 1px solid #e2e8f0; padding: 8px 12px; }}
            .epreuve-box th {{ background: #f1f5f9; width: 30%; }}
            .consignes {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 12px 15px; font-size: 12px; margin: 20px 0; color: #92400e; }}
            .btn-print {{ background: #0284c7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }}
            @media print {{ .no-print {{ display: none; }} body {{ padding: 0; }} }}
        </style>
    </head>
    <body>
        <div class="no-print" style="text-align: right; margin-bottom: 20px;">
            <button class="btn-print" onclick="window.print()">🖨️ Imprimer toutes les convocations ({len(convs)})</button>
        </div>
    """

    for c in convs:
        dt_obj = datetime.strptime(c['date_epreuve'], "%Y-%m-%d").strftime("%d/%m/%Y")
        html += f"""
        <div class="convocation-page">
            <table class="header-table" style="border: none;">
                <tr style="border: none;">
                    <td style="border: none; width: 50%;">
                        <div class="rf-flag">RÉPUBLIQUE FRANÇAISE</div>
                        <div style="font-size: 11px; color: #64748b;">MINISTÈRE DES SPORTS ET DES JEUX OLYMPIQUES<br>DRAJES - DÉLÉGATION RÉGIONALE ACADÉMIQUE</div>
                    </td>
                    <td style="border: none; text-align: right;" class="of-info">
                        <strong>{org.get('nom')}</strong><br>
                        Centre d'Examen Habilité JEPS<br>
                        Certifié QUALIOPI N° {org.get('qualiopi_num')}
                    </td>
                </tr>
            </table>

            <div class="conv-title">CONVOCATION OFFICIELLE À L'ÉPREUVE DE CERTIFICATION</div>

            <div class="stg-card">
                <table>
                    <tr><td><strong>Candidat(e) :</strong></td><td style="font-size: 15px; font-weight: bold; color: #1e3a8a;">{c['stg_prenom'].upper()} {c['stg_nom'].upper()}</td></tr>
                    <tr><td><strong>Date de naissance :</strong></td><td>{c.get('date_naissance', 'Non renseignée')}</td></tr>
                    <tr><td><strong>Formation préparée :</strong></td><td><strong>{c['diplome_titre']}</strong> (RNCP : {c['code_rncp']})</td></tr>
                    <tr><td><strong>Session :</strong></td><td>{c['session_titre']}</td></tr>
                    <tr><td><strong>Structure d'alternance :</strong></td><td>{c.get('structure_accueil', 'Non renseignée')}</td></tr>
                </table>
            </div>

            <div class="epreuve-box">
                <table>
                    <tr><th>Épreuve Certificative</th><td style="color: #0369a1; font-weight: bold; font-size: 14px;">{c['titre_epreuve']}</td></tr>
                    <tr><th>Date de l'épreuve</th><td><strong>{dt_obj}</strong></td></tr>
                    <tr><th>Heure précise de passage</th><td style="font-size: 15px; font-weight: bold; color: #dc2626;">{c['heure_passage']} (Se présenter 20 min avant)</td></tr>
                    <tr><th>Lieu & Salle d'examen</th><td><strong>{c['salle_ou_plateau']}</strong><br><span style="font-size: 11px; color: #64748b;">{c['lieu_principal']}</span></td></tr>
                    <tr><th>Commission de Jury</th><td>{c['composition_jury']}</td></tr>
                </table>
            </div>

            <div class="consignes">
                <strong>⚠️ CONSIGNES STRICTES ET PIÈCES À PRODUIRE LE JOUR DE L'ÉPREUVE :</strong>
                <ul style="margin: 5px 0 0 0; padding-left: 20px;">
                    <li>Présenter une <strong>pièce d'identité originale en cours de validité</strong> (CNI, Passeport, Titre de séjour).</li>
                    <li>Remettre <strong>3 exemplaires papier reliés</strong> du dossier de projet certifié par votre tuteur de structure.</li>
                    <li>Tout retard entraînera le refus d'accès à l'épreuve et le signalement immédiat à la DRAJES pour note éliminatoire.</li>
                    <li>La présente convocation doit être émargée sur place devant les examinateurs.</li>
                </ul>
            </div>

            <div style="margin-top: 40px; display: flex; justify-content: space-between; align-items: flex-end;">
                <div>
                    Fait à {org.get('ville')}, le {datetime.now().strftime('%d/%m/%Y')}<br>
                    <strong>Le Coordonnateur Pédagogique :</strong><br>
                    <em>Signature autorisée</em>
                </div>
                <div style="border: 1px dashed #94a3b8; padding: 10px 20px; font-size: 11px; text-align: center; border-radius: 4px;">
                    Émargement du Candidat le jour de l'épreuve :<br><br><br>
                </div>
            </div>
        </div>
        """

    html += "</body></html>"
    return html

def generate_monthly_planning_html(session_id, month_year="2026-10"):
    """
    Génère le planning mensuel destiné aux stagiaires et tuteurs (envoi anticipé la semaine précédente).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, f.nom as formateur_nom, f.prenom as formateur_prenom, s.titre as session_titre
    FROM planning_slots p
    LEFT JOIN formateurs f ON p.formateur_id = f.id
    JOIN sessions s ON p.session_id = s.id
    WHERE p.session_id = ? AND p.date_slot LIKE ?
    ORDER BY p.date_slot, p.periode
    """, (session_id, f"{month_year}%"))
    slots = [dict(s) for s in cursor.fetchall()]
    org = get_organisme_header()
    conn.close()

    month_name = "Octobre 2026" if "10" in month_year else month_year

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Planning de Formation - {month_name}</title>
        <style>
            @page {{ size: A4 landscape; margin: 12mm; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1e293b; font-size: 12px; background: #fff; margin: 0; padding: 20px; }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #0284c7; padding-bottom: 10px; margin-bottom: 15px; }}
            h1 {{ font-size: 18px; color: #0f172a; margin: 0 0 5px 0; text-transform: uppercase; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 9px 12px; text-align: left; }}
            th {{ background: #0284c7; color: white; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
            tr:nth-child(even) {{ background: #f8fafc; }}
            .badge-lieu {{ background: #e0f2fe; color: #0369a1; padding: 3px 6px; border-radius: 4px; font-weight: 600; font-size: 10px; }}
            .btn-print {{ background: #0284c7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; }}
            @media print {{ .no-print {{ display: none; }} body {{ padding: 0; }} }}
        </style>
    </head>
    <body>
        <div class="no-print" style="text-align: right; margin-bottom: 15px;">
            <button class="btn-print" onclick="window.print()">🖨️ Imprimer / Exporter le Planning Mensuel ({month_name})</button>
        </div>

        <div class="header">
            <div>
                <h1>CALENDRIER MENSUEL DE FORMATION — {month_name.upper()}</h1>
                <div style="color: #64748b; font-size: 12px;">Transmis aux Stagiaires et Tuteurs d'Entreprise | {org.get('nom')}</div>
            </div>
            <div style="text-align: right; font-size: 11px; color: #64748b;">
                Horaires Centre : 09h00 - 12h30 / 13h30 - 17h00 (7h/j)<br>
                Émargement obligatoire matin & après-midi
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 14%;">Date</th>
                    <th style="width: 12%;">Créneau</th>
                    <th style="width: 30%;">Module & Contenu Pédagogique</th>
                    <th style="width: 22%;">Intervenant Formateur</th>
                    <th style="width: 22%;">Lieu / Salle</th>
                </tr>
            </thead>
            <tbody>
    """

    for s in slots:
        dt = datetime.strptime(s['date_slot'], "%Y-%m-%d").strftime("%d/%m/%Y")
        formateur_str = f"{s['formateur_prenom']} {s['formateur_nom']}" if s['formateur_nom'] else "Équipe Pédagogique"
        html += f"""
                <tr>
                    <td><strong>{dt}</strong></td>
                    <td>{s['periode']}</td>
                    <td><strong>{s['thematique']}</strong><br><span style="font-size: 10px; color: #64748b;">{s.get('commentaire') or ''}</span></td>
                    <td>{formateur_str}</td>
                    <td><span class="badge-lieu">{s['salle']}</span></td>
                </tr>
        """

    html += """
            </tbody>
        </table>
        <div style="margin-top: 20px; font-size: 11px; color: #64748b;">
            💡 <strong>Rappel Qualiopi / DRAJES :</strong> Toute absence doit être immédiatement justifiée par écrit auprès de la coordination sous 48h avec copie à votre employeur/tuteur.
        </div>
    </body>
    </html>
    """
    return html

def get_stagiaires_deadlines(session_id):
    """
    Calcule le compte à rebours et prépare les emails de relance automatique pour le dépôt du dossier de projet.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT date_depot_dossier_projet FROM sessions WHERE id = ?", (session_id,))
    s_row = cursor.fetchone()
    if not s_row or not s_row[0]:
        conn.close()
        return []

    date_limite_str = s_row[0]
    dt_limite = datetime.strptime(date_limite_str, "%Y-%m-%d")
    today = datetime.now()
    jours_restants = (dt_limite - today).days

    cursor.execute("SELECT * FROM stagiaires WHERE session_id = ? ORDER BY nom", (session_id,))
    stagiaires = [dict(s) for s in cursor.fetchall()]
    conn.close()

    results = []
    for st in stagiaires:
        statut = st['statut_dossier_projet']
        alerte_niveau = "Normal"
        relance_sujet = ""
        relance_texte = ""

        if statut != "Validé pour jury":
            if jours_restants < 0:
                alerte_niveau = "Retard Critique"
            elif jours_restants <= 7:
                alerte_niveau = "Urgent J-7"
            elif jours_restants <= 15:
                alerte_niveau = "Attention J-15"

            relance_sujet = f"Rappel Échéance : Dépôt du Dossier de Projet UC1/UC2 avant le {dt_limite.strftime('%d/%m/%Y')}"
            relance_texte = f"""Bonjour {st['prenom']},

Nous te rappelons que la date limite impérative de dépôt de ton Dossier de Projet UC1/UC2 pour la session DRAJES est fixée au :
📅 {dt_limite.strftime('%d/%m/%Y')} à 18h00 ({jours_restants} jours restants).

Ton dossier doit comporter la validation écrite de ton tuteur ({st['tuteur_nom']}) et être déposé en format numérique sur l'extranet et en 3 exemplaires reliés au centre de formation.

En cas de difficulté de rédaction, contacte immédiatement ton coordonnateur pédagogique.

Bien cordialement,
La Coordination Pédagogique JEPS
"""

        results.append({
            "stagiaire_id": st['id'],
            "nom_complet": f"{st['prenom']} {st['nom']}",
            "email": st['email'],
            "tuteur": st['tuteur_nom'],
            "statut_dossier": statut,
            "date_limite": date_limite_str,
            "jours_restants": jours_restants,
            "alerte_niveau": alerte_niveau,
            "email_relance_sujet": relance_sujet,
            "email_relance_texte": relance_texte
        })

    return results
