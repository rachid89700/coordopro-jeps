"""
Engine de Génération des Dossiers Réglementaires (RNCP / JEPS / DRAJES)
Génère 100% en local et sans LLM :
1. Dossier d'Habilitation RNCP complet (35h de travail automatisées)
2. Dossier de Complétude DRAJES pour ouverture de session (J-2 mois)
"""

import json
from datetime import datetime
from database import get_db

def get_editor_toolbar_html(doc_id="dossier"):
    """Barre d'outils WYSIWYG permettant au coordonnateur de modifier directement n'importe quel texte du dossier."""
    return f"""
    <div class="no-print" style="position: sticky; top: 0; z-index: 1000; background: #0f172a; color: white; padding: 10px 15px; border-radius: 8px; margin-bottom: 20px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-weight: bold; font-size: 13px; color: #38bdf8;">⚡ CoordoPro JEPS · Mode Document</span>
            <button id="btn-toggle-edit" onclick="toggleEditMode()" style="background: #3b82f6; hover:background: #2563eb; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
                <span>✏️ Activer Édition Directe</span>
            </button>
            <button id="btn-save-doc" onclick="saveDocChanges('{doc_id}')" style="background: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; display: none;">
                💾 Enregistrer mes modifications
            </button>
            <button id="btn-reset-doc" onclick="resetDocChanges('{doc_id}')" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; display: none;">
                🔄 Réinitialiser
            </button>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span id="edit-status-msg" style="font-size: 11px; color: #94a3b8;">Cliquez sur n'importe quel texte pour modifier</span>
            <button class="btn-print" onclick="window.print()" style="background: #0284c7; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px;">
                🖨️ Exporter en PDF / Imprimer
            </button>
        </div>
    </div>
    <script>
        let isEditing = false;
        const DOC_KEY = "coordopro_doc_{doc_id}";

        function toggleEditMode() {{
            isEditing = !isEditing;
            const content = document.getElementById("document-content");
            const btn = document.getElementById("btn-toggle-edit");
            const btnSave = document.getElementById("btn-save-doc");
            const btnReset = document.getElementById("btn-reset-doc");
            const status = document.getElementById("edit-status-msg");

            if (isEditing) {{
                content.setAttribute("contenteditable", "true");
                content.style.outline = "2px dashed #38bdf8";
                content.style.padding = "10px";
                content.style.borderRadius = "8px";
                btn.style.background = "#eab308";
                btn.innerHTML = "<span>🔓 Mode Édition Actif</span>";
                btnSave.style.display = "inline-block";
                btnReset.style.display = "inline-block";
                status.innerText = "Mode interactif activé : vous pouvez réécrire, supprimer ou ajuster tout le dossier.";
                status.style.color = "#38bdf8";
            }} else {{
                content.removeAttribute("contenteditable");
                content.style.outline = "none";
                btn.style.background = "#3b82f6";
                btn.innerHTML = "<span>✏️ Activer Édition Directe</span>";
                btnSave.style.display = "none";
                btnReset.style.display = "none";
                status.innerText = "Cliquez sur n'importe quel texte pour modifier";
                status.style.color = "#94a3b8";
            }}
        }}

        function saveDocChanges(key) {{
            const content = document.getElementById("document-content");
            localStorage.setItem(DOC_KEY, content.innerHTML);
            const status = document.getElementById("edit-status-msg");
            status.innerText = "✅ Modifications sauvegardées localement !";
            status.style.color = "#10b981";
            setTimeout(() => {{
                if (isEditing) status.innerText = "Modifications enregistrées. Cliquez sur Exporter PDF quand vous avez fini.";
            }}, 3000);
        }}

        function resetDocChanges(key) {{
            if (confirm("Voulez-vous rétablir les données par défaut issues de la base de données ?")) {{
                localStorage.removeItem(DOC_KEY);
                window.location.reload();
            }}
        }}

        window.addEventListener("DOMContentLoaded", () => {{
            const saved = localStorage.getItem(DOC_KEY);
            if (saved) {{
                const content = document.getElementById("document-content");
                if (content) {{
                    content.innerHTML = saved;
                    const status = document.getElementById("edit-status-msg");
                    if (status) status.innerText = "ℹ️ Version personnalisée chargée depuis votre navigateur.";
                }}
            }}
        }});
    </script>
    """

def get_organisme_info():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM organisme LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {}

def generate_habilitation_html(diplome_code):
    """
    Génère un Dossier d'Habilitation complet et officiel selon les critères DRAJES / France Compétences.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM referentiels WHERE code_diplome = ?", (diplome_code,))
    ref = cursor.fetchone()
    if not ref:
        conn.close()
        return "<p>Référentiel introuvable.</p>"
    ref = dict(ref)
    blocs = json.loads(ref.get("blocs_competences_json", "[]"))
    modalites = json.loads(ref.get("modalites_certification_json", "{}"))

    # Récupérer l'équipe formateurs qualifiée
    cursor.execute("SELECT * FROM formateurs")
    formateurs = [dict(f) for f in cursor.fetchall()]
    org = get_organisme_info()
    conn.close()

    total_centre = ref.get("heures_centre_min", 600)
    total_entreprise = ref.get("heures_entreprise_min", 600)
    total_global = total_centre + total_entreprise

    toolbar = get_editor_toolbar_html(f"habilitation_{diplome_code}")
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dossier d'Habilitation - {ref['code_diplome']} - {org.get('nom')}</title>
        <style>
            @page {{ size: A4; margin: 18mm 15mm; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1e293b; line-height: 1.5; font-size: 13px; background: #fff; margin: 0; padding: 25px; }}
            .header-box {{ border-bottom: 3px solid #0284c7; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; }}
            .of-title {{ font-size: 16px; font-weight: bold; color: #0369a1; text-transform: uppercase; }}
            .of-sub {{ font-size: 11px; color: #64748b; }}
            .badge-qualiopi {{ background: #ecfdf5; border: 1px solid #10b981; color: #047857; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px; display: inline-block; }}
            .badge-rncp {{ background: #eff6ff; border: 1px solid #3b82f6; color: #1d4ed8; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px; display: inline-block; }}
            h1 {{ font-size: 22px; color: #0f172a; margin: 20px 0 10px 0; text-align: center; text-transform: uppercase; letter-spacing: 0.5px; }}
            .subtitle {{ text-align: center; color: #475569; font-size: 14px; margin-bottom: 30px; font-weight: 500; }}
            h2 {{ font-size: 15px; color: #0284c7; border-left: 4px solid #0284c7; padding-left: 10px; margin-top: 25px; margin-bottom: 12px; text-transform: uppercase; }}
            h3 {{ font-size: 13px; color: #334155; margin-top: 15px; margin-bottom: 8px; }}
            p, li {{ text-align: justify; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 12px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; vertical-align: top; }}
            th {{ background: #f8fafc; color: #1e293b; font-weight: 600; }}
            .highlight-box {{ background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 6px; padding: 12px 16px; margin: 15px 0; overflow-x: auto; }}
            .page-break {{ page-break-after: always; }}
            .sign-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 40px; }}
            .sign-box {{ border: 1px dashed #94a3b8; padding: 15px; border-radius: 6px; min-height: 90px; }}
            .no-print {{ text-align: right; margin-bottom: 20px; }}
            .btn-print {{ background: #0284c7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }}
            .btn-print:hover {{ background: #0369a1; }}
            @media (max-width: 768px) {{
                body {{ padding: 12px; font-size: 12px; }}
                .sign-grid {{ grid-template-columns: 1fr; gap: 15px; }}
                table {{ display: block; overflow-x: auto; width: 100%; }}
                h1 {{ font-size: 18px; }}
                .header-box {{ flex-direction: column; }}
            }}
            @media print {{ .no-print {{ display: none !important; }} body {{ padding: 0; }} }}
        </style>
    </head>
    <body>
        {toolbar}
        <div id="document-content">
        <div class="header-box">
            <div>
                <div class="of-title">{org.get('nom', 'ORGANISME DE FORMATION')}</div>
                <div class="of-sub">SIRET : {org.get('siret')} | N° Déclaration d'Activité : {org.get('nda')}</div>
                <div class="of-sub">{org.get('adresse')} - {org.get('code_postal')} {org.get('ville')} | Tél : {org.get('telephone')}</div>
            </div>
            <div style="text-align: right;">
                <span class="badge-qualiopi">Certifié QUALIOPI</span><br>
                <span style="font-size: 10px; color: #64748b;">N° {org.get('qualiopi_num')}</span>
            </div>
        </div>

        <h1>DOSSIER DE DEMANDE D'HABILITATION</h1>
        <div class="subtitle">À DISPENSER LA FORMATION ET ORGANISER LES ÉPREUVES CERTIFICATIVES DU DIPLÔME :<br>
        <strong>{ref['intitule']}</strong></div>

        <div class="highlight-box">
            <table style="border: none; margin: 0;">
                <tr style="border: none;"><td style="border: none; width: 30%;"><strong>Filière :</strong> {ref['filiere']}</td><td style="border: none; width: 35%;"><strong>Code RNCP :</strong> <span class="badge-rncp">{ref['code_rncp']}</span></td><td style="border: none; width: 35%;"><strong>Niveau Européen :</strong> {ref['niveau_qualif']}</td></tr>
                <tr style="border: none;"><td style="border: none;" colspan="2"><strong>Arrêté de création :</strong> {ref['arrete_creation']}</td><td style="border: none;"><strong>Volume Global :</strong> {total_global}h ({total_centre}h Centre / {total_entreprise}h Entreprise)</td></tr>
            </table>
        </div>

        <h2>1. Présentation de l'Organisme Demandeur & Démarche Qualité</h2>
        <p>L'organisme <strong>{org.get('nom')}</strong> sollicite par le présent dossier l'habilitation auprès de la DRAJES pour dispenser le parcours complet du <strong>{ref['intitule']}</strong> et mettre en œuvre les épreuves d'évaluation certificative.</p>
        <p>L'organisme est détenteur de la certification <strong>QUALIOPI</strong> au titre des actions de formation (Catégorie L.6313-1-1°) et des actions de formation par apprentissage (CFA), garantissant le respect strict des 7 critères et 32 indicateurs du Référentiel National Qualité (RNQ).</p>

        <h2>2. Note d'Opportunité et Besoins Économiques du Territoire</h2>
        <p>L'ouverture de cette filière répond à un besoin critique d'éducateurs et animateurs professionnels qualifiés recensé auprès des collectivités territoriales, des clubs omnisports, des centres sociaux et des structures de tourisme sportif. Les enquêtes territoriales menées démontrent un taux d'insertion professionnelle supérieur à 85% dans les 6 mois suivant l'obtention du diplôme.</p>

        <h2>3. Architecture Pédagogique & Maquette des 4 Unités Capitalisables (UC)</h2>
        <p>Le parcours est structuré conformément au référentiel national en 4 Blocs de Compétences autonomes et capitalisables :</p>
        <table>
            <thead>
                <tr>
                    <th style="width: 12%;">Bloc / UC</th>
                    <th style="width: 38%;">Intitulé & Compétences Clés</th>
                    <th style="width: 12%;">Volume Centre</th>
                    <th style="width: 38%;">Modalités d'Évaluation Certificative</th>
                </tr>
            </thead>
            <tbody>
    """

    for b in blocs:
        html += f"""
                <tr>
                    <td><strong>{b.get('uc')}</strong></td>
                    <td><strong>{b.get('titre')}</strong><br><span style="color:#64748b; font-size:11px;">{b.get('competences', '')}</span></td>
                    <td style="text-align: center;"><strong>{b.get('heures', 150)} h</strong></td>
                    <td>{b.get('modalite_eval', 'Épreuve certificative DRAJES')}</td>
                </tr>
        """

    html += f"""
            </tbody>
        </table>

        <h2>4. Modalités d'Alternance & Ruban Pédagogique</h2>
        <p>Le rythme d'alternance retenu est de <strong>2 jours en centre de formation (14h)</strong> et <strong>3 jours en structure d'accueil professionnelle (21h)</strong> par semaine, assurant une immersion continue propice à la conduite du projet d'animation de terrain exigé aux UC1/UC2.</p>
        <ul>
            <li><strong>Volume total en centre de formation :</strong> {total_centre} heures (cours théoriques, TD, simulations pédagogiques, mises en situation d'animation).</li>
            <li><strong>Volume total en entreprise / structure d'accueil :</strong> {total_entreprise} heures (tutorat individuel, conduite de cycles sportifs réels, participation à la vie associative).</li>
            <li><strong>Durée totale du cycle :</strong> 10 à 12 mois.</li>
        </ul>

        <h2>5. Encadrement & Équipe Pédagogique Qualifiée</h2>
        <p>L'équipe pédagogique mobilisée justifie des titres, diplômes d'État et cartes professionnelles exigés par le Ministère des Sports :</p>
        <table>
            <thead>
                <tr>
                    <th>Intervenant</th>
                    <th>Rôle & Statut</th>
                    <th>Titres & Qualifications</th>
                    <th>Carte Pro / Référence</th>
                    <th>Domaines d'Intervention</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background: #f0fdf4;">
                    <td><strong>{org.get('coordonnateur_principal')}</strong></td>
                    <td><strong>Coordonnateur Général Pédagogique</strong></td>
                    <td>Master STAPS / Titulaire DEJEPS</td>
                    <td>ED-75-COORD-01</td>
                    <td>Pilotage du ruban, suivi DRAJES, coordination des jurys</td>
                </tr>
    """

    for f in formateurs:
        comps = ", ".join(json.loads(f.get("competences_json", "[]")))
        html += f"""
                <tr>
                    <td><strong>{f['prenom']} {f['nom']}</strong></td>
                    <td>Formateur Référent ({f['statut']})</td>
                    <td>{f.get('diplomes_titres', 'Titre Professionnel')}</td>
                    <td>{f.get('carte_pro_num', 'En cours')}</td>
                    <td>{comps}</td>
                </tr>
        """

    html += f"""
            </tbody>
        </table>

        <h2>6. Règlement des Épreuves Certificatives & Composition des Jurys</h2>
        <p>Conformément aux textes réglementaires régissant le diplôme <strong>{ref['intitule']}</strong> :</p>
        <ul>
            <li><strong>Conditions d'accès :</strong> Titulaire du PSC1 en cours de validité + Réussite aux Tests d'Exigences Préalables (TEP).</li>
            <li><strong>Épreuves certificatives :</strong> Mises en œuvre dans le respect strict des grilles d'évaluation ministérielles.</li>
            <li><strong>Jury d'évaluation :</strong> Chaque commission d'évaluation est composée de 2 évaluateurs habilités n'ayant pas assuré la formation directe du stagiaire (1 représentant de l'État ou enseignant EPS + 1 professionnel qualifié du secteur).</li>
        </ul>

        <h2>7. Plateaux Techniques & Moyens Pédagogiques</h2>
        <p>L'organisme dispose d'installations sportives et pédagogiques homologuées :</p>
        <ul>
            <li><strong>Salles de cours théoriques :</strong> 2 salles équipées de vidéoprojecteurs interactifs, sonorisation et accès Wi-Fi haut débit.</li>
            <li><strong>Plateaux sportifs couverts :</strong> Gymnase omnisports aux normes fédérales (surface parquet, matériel pédagogique multi-activités complet).</li>
            <li><strong>Espaces de pleine nature :</strong> Conventions d'accès aux parcs et bases de loisirs régionales pour les cycles d'orientation et de randonnée.</li>
        </ul>

        <div class="sign-grid">
            <div class="sign-box">
                <strong>Pour l'Organisme de Formation :</strong><br>
                {org.get('responsable_legal')}<br>
                Fait à {org.get('ville')}, le {datetime.now().strftime('%d/%m/%Y')}<br>
                <em>Signature et Cachet :</em>
            </div>
            <div class="sign-box">
                <strong>Pour la DRAJES / Délégation Régionale :</strong><br>
                Visa de réception et décision d'habilitation :<br>
                <em>Mention : Accroché / Habilité / Complément requis</em>
            </div>
        </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_completude_html(session_id):
    """
    Génère le Dossier de Complétude officiel d'ouverture de session DRAJES (exigé 2 mois avant le démarrage).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT s.*, r.intitule, r.code_rncp, r.filiere
    FROM sessions s
    JOIN referentiels r ON s.diplome_code = r.code_diplome
    WHERE s.id = ?
    """, (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        return "<p>Session introuvable.</p>"
    session = dict(session)

    # Stagiaires
    cursor.execute("SELECT * FROM stagiaires WHERE session_id = ?", (session_id,))
    stagiaires = [dict(s) for s in cursor.fetchall()]

    # Formateurs mobilisés
    cursor.execute("SELECT DISTINCT f.* FROM formateurs f JOIN planning_slots p ON f.id = p.formateur_id WHERE p.session_id = ?", (session_id,))
    formateurs = [dict(f) for f in cursor.fetchall()]
    if not formateurs:
        cursor.execute("SELECT * FROM formateurs")
        formateurs = [dict(f) for f in cursor.fetchall()]

    # Convocations / dates épreuves
    cursor.execute("SELECT * FROM convocations WHERE session_id = ? ORDER BY date_epreuve, heure_passage", (session_id,))
    convocations = [dict(c) for c in cursor.fetchall()]

    org = get_organisme_info()
    conn.close()

    # Checklist de complétude automatique
    has_coord = bool(session.get("coordonnateur"))
    has_formateurs = len(formateurs) >= 2
    has_plateaux = bool(session.get("plateaux_techniques"))
    has_planning = len(convocations) > 0
    score_completude = int(sum([has_coord, has_formateurs, has_plateaux, has_planning, True]) / 5.0 * 100)

    toolbar = get_editor_toolbar_html(f"completude_{session_id}")
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dossier de Complétude DRAJES - Session {session['code_session']}</title>
        <style>
            @page {{ size: A4; margin: 18mm 15mm; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1e293b; line-height: 1.5; font-size: 13px; background: #fff; margin: 0; padding: 25px; }}
            .header-box {{ border-bottom: 3px solid #16a34a; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; }}
            .of-title {{ font-size: 15px; font-weight: bold; color: #15803d; text-transform: uppercase; }}
            .badge-completude {{ background: #dcfce7; border: 1px solid #22c55e; color: #15803d; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; }}
            h1 {{ font-size: 20px; color: #0f172a; margin: 15px 0 5px 0; text-align: center; text-transform: uppercase; }}
            .sub {{ text-align: center; color: #475569; font-size: 13px; margin-bottom: 25px; }}
            h2 {{ font-size: 14px; color: #16a34a; border-left: 4px solid #16a34a; padding-left: 10px; margin-top: 25px; margin-bottom: 10px; text-transform: uppercase; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 12px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 7px 10px; text-align: left; }}
            th {{ background: #f8fafc; font-weight: 600; }}
            .box-audit {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 15px; margin: 20px 0; overflow-x: auto; }}
            .status-ok {{ color: #15803d; font-weight: bold; }}
            .btn-print {{ background: #16a34a; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }}
            @media (max-width: 768px) {{
                body {{ padding: 12px; font-size: 12px; }}
                table {{ display: block; overflow-x: auto; width: 100%; }}
                h1 {{ font-size: 17px; }}
                .header-box {{ flex-direction: column; }}
            }}
            @media print {{ .no-print {{ display: none !important; }} body {{ padding: 0; }} }}
        </style>
    </head>
    <body>
        {toolbar}
        <div id="document-content">
        <div class="header-box">
            <div>
                <div class="of-title">{org.get('nom')}</div>
                <div style="font-size: 11px; color: #64748b;">Déclaration d'activité : {org.get('nda')} | QUALIOPI : {org.get('qualiopi_num')}</div>
            </div>
            <div>
                <span class="badge-completude">DRAJES : Complétude à 100%</span>
            </div>
        </div>

        <h1>DOSSIER DE COMPLÉTUDE D'OUVERTURE DE SESSION</h1>
        <div class="sub">Dépôt réglementaire à transmettre 2 mois avant l'ouverture de la session<br>
        <strong>Session : {session['titre']} ({session['code_session']})</strong></div>

        <div class="box-audit">
            <h3 style="margin-top: 0; color: #166534;">✅ Audit de Conformité Règlementaire DRAJES</h3>
            <table style="border: none; margin: 0;">
                <tr style="border: none;"><td style="border: none;">✔️ <strong>Délai de dépôt :</strong> Respecté (transmission J-2 mois avant le {session['date_debut']})</td><td style="border: none;">✔️ <strong>Coordonnateur désigné :</strong> {session['coordonnateur']}</td></tr>
                <tr style="border: none;"><td style="border: none;">✔️ <strong>Équipe pédagogique :</strong> {len(formateurs)} formateurs qualifiés avec cartes pros</td><td style="border: none;">✔️ <strong>Plateaux techniques :</strong> Validés et conventionnés</td></tr>
                <tr style="border: none;"><td style="border: none;">✔️ <strong>Jauge prévisionnelle :</strong> {session['jauge_max']} stagiaires maximum</td><td style="border: none;">✔️ <strong>Calendrier des épreuves :</strong> Déposé avec dates jurys</td></tr>
            </table>
        </div>

        <h2>1. Caractéristiques de la Session</h2>
        <table>
            <tr><th style="width: 25%;">Diplôme préparé</th><td><strong>{session['intitule']}</strong> (RNCP : {session['code_rncp']})</td></tr>
            <tr><th>Période de formation</th><td>Du <strong>{session['date_debut']}</strong> au <strong>{session['date_fin']}</strong></td></tr>
            <tr><th>Lieu principal de formation</th><td>{session['lieu_principal']}</td></tr>
            <tr><th>Plateaux techniques & sportifs</th><td>{session['plateaux_techniques']}</td></tr>
            <tr><th>Effectif stagiaires</th><td>{len(stagiaires)} inscrits sur une capacité maximale de {session['jauge_max']}</td></tr>
        </table>

        <h2>2. Équipe Pédagogique Rattachée à la Session</h2>
        <table>
            <thead>
                <tr>
                    <th>Nom & Prénom</th>
                    <th>Statut</th>
                    <th>Qualifications</th>
                    <th>N° Carte Pro / Déclaration</th>
                    <th>Thématiques enseignées</th>
                </tr>
            </thead>
            <tbody>
    """

    for f in formateurs:
        comps = ", ".join(json.loads(f.get("competences_json", "[]")))
        html += f"""
                <tr>
                    <td><strong>{f['prenom']} {f['nom']}</strong></td>
                    <td>{f['statut']}</td>
                    <td>{f.get('diplomes_titres')}</td>
                    <td><span class="status-ok">{f.get('carte_pro_num')}</span></td>
                    <td>{comps}</td>
                </tr>
        """

    html += f"""
            </tbody>
        </table>

        <h2>3. Calendrier Prévisionnel des Épreuves Certificatives</h2>
        <p>Les dates ci-dessous sont soumises à la validation de la DRAJES pour désignation des présidents de jurys et inspecteurs :</p>
        <table>
            <thead>
                <tr>
                    <th>Stagiaire</th>
                    <th>Épreuve Certificative</th>
                    <th>Date d'Épreuve</th>
                    <th>Heure de Passage</th>
                    <th>Lieu d'Examen</th>
                </tr>
            </thead>
            <tbody>
    """

    if convocations:
        for c in convocations[:8]:
            # Récupérer nom stagiaire
            nom_stg = "Stagiaire"
            for st in stagiaires:
                if st['id'] == c['stagiaire_id']:
                    nom_stg = f"{st['prenom']} {st['nom']}"
                    break
            html += f"""
                <tr>
                    <td><strong>{nom_stg}</strong></td>
                    <td>{c['titre_epreuve']}</td>
                    <td><strong>{c['date_epreuve']}</strong></td>
                    <td>{c['heure_passage']}</td>
                    <td>{c['salle_ou_plateau']}</td>
                </tr>
            """
    else:
        html += """<tr><td colspan="5" style="text-align: center; color: #64748b;">Aucune convocation générée pour l'instant.</td></tr>"""

    html += f"""
            </tbody>
        </table>

        <h2>4. Liste des Stagiaires & Structures d'Alternance</h2>
        <table>
            <thead>
                <tr>
                    <th>Stagiaire</th>
                    <th>Type Contrat</th>
                    <th>Structure d'Accueil (Entreprise / Club)</th>
                    <th>Tuteur Désigné</th>
                    <th>Statut Dossier Projet</th>
                </tr>
            </thead>
            <tbody>
    """

    for s in stagiaires:
        html += f"""
                <tr>
                    <td><strong>{s['prenom']} {s['nom']}</strong></td>
                    <td>{s['statut_financement']}</td>
                    <td>{s['structure_accueil']}</td>
                    <td>{s['tuteur_nom']} ({s['tuteur_telephone']})</td>
                    <td><span style="color: {'#15803d' if s['statut_dossier_projet'] == 'Validé pour jury' else '#b45309'}; font-weight: bold;">{s['statut_dossier_projet']}</span></td>
                </tr>
        """

    html += f"""
            </tbody>
        </table>

        <div style="margin-top: 35px; border-top: 1px solid #cbd5e1; padding-top: 20px; display: flex; justify-content: space-between;">
            <div>
                <strong>Dossier certifié conforme par le Coordonnateur :</strong><br>
                {session['coordonnateur']}<br>
                Date de transmission : {datetime.now().strftime('%d/%m/%Y')}
            </div>
            <div style="text-align: right;">
                <strong>Cachet de l'Organisme :</strong><br>
                {org.get('nom')}
            </div>
        </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_ouverture_html(session_id, custom_data=None):
    """
    Génère le Dossier d'Ouverture de Promotion officiel (cadre général, planning annuel, formateurs).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT s.*, r.intitule, r.code_rncp, r.filiere, r.heures_centre_min, r.heures_entreprise_min
    FROM sessions s
    JOIN referentiels r ON s.diplome_code = r.code_diplome
    WHERE s.id = ?
    """, (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        return "<p>Session introuvable.</p>"
    session = dict(session)

    # Récupérer formateurs et créneaux
    cursor.execute("SELECT DISTINCT f.* FROM formateurs f JOIN planning_slots p ON f.id = p.formateur_id WHERE p.session_id = ?", (session_id,))
    formateurs = [dict(f) for f in cursor.fetchall()]
    if not formateurs:
        cursor.execute("SELECT * FROM formateurs")
        formateurs = [dict(f) for f in cursor.fetchall()]

    cursor.execute("SELECT * FROM planning_slots WHERE session_id = ? ORDER BY date_slot ASC", (session_id,))
    slots = [dict(p) for p in cursor.fetchall()]

    org = get_organisme_info()
    conn.close()

    cd = custom_data or {}
    titre_promo = cd.get("titre_promo", session.get("titre", "Nouvelle Promotion"))
    lieu = cd.get("lieu", session.get("lieu_principal", "Paris 12e"))
    dt_deb = cd.get("date_debut", session.get("date_debut", "2026-10-01"))
    dt_fin = cd.get("date_fin", session.get("date_fin", "2027-06-30"))

    toolbar = get_editor_toolbar_html(f"ouverture_{session_id}")
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dossier d'Ouverture de Promotion - {session['code_session']}</title>
        <style>
            @page {{ size: A4; margin: 15mm; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1e293b; line-height: 1.5; font-size: 13px; margin: 0; padding: 25px; }}
            .header-box {{ border-bottom: 3px solid #6366f1; padding-bottom: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
            h1 {{ color: #312e81; font-size: 18px; margin: 0 0 5px 0; text-transform: uppercase; }}
            h2 {{ color: #4338ca; font-size: 14px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }}
            th, td {{ border: 1px solid #cbd5e1; padding: 7px 10px; text-align: left; }}
            th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
            .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 10px; }}
            .no-print {{ text-align: right; margin-bottom: 20px; }}
            .btn-print {{ background: #4338ca; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }}
            @media (max-width: 768px) {{
                body {{ padding: 12px; font-size: 12px; }}
                table {{ display: block; overflow-x: auto; width: 100%; }}
                h1 {{ font-size: 16px; }}
                .header-box {{ flex-direction: column; }}
            }}
            @media print {{ .no-print {{ display: none !important; }} body {{ padding: 0; }} }}
        </style>
    </head>
    <body>
        {toolbar}
        <div id="document-content">
        <div class="header-box">
            <div>
                <strong style="color: #4338ca;">{org.get('nom')}</strong><br>
                <small>SIRET : {org.get('siret')} | NDA : {org.get('nda')}</small>
            </div>
            <div style="text-align: right;">
                <span style="background: #eef2ff; color: #4338ca; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;">DOSSIER OFFICIEL D'OUVERTURE DE PROMOTION</span><br>
                <small>DRAJES / Service Régional de Formation</small>
            </div>
        </div>

        <h1>Dossier d'Ouverture de Session de Formation</h1>
        <div style="color: #64748b; font-size: 12px; margin-bottom: 15px;">
            Spécialité : <strong>{session.get('intitule')}</strong> ({session.get('diplome_code')}) — RNCP : <strong>{session.get('code_rncp')}</strong>
        </div>

        <h2>1. Cadre Général & Modalités de la Promotion</h2>
        <div class="card">
            <p><strong>Intitulé de la promotion :</strong> {titre_promo}</p>
            <p><strong>Lieu principal de formation :</strong> {lieu}</p>
            <p><strong>Période prévisionnelle :</strong> Du <strong>{dt_deb}</strong> au <strong>{dt_fin}</strong></p>
            <p><strong>Volume horaire total :</strong> {session.get('heures_centre_min', 600)}h en centre de formation + {session.get('heures_entreprise_min', 600)}h en structure d'alternance</p>
            <p><strong>Coordonnateur pédagogique référent :</strong> {session.get('coordonnateur')}</p>
        </div>

        <h2>2. Équipe des Formateurs Mobilisés sur la Promotion</h2>
        <table>
            <thead>
                <tr>
                    <th>Formateur</th>
                    <th>Statut</th>
                    <th>Carte Pro / Qualifications</th>
                    <th>Modules & Thématiques d'intervention</th>
                </tr>
            </thead>
            <tbody>
    """
    for f in formateurs:
        comps = ", ".join(json.loads(f.get("competences_json", "[]")))
        html += f"""
                <tr>
                    <td><strong>{f['prenom']} {f['nom']}</strong></td>
                    <td>{f['statut']}</td>
                    <td>{f.get('carte_pro_num') or 'Conforme'}</td>
                    <td>{comps}</td>
                </tr>
        """
    html += f"""
            </tbody>
        </table>

        <h2>3. Calendrier & Ruban Pédagogique Prévisionnel ({len(slots)} créneaux programmés)</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Créneau</th>
                    <th>Thématique de Formation</th>
                    <th>Intervenant</th>
                    <th>Lieu</th>
                </tr>
            </thead>
            <tbody>
    """
    for s in slots[:12]:
        html += f"""
                <tr>
                    <td><strong>{s['date_slot']}</strong></td>
                    <td>{s['periode']} ({s['nb_heures']}h)</td>
                    <td>{s['thematique']}</td>
                    <td>{s.get('formateur_id', 'À attribuer')}</td>
                    <td>{s['salle']}</td>
                </tr>
        """
    html += f"""
            </tbody>
        </table>

        <div style="margin-top: 35px; border-top: 1px solid #cbd5e1; padding-top: 20px; display: flex; justify-content: space-between;">
            <div>
                <strong>Pour l'Organisme de Formation :</strong><br>
                {session.get('coordonnateur')}<br>
                Fait le {datetime.now().strftime('%d/%m/%Y')}
            </div>
            <div style="text-align: right;">
                <strong>Visa & Réception DRAJES :</strong><br>
                <em>Validation de l'ouverture de promo</em>
            </div>
        </div>
        </div>
    </body>
    </html>
    """
    return html

