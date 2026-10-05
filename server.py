"""
Serveur Web Autonome & API REST CoordoPro JEPS
100% Python Standard Library (zéro dépendance externe, zéro clé API, 100% gratuit et local).
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import mimetypes

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from database import init_db, seed_data, get_db
import engine_dossiers
import engine_planning
import engine_stagiaires
import engine_finance
import jarvis_engine

PORT = int(os.environ.get("PORT", 8088))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

class CoordoProHandler(http.server.SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API Endpoints
        if path == "/api/stats":
            self.send_json(self.get_dashboard_stats())
            return
        elif path == "/api/referentiels":
            self.send_json(self.get_referentiels())
            return
        elif path == "/api/sessions":
            self.send_json(self.get_sessions())
            return
        elif path == "/api/formateurs":
            self.send_json(self.get_formateurs())
            return
        elif path == "/api/planning":
            session_id = query.get("session_id", [None])[0]
            self.send_json(self.get_planning(session_id))
            return
        elif path == "/api/solicitation-email":
            slot_id = query.get("slot_id", [None])[0]
            if slot_id:
                data = engine_planning.generate_solicitation_email(int(slot_id))
                self.send_json(data or {"error": "Slot introuvable"})
            else:
                self.send_json({"error": "Paramètre slot_id manquant"})
            return
        elif path == "/api/stagiaires":
            session_id = query.get("session_id", [1])[0]
            self.send_json(self.get_stagiaires(session_id))
            return
        elif path == "/api/deadlines":
            session_id = query.get("session_id", [1])[0]
            self.send_json(engine_stagiaires.get_stagiaires_deadlines(int(session_id)))
            return
        elif path == "/api/convocations":
            session_id = query.get("session_id", [1])[0]
            self.send_json(self.get_convocations(session_id))
            return
        elif path == "/api/candidatures":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM candidatures ORDER BY id DESC")
            cands = [dict(r) for r in cur.fetchall()]
            conn.close()
            self.send_json(cands)
            return
        elif path == "/api/jarvis/audit":
            session_id = int(query.get("session_id", [1])[0])
            report = jarvis_engine.run_zero_defect_audit(session_id)
            self.send_json(report)
            return
        elif path == "/api/jarvis/logs":
            limit = int(query.get("limit", [15])[0])
            logs = jarvis_engine.get_recent_audit_logs(limit)
            self.send_json(logs)
            return
        elif path == "/api/jarvis/rules":
            rules = jarvis_engine.get_learned_rules()
            self.send_json(rules)
            return
        elif path == "/api/finance":
            session_id = query.get("session_id", [None])[0]
            sid = int(session_id) if session_id else None
            self.send_json(engine_finance.get_finance_matrix(sid))
            return
        elif path == "/api/finance/export-csv":
            session_id = query.get("session_id", [None])[0]
            sid = int(session_id) if session_id else None
            csv_data = engine_finance.export_finance_csv(sid)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=suivi_factures_formateurs.csv")
            self.end_headers()
            self.wfile.write(csv_data.encode("utf-8-sig"))
            return

        # 2. Documents imprimables & exportables (HTML / PDF)
        elif path == "/api/dossier/habilitation":
            diplome = query.get("diplome_code", ["BPJEPS_APT"])[0]
            html = engine_dossiers.generate_habilitation_html(diplome)
            self.send_html(html)
            return
        elif path == "/api/dossier/completude":
            session_id = int(query.get("session_id", [1])[0])
            html = engine_dossiers.generate_completude_html(session_id)
            self.send_html(html)
            return
        elif path == "/api/dossier/ouverture":
            session_id = int(query.get("session_id", [1])[0])
            html = engine_dossiers.generate_ouverture_html(session_id)
            self.send_html(html)
            return
        elif path == "/api/convocations/print":
            session_id = int(query.get("session_id", [1])[0])
            stagiaire_id = query.get("stagiaire_id", [None])[0]
            stg_id = int(stagiaire_id) if stagiaire_id else None
            html = engine_stagiaires.generate_convocations_html(session_id, stg_id)
            self.send_html(html)
            return
        elif path == "/api/planning/print-monthly":
            session_id = int(query.get("session_id", [1])[0])
            month = query.get("month", ["2026-10"])[0]
            html = engine_stagiaires.generate_monthly_planning_html(session_id, month)
            self.send_html(html)
            return

        # 3. Fichiers Statiques
        if path == "/" or path == "":
            path = "/index.html"

        file_path = os.path.join(STATIC_DIR, path.lstrip("/"))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "text/plain; charset=utf-8")
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        if path == "/api/planning/auto-assign":
            session_id = int(payload.get("session_id", 1))
            week_slots = payload.get("week_slots", [])
            results = engine_planning.auto_assign_week_planning(session_id, week_slots)
            self.send_json({"success": True, "results": results})
            return
        elif path == "/api/planning/swap":
            slot1_id = int(payload.get("slot1_id"))
            slot2_id = int(payload.get("slot2_id"))
            res = engine_planning.execute_swap_slots(slot1_id, slot2_id)
            self.send_json(res)
            return
        elif path == "/api/solicitation-response":
            slot_id = int(payload.get("slot_id"))
            reponse = payload.get("reponse", "accepte")
            res = engine_planning.process_trainer_response(slot_id, reponse)
            self.send_json(res)
            return
        elif path == "/api/planning/add":
            ses_id = int(payload.get("session_id", 1))
            dt = payload.get("date_slot")
            theme = payload.get("thematique")
            f_id = int(payload["formateur_id"]) if payload.get("formateur_id") else None
            per = payload.get("periode", "Journée")
            h = float(payload.get("nb_heures", 7.0))
            salle = payload.get("salle", "Salle Principale A1")
            comm = payload.get("commentaire", "")
            res = engine_planning.add_planning_slot(ses_id, dt, theme, f_id, per, h, salle, comm)
            self.send_json(res)
            return
        elif path == "/api/planning/update":
            s_id = int(payload.get("slot_id"))
            dt = payload.get("date_slot")
            theme = payload.get("thematique")
            f_id = int(payload["formateur_id"]) if payload.get("formateur_id") else None
            per = payload.get("periode", "Journée")
            h = float(payload.get("nb_heures", 7.0))
            salle = payload.get("salle", "Salle Principale A1")
            st = payload.get("statut_slot", "Confirmé")
            comm = payload.get("commentaire", "")
            res = engine_planning.update_planning_slot(s_id, dt, theme, f_id, per, h, salle, st, comm)
            self.send_json(res)
            return
        elif path == "/api/planning/delete":
            s_id = int(payload.get("slot_id"))
            res = engine_planning.delete_planning_slot(s_id)
            self.send_json(res)
            return
        elif path == "/api/planning/complete":
            s_id = int(payload.get("slot_id"))
            res = engine_planning.mark_slot_completed(s_id)
            self.send_json(res)
            return
        elif path == "/api/import-persen":
            csv_text = payload.get("csv_content", "")
            ses_id = int(payload.get("session_id", 1))
            res = engine_planning.import_persen_csv(csv_text, ses_id)
            self.send_json(res)
            return
        elif path == "/api/candidature/add":
            nom = payload.get("nom", "").strip()
            prenom = payload.get("prenom", "").strip()
            email = payload.get("email", "").strip()
            tel = payload.get("telephone", "").strip()
            dip = payload.get("diplome_vise", "BPJEPS_APT")
            cv_nom = payload.get("cv_nom", "CV_candidat.pdf")
            cv_txt = payload.get("cv_texte", "")
            mot_txt = payload.get("motivation_texte", "")
            
            # Analyse calibrée locale (sans LLM) : détection de mots-clés pédagogiques, longueur, orthographe
            score = 60
            obs = []
            txt_comb = (cv_txt + " " + mot_txt).lower()
            if any(k in txt_comb for k in ["bafa", "bpjeps", "cpjeps", "psc1", "animateur", "club", "association", "sport", "jeunesse"]):
                score += 20
                obs.append("Expérience ou prérequis animation/sport détectés.")
            if len(mot_txt.split()) > 40:
                score += 10
                obs.append("Lettre développée et argumentée.")
            if any(k in txt_comb for k in ["transmettre", "projet", "pedagogie", "progression", "objectifs", "valeurs"]):
                score += 10
                obs.append("Vocabulaire pédagogique pertinent.")
            score = min(score, 98)
            analyse = " | ".join(obs) if obs else "Profil standard à approfondir en entretien."
            
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO candidatures (nom, prenom, email, telephone, diplome_vise, cv_nom, cv_texte, motivation_texte, score_ecrit, analyse_ia, statut, date_depot, pieces_manquantes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Nouveau', ?, 'Attestation TEP, Pièce d identité')
            """, (nom, prenom, email, tel, dip, cv_nom, cv_txt, mot_txt, score, analyse, datetime.now().strftime("%Y-%m-%d")))
            new_id = cur.lastrowid
            conn.commit()
            conn.close()
            self.send_json({"success": True, "id": new_id, "score": score, "analyse": analyse})
            return
        elif path == "/api/candidature/relancer":
            cid = int(payload.get("candidature_id", 0))
            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE candidatures SET statut = 'Relancé' WHERE id = ?", (cid,))
            conn.commit()
            conn.close()
            jarvis_engine.log_event("Jarvis RPA", "Candidature", "Modification", f"Candidat #{cid} relancé pour pièces manquantes")
            self.send_json({"success": True, "message": f"Notification envoyée au candidat #{cid} pour dépôt des pièces manquantes."})
            return
        elif path == "/api/jarvis/learn":
            pattern = payload.get("pattern", "").strip()
            action_type = payload.get("action_type", "").strip()
            desc = payload.get("description", "Appris via interface")
            res = jarvis_engine.add_learned_rule(pattern, action_type, desc)
            self.send_json(res)
            return
        elif path == "/api/finance/update":
            fac_id = int(payload.get("facture_id"))
            statut = payload.get("statut_paiement")
            num = payload.get("numero_facture")
            dt_rec = payload.get("date_reception_facture")
            dt_trans = payload.get("date_transmission_compta")
            dt_pay = payload.get("date_paiement")
            res = engine_finance.update_facture_status(fac_id, statut, num, dt_rec, dt_trans, dt_pay)
        elif path == "/api/jarvis/dispatch":
            tool_name = payload.get("tool_name", "")
            tool_payload = payload.get("payload", {})
            res = jarvis_engine.JarvisToolRegistry.dispatch(tool_name, tool_payload)
            self.send_json(res)
            return
        elif path == "/api/jarvis/query":
            q_type = payload.get("query_type", "modifications_aujourdhui")
            s_id = payload.get("session_id")
            res = jarvis_engine.query_audit_memory(q_type, int(s_id) if s_id else None)
            self.send_json(res)
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 API Endpoint Not Found")

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_html(self, html_content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    # Helpers Base de Données
    def get_dashboard_stats(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions")
        nb_sessions = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM stagiaires")
        nb_stagiaires = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM formateurs")
        nb_formateurs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM planning_slots WHERE statut_slot = 'Planifié'")
        nb_slots_a_confirmer = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM factures_formateurs WHERE statut_paiement = 'En attente facture'")
        nb_factures_en_attente = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM stagiaires WHERE statut_dossier_projet != 'Validé pour jury'")
        nb_dossiers_a_suivre = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM organisme LIMIT 1")
        org = dict(cursor.fetchone())
        conn.close()

        fin = engine_finance.get_finance_matrix()
        return {
            "nb_sessions": nb_sessions,
            "nb_stagiaires": nb_stagiaires,
            "nb_formateurs": nb_formateurs,
            "nb_slots_a_confirmer": nb_slots_a_confirmer,
            "nb_factures_en_attente": nb_factures_en_attente,
            "nb_dossiers_a_suivre": nb_dossiers_a_suivre,
            "budget": fin["kpis"],
            "organisme": org
        }

    def get_referentiels(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, code_diplome, intitule, filiere, code_rncp, niveau_qualif, heures_centre_min, heures_entreprise_min FROM referentiels")
        data = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return data

    def get_sessions(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT s.*, r.intitule as diplome_titre, r.code_rncp,
               (SELECT COUNT(*) FROM stagiaires WHERE session_id = s.id) as nb_inscrits
        FROM sessions s
        JOIN referentiels r ON s.diplome_code = r.code_diplome
        ORDER BY s.id
        """)
        data = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return data

    def get_formateurs(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM formateurs ORDER BY nom")
        rows = []
        for r in cursor.fetchall():
            d = dict(r)
            d["competences"] = json.loads(d.get("competences_json", "[]"))
            d["disponibilites"] = json.loads(d.get("disponibilites_json", "{}"))
            rows.append(d)
        conn.close()
        return rows

    def get_planning(self, session_id=None):
        conn = get_db()
        cursor = conn.cursor()
        query = """
        SELECT p.*, f.nom as formateur_nom, f.prenom as formateur_prenom, f.taux_journalier, s.titre as session_titre
        FROM planning_slots p
        LEFT JOIN formateurs f ON p.formateur_id = f.id
        JOIN sessions s ON p.session_id = s.id
        """
        params = []
        if session_id:
            query += " WHERE p.session_id = ?"
            params.append(session_id)
        query += " ORDER BY p.date_slot, p.periode"
        cursor.execute(query, tuple(params))
        data = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return data

    def get_stagiaires(self, session_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stagiaires WHERE session_id = ? ORDER BY nom", (session_id,))
        data = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return data

    def get_convocations(self, session_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT c.*, s.nom as stg_nom, s.prenom as stg_prenom, s.email as stg_email, s.telephone as stg_tel
        FROM convocations c
        JOIN stagiaires s ON c.stagiaire_id = s.id
        WHERE c.session_id = ?
        ORDER BY c.date_epreuve, c.heure_passage
        """, (session_id,))
        data = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return data

def run_server():
    init_db()
    seed_data()
    httpd = http.server.ThreadingHTTPServer(("", PORT), CoordoProHandler)
    print("================================================================")
    print(f"[OK] CoordoPro JEPS - Serveur Multithread Demarre avec Succes !")
    print(f"Interface Web : http://localhost:{PORT}")
    print(f"Dossier Statique : {STATIC_DIR}")
    print("================================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
