"""
Module Database & Modèles CoordoPro JEPS
Base SQLite autonome avec schémas relationnels et données de référence RNCP / JEPS / DRAJES.
"""

import sqlite3
import os
import json
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "coordopro.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Table Organisme de Formation
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS organisme (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        siret TEXT,
        nda TEXT,
        qualiopi_num TEXT,
        qualiopi_date TEXT,
        adresse TEXT,
        ville TEXT,
        code_postal TEXT,
        telephone TEXT,
        email TEXT,
        responsable_legal TEXT,
        coordonnateur_principal TEXT
    )
    """)

    # 2. Table Référentiels Diplômes (RNCP / JEPS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS referentiels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code_diplome TEXT UNIQUE NOT NULL, -- ex: BPJEPS_APT
        intitule TEXT NOT NULL,
        filiere TEXT DEFAULT 'JEPS',
        code_rncp TEXT,
        niveau_qualif TEXT,
        arrete_creation TEXT,
        heures_centre_min INTEGER,
        heures_entreprise_min INTEGER,
        description TEXT,
        blocs_competences_json TEXT, -- [{uc: 'UC1', titre: '...', objectif: '...', eval: '...'}]
        modalites_certification_json TEXT
    )
    """)

    # 3. Table Sessions de formation
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code_session TEXT UNIQUE NOT NULL, -- ex: BP-APT-2026-01
        diplome_code TEXT NOT NULL,
        titre TEXT NOT NULL,
        coordonnateur TEXT,
        date_debut TEXT,
        date_fin TEXT,
        date_limite_completude TEXT, -- DRAJES 2 mois avant début
        date_depot_dossier_projet TEXT, -- Date limite stagiaires
        lieu_principal TEXT,
        plateaux_techniques TEXT,
        jauge_max INTEGER DEFAULT 16,
        statut_drajes TEXT DEFAULT 'En préparation', -- 'En préparation', 'Complétude déposée', 'Validée DRAJES', 'En cours', 'Clôturée'
        budget_prev_formateurs REAL DEFAULT 25000.0,
        FOREIGN KEY (diplome_code) REFERENCES referentiels(code_diplome)
    )
    """)

    # 4. Table Formateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS formateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        email TEXT NOT NULL,
        telephone TEXT,
        statut TEXT DEFAULT 'Indépendant', -- 'Salarié', 'Indépendant / Sous-traitant', 'Vacataire'
        siret TEXT,
        taux_journalier REAL DEFAULT 420.0,
        taux_horaire REAL DEFAULT 60.0,
        competences_json TEXT, -- ['Méthodologie de projet', 'Diagnostic', 'Budget', 'IA', 'Com', 'Évaluation']
        disponibilites_json TEXT, -- {'lundi': true, 'mardi': true, ...}
        carte_pro_num TEXT,
        diplomes_titres TEXT
    )
    """)

    # 5. Table Stagiaires
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stagiaires (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        date_naissance TEXT,
        email TEXT NOT NULL,
        telephone TEXT,
        statut_financement TEXT, -- 'Apprentissage', 'Contrat Pro', 'CPF / Auto-financé', 'Transition Pro'
        structure_accueil TEXT,
        tuteur_nom TEXT,
        tuteur_email TEXT,
        tuteur_telephone TEXT,
        statut_dossier_projet TEXT DEFAULT 'En rédaction', -- 'Non commencé', 'En rédaction', 'Déposé', 'Validé pour jury', 'Retard'
        date_depot_effectif TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )
    """)

    # 6. Table Planning & Interventions Formateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        date_slot TEXT NOT NULL, -- YYYY-MM-DD
        periode TEXT DEFAULT 'Journée', -- 'Journée', 'Matin (9h-12h30)', 'Après-midi (13h30-17h)'
        nb_heures REAL DEFAULT 7.0,
        thematique TEXT NOT NULL, -- ex: 'IA', 'Diagnostic', 'Budget', 'Com', 'Évaluation', 'Méthodologie de projet'
        formateur_id INTEGER,
        statut_slot TEXT DEFAULT 'Planifié', -- 'À attribuer', 'Proposé', 'Confirmé', 'Effectué', 'Annulé / Remplacé'
        salle TEXT DEFAULT 'Salle Principale A1',
        commentaire TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (formateur_id) REFERENCES formateurs(id)
    )
    """)

    # 7. Table Convocations Certifications Stagiaires
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS convocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stagiaire_id INTEGER NOT NULL,
        session_id INTEGER NOT NULL,
        titre_epreuve TEXT NOT NULL, -- ex: 'Certification UC1/UC2 - Soutenance Projet', 'Certification UC3/UC4 - Séance pédagogique'
        date_epreuve TEXT NOT NULL,
        heure_passage TEXT NOT NULL,
        salle_ou_plateau TEXT NOT NULL,
        composition_jury TEXT,
        statut_envoi TEXT DEFAULT 'Prête', -- 'Prête', 'Envoyée', 'Accusé reçu'
        statut_presence TEXT DEFAULT 'Convoqué', -- 'Convoqué', 'Présent', 'Absent justifié', 'Validé', 'Non validé'
        FOREIGN KEY (stagiaire_id) REFERENCES stagiaires(id),
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )
    """)

    # 8. Table Facturation & Paiement Formateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factures_formateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        formateur_id INTEGER NOT NULL,
        session_id INTEGER NOT NULL,
        planning_slot_id INTEGER,
        date_intervention TEXT NOT NULL,
        thematique TEXT NOT NULL,
        nb_heures REAL DEFAULT 7.0,
        montant_ht REAL NOT NULL,
        statut_intervention TEXT DEFAULT 'Effectué', -- 'Planifié', 'Effectué', 'Reporté'
        numero_facture TEXT,
        date_reception_facture TEXT,
        date_transmission_compta TEXT,
        statut_paiement TEXT DEFAULT 'En attente facture', -- 'En attente facture', 'Facture reçue', 'Transmis en paiement', 'Payé'
        date_paiement TEXT,
        mode_reglement TEXT DEFAULT 'Virement bancaire',
        commentaire TEXT,
        FOREIGN KEY (formateur_id) REFERENCES formateurs(id),
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (planning_slot_id) REFERENCES planning_slots(id)
    )
    """)

    # 9. Table Historique des Emails & Sollicitations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destinataire_type TEXT, -- 'Formateur', 'Stagiaire', 'Tuteur', 'DRAJES'
        destinataire_nom TEXT,
        destinataire_email TEXT,
        type_email TEXT, -- 'Sollicitation Formateur', 'Convocation Stagiaire', 'Planning Mensuel', 'Relance Dossier Projet', 'Complétude DRAJES'
        objet TEXT NOT NULL,
        corps_message TEXT NOT NULL,
        statut TEXT DEFAULT 'Envoyé', -- 'Brouillon', 'Envoyé', 'Répondu'
        date_creation TEXT,
        reponse_recue TEXT
    )
    """)

    conn.commit()
    conn.close()

def seed_data():
    """Injecte des données de référence réalistes pour l'OF et les diplômes JEPS."""
    conn = get_db()
    cursor = conn.cursor()

    # Vérifier si déjà injecté
    cursor.execute("SELECT COUNT(*) FROM organisme")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # 1. Organisme
    cursor.execute("""
    INSERT INTO organisme (nom, siret, nda, qualiopi_num, qualiopi_date, adresse, ville, code_postal, telephone, email, responsable_legal, coordonnateur_principal)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "ACADÉMIE FORMATRICE JEPS & SPORT (AFJS)",
        "849 321 456 00028",
        "11 75 58941 75 (Région Île-de-France)",
        "QUALIOPI-CERT-2024-0891",
        "15/01/2024 (Valide jusqu'au 14/01/2027)",
        "148 Avenue des Sports et de l'Animation",
        "Paris",
        "75012",
        "01 43 55 88 90",
        "contact@afjs-formation.fr",
        "Alexandre D. (Président Directeur Général)",
        "Coordonnateur Principal JEPS (Direction Pédagogique)"
    ))

    # 2. Référentiels JEPS
    referentiels = [
        (
            "BPJEPS_APT",
            "BPJEPS Spécialité Éducateur Sportif - Mention Activités Physiques pour Tous",
            "JEPS",
            "RNCP37104",
            "Niveau 4 (Bac)",
            "Arrêté du 21 juin 2016 modifié",
            600,
            600,
            "Diplôme d'État permettant d'encadrer en autonomie tous publics dans 3 grands domaines : activités physiques en pleine nature, activités d'entretien corporel, et jeux sportifs/jeux collectifs.",
            json.dumps([
                {
                    "uc": "UC1",
                    "titre": "Encadrer tout public dans tout lieu et toute structure",
                    "heures": 150,
                    "competences": "Communiquer dans les situations de la vie professionnelle, prendre en compte les caractéristiques des publics, contribuer au fonctionnement de la structure.",
                    "modalite_eval": "Dossier de présentation de projet d'animation (20 pages max) + Soutenance orale (15 min) + Entretien avec le jury DRAJES (25 min)."
                },
                {
                    "uc": "UC2",
                    "titre": "Mettre en œuvre un projet d'animation s'inscrivant dans le projet de la structure",
                    "heures": 150,
                    "competences": "Concevoir un projet d'animation, conduire le projet d'animation sur le terrain, évaluer le projet et son impact budgétaire/social.",
                    "modalite_eval": "Conjointe avec l'UC1 lors de la même épreuve certificative DRAJES."
                },
                {
                    "uc": "UC3",
                    "titre": "Concevoir la séance, le cycle d'animation ou d'apprentissage dans le champ des APT",
                    "heures": 150,
                    "competences": "Concevoir des cycles en activités de pleine nature, entretien corporel et jeux collectifs, sécuriser les pratiquants.",
                    "modalite_eval": "Fiche de séance détaillée + Conduite d'une séance pratique d'animation (60 min) avec public réel devant la commission d'évaluation + Entretien (30 min)."
                },
                {
                    "uc": "UC4",
                    "titre": "Mobiliser les techniques de la mention des APT pour mettre en œuvre une séance",
                    "heures": 150,
                    "competences": "Maîtriser les gestes techniques, adapter son guidage pédagogique, évaluer les progrès des pratiquants et gérer les situations d'urgence.",
                    "modalite_eval": "Conjointe avec l'UC3 sur le terrain sportif."
                }
            ], ensure_ascii=False),
            json.dumps({
                "prerequis": "Être titulaire du PSC1, satisfaire aux TEP (Tests d'Exigences Préalables DRAJES : Luc Léger + Parcours d'habileté motrice).",
                "epreuves_ep": "Épreuve 1 (UC1/UC2) : Projet d'animation. Épreuve 2 (UC3/UC4) : Mise en situation professionnelle pédagogique.",
                "composition_jury": "Deux évaluateurs habilités : 1 représentant DRAJES / agent de l'État + 1 professionnel qualifié du secteur sportif."
            }, ensure_ascii=False)
        ),
        (
            "CPJEPS_AAVQ",
            "CPJEPS Mention Animateur d'Activités et de Vie Quotidienne",
            "JEPS",
            "RNCP32359",
            "Niveau 3 (CAP/BEP)",
            "Arrêté du 26 février 2019",
            400,
            400,
            "Premier niveau de qualification professionnelle dans l'animation pour encadrer des enfants, adolescents ou adultes au sein d'accueils collectifs de mineurs et centres sociaux.",
            json.dumps([
                {"uc": "UC1", "titre": "Participer au projet et à la vie de la structure", "heures": 100, "modalite_eval": "Bilan de stage oral"},
                {"uc": "UC2", "titre": "Animer les temps de vie quotidienne de groupes", "heures": 100, "modalite_eval": "Observation sur site"},
                {"uc": "UC3", "titre": "Concevoir des activités en direction d'un groupe", "heures": 100, "modalite_eval": "Fiche d'activité"},
                {"uc": "UC4", "titre": "Animer des activités en direction d'un groupe", "heures": 100, "modalite_eval": "Mise en situation pratique"}
            ], ensure_ascii=False),
            json.dumps({"prerequis": "PSC1, 16 ans révolus.", "composition_jury": "Jury paritaire DRAJES."}, ensure_ascii=False)
        ),
        (
            "DEJEPS_DPTR",
            "DEJEPS Développement de Projets, Territoires et Réseaux",
            "JEPS",
            "RNCP4900",
            "Niveau 5 (Bac+2)",
            "Arrêté du 20 novembre 2006",
            700,
            700,
            "Forme des coordonnateurs de projets socio-éducatifs, directeurs d'équipements de quartier, responsables de pôles jeunesses et tiers-lieux.",
            json.dumps([
                {"uc": "UC1", "titre": "Concevoir un projet d'action", "heures": 175, "modalite_eval": "Mémoire de projet (40 pages) + soutenance"},
                {"uc": "UC2", "titre": "Coordonner la mise en œuvre d'un projet d'action", "heures": 175, "modalite_eval": "Entretien professionnel"},
                {"uc": "UC3", "titre": "Conduire des démarches pédagogiques innovantes", "heures": 175, "modalite_eval": "Étude de cas"},
                {"uc": "UC4", "titre": "Animer des réseaux territoriaux et partenariaux", "heures": 175, "modalite_eval": "Rapport partenarial"}
            ], ensure_ascii=False),
            json.dumps({"prerequis": "Bac ou expérience 2 ans dans l'animation socio-culturelle.", "composition_jury": "Jury plénier DRAJES."}, ensure_ascii=False)
        )
    ]

    cursor.executemany("""
    INSERT INTO referentiels (code_diplome, intitule, filiere, code_rncp, niveau_qualif, arrete_creation, heures_centre_min, heures_entreprise_min, description, blocs_competences_json, modalites_certification_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, referentiels)

    # 3. Sessions
    cursor.execute("""
    INSERT INTO sessions (code_session, diplome_code, titre, coordonnateur, date_debut, date_fin, date_limite_completude, date_depot_dossier_projet, lieu_principal, plateaux_techniques, jauge_max, statut_drajes, budget_prev_formateurs)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "BP-APT-2026-01",
        "BPJEPS_APT",
        "BPJEPS APT Promo 2026/2027 (Alternance & Apprentissage)",
        "Directeur Pédagogique",
        "2026-09-01",
        "2027-06-30",
        "2026-07-01",
        "2026-11-15", # Date limite dépôt dossier projet
        "Campus Sport & Santé, 148 Av des Sports, Paris 12e",
        "Gymnase Municipal Pierre de Coubertin, Piste d'athlétisme Suzanne Lenglen, Parc de Vincennes (Pleine nature)",
        14,
        "Validée DRAJES",
        28500.0
    ))

    cursor.execute("""
    INSERT INTO sessions (code_session, diplome_code, titre, coordonnateur, date_debut, date_fin, date_limite_completude, date_depot_dossier_projet, lieu_principal, plateaux_techniques, jauge_max, statut_drajes, budget_prev_formateurs)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "CPJEPS-2026-B",
        "CPJEPS_AAVQ",
        "CPJEPS AAVQ Session Automne-Hiver 2026",
        "Directeur Pédagogique",
        "2026-12-01",
        "2027-07-15",
        "2026-10-01", # J-2 mois : Urgence DRAJES !
        "2027-03-20",
        "Centre Socio-Culturel Nelson Mandela, Montreuil",
        "Espaces polyvalents et plaine de jeux Montreuil",
        12,
        "En préparation (Complétude requise)",
        16800.0
    ))

    # 4. Formateurs
    formateurs = [
        (
            "Ndiaye", "Ibrahima", "ibrahima.ndiaye@formation-sport.fr", "06 12 34 56 78", "Indépendant", "84912384700019",
            420.0, 60.0,
            json.dumps(["Méthodologie de projet", "Diagnostic de territoire", "Évaluation", "Réglementation sportive"], ensure_ascii=False),
            json.dumps({"lundi": True, "mardi": True, "mercredi": False, "jeudi": True, "vendredi": True}, ensure_ascii=False),
            "ED-75-98214-APT", "Master STAPS & DEJEPS DPTR"
        ),
        (
            "Benali", "Sarah", "sarah.benali@gestion-asso.fr", "06 98 76 54 32", "Indépendant", "91283746500021",
            450.0, 64.0,
            json.dumps(["Budget", "Comptabilité de projet", "Financements publics & Mécénat"], ensure_ascii=False),
            json.dumps({"lundi": False, "mardi": True, "mercredi": True, "jeudi": True, "vendredi": False}, ensure_ascii=False),
            "Non applicable", "Expert-Comptable mémorialiste & Formatrice DRAJES"
        ),
        (
            "Lefebvre", "Marc", "marc.lefebvre@digital-coach.fr", "06 45 67 89 01", "Indépendant", "77889911200034",
            480.0, 68.0,
            json.dumps(["IA", "Outils numériques", "Communication & Réseaux sociaux"], ensure_ascii=False),
            json.dumps({"lundi": True, "mardi": False, "mercredi": True, "jeudi": False, "vendredi": True}, ensure_ascii=False),
            "ED-92-11409-AP", "Master Ingénierie Pédagogique Numérique"
        ),
        (
            "Mansouri", "Driss", "driss.mansouri@outdoor-expert.fr", "06 33 22 11 00", "Indépendant", "66554433200045",
            400.0, 57.0,
            json.dumps(["Activités Pleine Nature", "Sécurité", "Pédagogie de l'effort", "Évaluation"], ensure_ascii=False),
            json.dumps({"lundi": True, "mardi": True, "mercredi": False, "jeudi": True, "vendredi": True}, ensure_ascii=False),
            "ED-75-33412-APT", "BEES 2e degré & BPJEPS APT"
        ),
        (
            "Dupont", "Camille", "camille.dupont@dynamique-asso.fr", "06 77 88 99 22", "Indépendant", "55443322100056",
            420.0, 60.0,
            json.dumps(["Communication & Réseaux sociaux", "Dynamique de groupe", "Diagnostic de territoire"], ensure_ascii=False),
            json.dumps({"lundi": True, "mardi": True, "mercredi": True, "jeudi": True, "vendredi": False}, ensure_ascii=False),
            "ED-93-77611-LTP", "DEJEPS Animation Socio-Educative"
        )
    ]

    cursor.executemany("""
    INSERT INTO formateurs (nom, prenom, email, telephone, statut, siret, taux_journalier, taux_horaire, competences_json, disponibilites_json, carte_pro_num, diplomes_titres)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, formateurs)

    # 5. Stagiaires (Session 1 : BP-APT-2026-01)
    stagiaires = [
        ("Martin", "Léo", "2001-05-14", "leo.martin@gmail.com", "06 11 22 33 44", "Apprentissage", "Club Omnisports de Vincennes", "Jean-Marc Voisin", "jm.voisin@cov-sport.fr", "01 43 28 90 00", "En rédaction", None),
        ("Traoré", "Aminata", "2002-11-20", "aminata.traore@outlook.fr", "06 22 33 44 55", "Apprentissage", "Mairie de Paris - Direction Jeunesse", "Nathalie Guérin", "nathalie.guerin@paris.fr", "01 42 76 40 40", "Validé pour jury", "2026-09-20"),
        ("Dubois", "Thomas", "1999-08-03", "thomas.dubois@free.fr", "06 33 44 55 66", "Contrat Pro", "Association Sportive Belleville", "Kamel Cheikh", "kamel@asb-sport.org", "01 40 33 12 12", "En rédaction", None),
        ("Belkacem", "Inès", "2003-02-17", "ines.belkacem@gmail.com", "06 44 55 66 77", "Apprentissage", "Centre Social & Sportif Rosa Parks", "Fatima Mansour", "fatima@cs-rosaparks.fr", "01 48 03 55 66", "En rédaction", None),
        ("Morel", "Julien", "2000-09-29", "julien.morel@orange.fr", "06 55 66 77 88", "Transition Pro", "UCPA Île-de-France", "Arnaud Petit", "apetit@ucpa.asso.fr", "01 45 87 90 90", "Retard", None),
        ("Zerrouki", "Sofiane", "2002-04-12", "sofiane.zerrouki@hotmail.com", "06 66 77 88 99", "Apprentissage", "ASPTT Grand Paris", "Brigitte Roux", "b.roux@asptt-paris.fr", "01 47 00 22 33", "Validé pour jury", "2026-09-22"),
        ("Bernard", "Lucas", "2001-12-05", "lucas.bernard@gmail.com", "06 77 88 99 00", "Apprentissage", "Fédération Française Sports pour Tous", "Gérard Fabre", "gerard.fabre@sportspourtous.org", "01 41 66 70 00", "En rédaction", None),
        ("Mercier", "Chloé", "2003-07-24", "chloe.mercier@gmail.com", "06 88 99 00 11", "Apprentissage", "Gymnase Club Montreuil", "Élodie Vernet", "elodie@gcm-fitness.fr", "01 48 55 11 22", "En rédaction", None)
    ]

    for s in stagiaires:
        cursor.execute("""
        INSERT INTO stagiaires (session_id, nom, prenom, date_naissance, email, telephone, statut_financement, structure_accueil, tuteur_nom, tuteur_email, tuteur_telephone, statut_dossier_projet, date_depot_effectif)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, s)

    # 6. Planning pré-configuré (Exemple concret : Semaine du 6 au 10 octobre 2026 évoqué par l'utilisateur !)
    planning_items = [
        # Semaine précédente effectuée (Fin Septembre)
        (1, "2026-09-24", "Journée", 7.0, "Méthodologie de projet", 1, "Effectué", "Salle Principale A1", "Séance cadrage UC1/UC2"),
        (1, "2026-09-25", "Journée", 7.0, "Méthodologie de projet", 1, "Effectué", "Salle Principale A1", "Élaboration des hypothèses de projet"),
        (1, "2026-09-28", "Journée", 7.0, "Activités Pleine Nature", 4, "Effectué", "Plateau Vincennes", "Randonnée et orientation pédagogique"),
        (1, "2026-09-29", "Journée", 7.0, "Activités Pleine Nature", 4, "Effectué", "Plateau Vincennes", "Sécurité et gestion des imprévus"),
        # Semaine d'Octobre demandée spécifiquement :
        # "1 jour sur l'IA, 1 jour sur le diagnostic, 1 jour sur le budget, 1 jour sur la com, 1 jour sur l'évaluation"
        (1, "2026-10-05", "Journée", 7.0, "IA", 3, "Confirmé", "Salle Numérique B2", "IA appliquée à la gestion de séance sportive"),
        (1, "2026-10-06", "Journée", 7.0, "Diagnostic de territoire", 1, "Confirmé", "Salle Principale A1", "Enquête de terrain et cartographie des besoins"),
        (1, "2026-10-07", "Journée", 7.0, "Budget", 2, "Confirmé", "Salle Principale A1", "Modélisation du budget prévisionnel d'un projet"),
        (1, "2026-10-08", "Journée", 7.0, "Communication & Réseaux sociaux", 5, "Confirmé", "Salle Principale A1", "Stratégie de communication pour recruter des pratiquants"),
        (1, "2026-10-09", "Journée", 7.0, "Évaluation", 1, "Confirmé", "Salle Principale A1", "Indicateurs d'impact et bilan certificatif UC2"),
        # Semaine suivante (Mi-Octobre)
        (1, "2026-10-15", "Journée", 7.0, "Pédagogie de l'effort", 4, "Planifié", "Gymnase Pierre de Coubertin", "Conception de cycles d'entretien physique"),
        (1, "2026-10-16", "Journée", 7.0, "Pédagogie de l'effort", 4, "Planifié", "Gymnase Pierre de Coubertin", "Mise en situation pratique UC3/UC4")
    ]

    cursor.executemany("""
    INSERT INTO planning_slots (session_id, date_slot, periode, nb_heures, thematique, formateur_id, statut_slot, salle, commentaire)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, planning_items)

    # 7. Facturation formateurs (Matrice complète)
    factures_data = [
        # Ibrahima Ndiaye - 24/09 (Effectué, Facture reçue et transmise en paiement)
        (1, 1, 1, "2026-09-24", "Méthodologie de projet", 7.0, 420.0, "Effectué", "FAC-2026-09-112", "2026-09-26", "2026-09-27", "Transmis en paiement", None, "Virement bancaire", "Facture validée par le coordonnateur"),
        # Ibrahima Ndiaye - 25/09 (Effectué, Payé !)
        (1, 1, 2, "2026-09-25", "Méthodologie de projet", 7.0, 420.0, "Effectué", "FAC-2026-09-113", "2026-09-26", "2026-09-27", "Payé", "2026-09-29", "Virement bancaire", "Règlement SEPA n° 44921"),
        # Driss Mansouri - 28/09 (Effectué, Facture reçue)
        (4, 1, 3, "2026-09-28", "Activités Pleine Nature", 7.0, 400.0, "Effectué", "FAC-DM-2026-44", "2026-09-29", None, "Facture reçue", None, "Virement bancaire", "En attente transmission compta"),
        # Driss Mansouri - 29/09 (Effectué, en attente facture)
        (4, 1, 4, "2026-09-29", "Activités Pleine Nature", 7.0, 400.0, "Effectué", None, None, None, "En attente facture", None, "Virement bancaire", "Relance envoyée"),
        # Interventions prévues Octobre (Planifié / En attente intervention)
        (3, 1, 5, "2026-10-05", "IA", 7.0, 480.0, "Planifié", None, None, None, "En attente facture", None, "Virement bancaire", "Contrat d'intervention signé"),
        (1, 1, 6, "2026-10-06", "Diagnostic de territoire", 7.0, 420.0, "Planifié", None, None, None, "En attente facture", None, "Virement bancaire", "Intervention programmée"),
        (2, 1, 7, "2026-10-07", "Budget", 7.0, 450.0, "Planifié", None, None, None, "En attente facture", None, "Virement bancaire", "Intervention programmée"),
        (5, 1, 8, "2026-10-08", "Communication & Réseaux sociaux", 7.0, 420.0, "Planifié", None, None, None, "En attente facture", None, "Virement bancaire", "Intervention programmée"),
        (1, 1, 9, "2026-10-09", "Évaluation", 7.0, 420.0, "Planifié", None, None, None, "En attente facture", None, "Virement bancaire", "Intervention programmée")
    ]

    cursor.executemany("""
    INSERT INTO factures_formateurs (formateur_id, session_id, planning_slot_id, date_intervention, thematique, nb_heures, montant_ht, statut_intervention, numero_facture, date_reception_facture, date_transmission_compta, statut_paiement, date_paiement, mode_reglement, commentaire)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, factures_data)

    # 8. Convocations Certifications (Épreuve UC1/UC2 prévue début Novembre 2026)
    convocations = [
        (1, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-24", "09h00 - 10h00", "Salle de Soutenance A - DRAJES", "M. Jean Renard (Inspecteur DRAJES) & Mme Claire Thomas (Directrice Club Sportif)", "Prête", "Convoqué"),
        (2, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-24", "10h15 - 11h15", "Salle de Soutenance A - DRAJES", "M. Jean Renard (Inspecteur DRAJES) & Mme Claire Thomas (Directrice Club Sportif)", "Envoyée", "Convoqué"),
        (3, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-24", "11h30 - 12h30", "Salle de Soutenance A - DRAJES", "M. Jean Renard (Inspecteur DRAJES) & Mme Claire Thomas (Directrice Club Sportif)", "Prête", "Convoqué"),
        (4, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-24", "14h00 - 15h00", "Salle de Soutenance B - DRAJES", "Mme Hélène Mercier (DRAJES) & M. Patrick Simon (Coordonnateur EPGF)", "Prête", "Convoqué"),
        (5, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-24", "15h15 - 16h15", "Salle de Soutenance B - DRAJES", "Mme Hélène Mercier (DRAJES) & M. Patrick Simon (Coordonnateur EPGF)", "Prête", "Convoqué"),
        (6, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-25", "09h00 - 10h00", "Salle de Soutenance A - DRAJES", "M. Jean Renard (Inspecteur DRAJES) & Mme Claire Thomas (Directrice Club Sportif)", "Envoyée", "Convoqué"),
        (7, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-25", "10h15 - 11h15", "Salle de Soutenance A - DRAJES", "M. Jean Renard (Inspecteur DRAJES) & Mme Claire Thomas (Directrice Club Sportif)", "Prête", "Convoqué"),
        (8, 1, "Certification UC1 & UC2 - Soutenance du Projet d'Animation", "2026-11-25", "11h30 - 12h30", "Salle de Soutenance A - DRAJES", "M. Jean Renard (Inspecteur DRAJES) & Mme Claire Thomas (Directrice Club Sportif)", "Prête", "Convoqué")
    ]

    cursor.executemany("""
    INSERT INTO convocations (stagiaire_id, session_id, titre_epreuve, date_epreuve, heure_passage, salle_ou_plateau, composition_jury, statut_envoi, statut_presence)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, convocations)

    conn.commit()
    conn.close()
    print("Database seeded with rich JEPS/RNCP reference data!")

if __name__ == "__main__":
    init_db()
    seed_data()
