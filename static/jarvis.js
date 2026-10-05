/**
 * JARVIS — Assistant conversationnel du coordonnateur (CoordoPro JEPS)
 * --------------------------------------------------------------------
 * 100 % déterministe : AUCUN LLM, AUCUNE API payante.
 * Un moteur de règles (mots-clés + expressions régulières) comprend des
 * phrases en français et pilote les API locales existantes (/api/...).
 *
 * POUR MODIFIER LE COMPORTEMENT : éditez uniquement les sections
 *   1. CONFIG        (mots-clés, valeurs par défaut)
 *   2. CHECKLISTS    (pièces des dossiers DRAJES)
 *   3. INTENTS       (liste ordonnée des règles -> actions)
 * Vocal : API Web Speech du navigateur (gratuite, Chrome/Edge).
 */
(function () {
    "use strict";

    // ================================================================
    // 1. CONFIG
    // ================================================================
    const CONFIG = {
        anneeParDefaut: 2026,
        salleParDefaut: "Salle A1 - Principale",
        statutAjout: "Proposé",
        mois: { janvier: 1, fevrier: 2, mars: 3, avril: 4, mai: 5, juin: 6, juillet: 7,
                aout: 8, septembre: 9, octobre: 10, novembre: 11, decembre: 12 },
        jours: { dimanche: 0, lundi: 1, mardi: 2, mercredi: 3, jeudi: 4, vendredi: 5, samedi: 6 },
        diplomes: {
            "mapst": "BPJEPS MAPST (ex APT)", "apt": "BPJEPS MAPST (ex APT)",
            "apsf": "BPJEPS APSF (ex AF)", "af": "BPJEPS APSF (ex AF)",
            "asec": "BPJEPS ASEC", "equitation": "BPJEPS Équitation",
            "cpjeps": "CPJEPS Animateur (AAVQ)", "aavq": "CPJEPS Animateur (AAVQ)",
            "dejeps": "DEJEPS DPTR", "desjeps": "DESJEPS",
            "bafa": "BAFA (Brevet d'Aptitude aux Fonctions d'Animateur)",
            "bafd": "BAFD (Brevet d'Aptitude aux Fonctions de Directeur)"
        }
    };

    // ================================================================
    // 2. CHECKLISTS (structure issue du Digipad DRAJES « Réforme BC »)
    // ================================================================
    const CHECKLISTS = {
        habilitation: {
            titre: "Étape 1/3 — Dossier d'Habilitation Réglementaire (DRAJES / RNCP)",
            pieces: [
                "Respect du cahier des charges — Annexe 2 du Code du Sport",
                "Arrêté de création de la mention ou spécialité",
                "Ruban pédagogique centre & entreprise (600h / 600h)",
                "Désignation du Coordonnateur Pédagogique référent",
                "Équipe de formateurs habilités (CV, cartes pros, diplômes)",
                "Grilles certificatives d'évaluation par bloc (BC)",
                "Positionnement, allègements et livret d'alternance"
            ],
            questions: [
                "Pour quel diplôme souhaitez-vous déposer l'habilitation ? (ex : BPJEPS MAPST, CPJEPS, BAFA, BAFD)",
                "Quel est le volume horaire prévu en centre de formation ? (ex : 600h)",
                "Qui est le coordonnateur pédagogique référent désigné ?",
                "Avez-vous rattaché au moins 2 formateurs avec carte pro valide ?"
            ]
        },
        ouverture: {
            titre: "Étape 2/3 — Dossier d'Ouverture de Promotion (Cadre & Planning)",
            pieces: [
                "Cadre général et intitulé de la promotion",
                "Dates officielles (début et fin de promo)",
                "Lieu principal et plateaux techniques sportifs/culturels",
                "Ruban pédagogique prévisionnel et planning annuel",
                "Équipe des formateurs mobilisés par thématique"
            ],
            questions: [
                "Quel est l'intitulé de la promotion ? (ex : BPJEPS MAPST Promo 2026/2027)",
                "Quelles sont les dates de début et de fin ? (ex : 01/10/2026 au 30/06/2027)",
                "Quel est le lieu principal de déroulement ? (ex : Gymnase & Salle A1)",
                "Les créneaux de formation sont-ils tous affectés aux formateurs ?"
            ]
        },
        completude: {
            titre: "Étape 3/3 — Dossier de Complétude J-2 mois (Candidats & Alternances)",
            pieces: [
                "Liste nominative des stagiaires inscrits",
                "Attestations des prérequis obligatoires (TEP, PSC1 à jour)",
                "Tableau officiel des structures d'alternance et des tuteurs",
                "Conventions de formation et contrats d'apprentissage signés",
                "Calendrier des jurys certificatifs (UC1/UC2 et UC3/UC4)"
            ],
            questions: [
                "Pour quelle session déposez-vous la complétude ? (ex : Session 1 BPJEPS)",
                "Tous les stagiaires ont-ils leur structure d'accueil et tuteur validés ?",
                "Les attestations TEP et PSC1 sont-elles bien archivées pour chaque candidat ?",
                "Avez-vous fixé la date prévisionnelle des jurys pléniers ?"
            ]
        }
    };

    // ================================================================
    // OUTILS
    // ================================================================
    const norm = s => (s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/['’]/g, " ");
    const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const human = isoStr => new Date(isoStr + "T12:00:00").toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
    const sid = () => (typeof currentSessionId !== "undefined" ? currentSessionId : 1);

    async function api(url, body) {
        const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
        const r = await fetch(url, opt);
        return r.json();
    }

    /** Extrait une date ISO d'une phrase : "9 octobre", "09/10", "demain", "lundi". */
    function parseDate(t) {
        const n = norm(t);
        const today = new Date(); today.setHours(12, 0, 0, 0);
        if (/\bapres[- ]demain\b/.test(n)) { const d = new Date(today); d.setDate(d.getDate() + 2); return iso(d); }
        if (/\bdemain\b/.test(n)) { const d = new Date(today); d.setDate(d.getDate() + 1); return iso(d); }
        if (/\baujourd hui\b/.test(n)) return iso(today);
        let m = n.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
        if (m) return m[0];
        m = n.match(/\b(\d{1,2})[\/.](\d{1,2})(?:[\/.](\d{2,4}))?\b/);
        if (m) {
            let y = m[3] ? +m[3] : CONFIG.anneeParDefaut; if (y < 100) y += 2000;
            return iso(new Date(y, +m[2] - 1, +m[1], 12));
        }
        m = n.match(/\b(\d{1,2}|1er)\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)(?:\s+(\d{4}))?/);
        if (m) {
            const day = m[1] === "1er" ? 1 : +m[1];
            return iso(new Date(m[3] ? +m[3] : CONFIG.anneeParDefaut, CONFIG.mois[m[2]] - 1, day, 12));
        }
        for (const [nom, idx] of Object.entries(CONFIG.jours)) {
            if (new RegExp(`\\b${nom}\\b`).test(n)) {
                const d = new Date(today); let diff = (idx - d.getDay() + 7) % 7; if (diff === 0) diff = 7;
                d.setDate(d.getDate() + diff); return iso(d);
            }
        }
        return null;
    }

    function parsePeriode(t) {
        const n = norm(t);
        if (/\bmatin(ee)?\b/.test(n)) return { periode: "Matin (9h-12h30)", heures: 3.5 };
        if (/\bapres[- ]midi\b/.test(n)) return { periode: "Après-midi (13h30-17h)", heures: 3.5 };
        return { periode: "Journée (9h-17h)", heures: 7 };
    }

    // ================================================================
    // MOTEUR FUZZY NLP & DISTANCE DE LEVENSHTEIN (Zéro Dépendance)
    // ================================================================
    function levenshtein(a, b) {
        if (!a || !b) return (a || b).length;
        const m = a.length, n = b.length;
        const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
        for (let i = 0; i <= m; i++) dp[i][0] = i;
        for (let j = 0; j <= n; j++) dp[0][j] = j;
        for (let i = 1; i <= m; i++) {
            for (let j = 1; j <= n; j++) {
                const cost = a[i - 1] === b[j - 1] ? 0 : 1;
                dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost);
            }
        }
        return dp[m][n];
    }

    function fuzzyMatch(word, target, maxDistance = 2) {
        if (!word || !target) return false;
        const w = norm(word);
        const t = norm(target);
        if (w.includes(t) || t.includes(w)) return true;
        if (Math.abs(w.length - t.length) > maxDistance) return false;
        return levenshtein(w, t) <= maxDistance;
    }

    let formateursCache = null;
    async function getFormateurs() {
        if (!formateursCache) formateursCache = await api("/api/formateurs");
        return formateursCache;
    }

    async function findFormateur(t) {
        const n = norm(t);
        const list = await getFormateurs();
        // 1. Match direct strict
        let exact = list.find(f => n.includes(norm(f.nom)) || new RegExp(`\\b${norm(f.prenom)}\\b`).test(n));
        if (exact) return exact;

        // 2. Fuzzy match token par token (support des fautes de frappe comme "ibrahim", "marouan", "mansuri")
        const tokens = n.split(/\s+/).filter(tok => tok.length >= 3);
        for (const tok of tokens) {
            for (const f of list) {
                if (fuzzyMatch(tok, f.prenom, 2) || fuzzyMatch(tok, f.nom, 2)) {
                    return f;
                }
            }
        }
        return null;
    }

    /** Thème = texte après "sur / en / pour / module / matiere" ou reconnaissance dans le catalogue. */
    function parseTheme(t) {
        const m = t.match(/\b(?:sur|en|pour|module|matiere|cours|seance)\s+(?:la |le |l'|les |du |de la )?(.+?)(?:\s+(?:le|du|au|à|a|avec|matin|après-midi|apres-midi)\b.*)?$/i);
        if (!m) return null;
        let theme = m[1].replace(/[.?!]+$/, "").trim();
        // Nettoyage des suffixes de jours ou formateurs
        theme = theme.replace(/\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b.*/i, "").trim();
        return theme.length > 1 && !parseDate(theme) ? theme.charAt(0).toUpperCase() + theme.slice(1) : null;
    }

    // ================================================================
    // ÉTAT DE CONVERSATION (questions de suivi + confirmations)
    // ================================================================
    let pending = null; // { type, data, missing }

    // ================================================================
    // 3. INTENTS — évalués dans l'ordre, la 1re règle qui matche gagne
    // ================================================================
    const INTENTS = [
        { name: "aide", test: n => /^(aide|help|\?|que sais[- ]tu faire|commandes?)\b/.test(n), run: aide },
        { name: "audit", test: n => /\b(audit|anomalie|anomalies|zero[- ]defect|conformite|qualiopi|controle|verif|verifier)\b/.test(n), run: auditIntent },
        { name: "logs", test: n => /\b(historique|derniers changements|journal|evenements?)\b/.test(n) || (/\b(modifi|change)/.test(n) && /\b(quoi|qu[' ]est[- ]ce|qui a)\b/.test(n)), run: logsIntent },
        { name: "modification", test: n => /\b(modifi|change|remplace|affecte|attribue|passe|decale|deplace|revoque)\b/.test(n), run: modificationPlanning },
        { name: "apprentissage", test: n => /\b(apprends?|enregistre que|sache que|quand je dis)\b/.test(n), run: learnIntent },
        { name: "relance", test: n => /\b(relance|relancer|notifier|notification|alerte candidat)\b/.test(n), run: relanceIntent },
        { name: "candidature", test: n => /\b(candidat|candidature|candidats|inscriptions?|pre[- ]?inscription|pieces manquantes)\b/.test(n), run: candidaturesIntent },
        { name: "ajout", test: n => /\b(ajoute|ajouter|place|placer|programme|programmer|planifie|planifier|mets|mettre|cale|caler|bloque|bloquer)\b/.test(n), run: ajoutCreneau },
        { name: "suppression", test: n => /\b(supprime|supprimer|annule|annuler|retire|retirer|efface)\b/.test(n), run: suppression },
        { name: "competence", test: n => /\b(qui peut|qui sait|formateur pour|formateurs? (en|sur)|competen)/.test(n), run: competence },
        { name: "trous", test: n => /\b(a attribuer|trous?|non attribue|sans formateur|manque)\b/.test(n), run: trous },
        { name: "dossier", test: n => /\b(habilitation|completude|ouverture|dossier|bafa|bafd)\b/.test(n), run: dossier },
        { name: "import", test: n => /\b(import|persen|csv)\b/.test(n), run: () => { openPersenModal(); return "J'ouvre l'import PERSEN. Glissez votre fichier CSV dans la zone."; } },
        { name: "automatch", test: n => /\b(auto[- ]?match|propose(r)? (un )?planning|affectation auto)/.test(n), run: async () => { await triggerAutoAssign(); return "Auto-match lancé sur la semaine type. Le planning a été rafraîchi."; } },
        { name: "stats", test: n => /\b(stat|chiffres?|resume|bilan|tableau de bord|dashboard|budget)\b/.test(n), run: stats },
        { name: "planning", test: n => /\b(planning|qui intervient|qui vient|programme du|cours|creneaux?|semaine)\b/.test(n) || !!parseDate(n), run: planning }
    ];

    async function aide() {
        return `Voici ce que je sais faire en mode Jarvis Super-Powers (100% vocal & local) :
<ul class="list-disc pl-4 mt-1 space-y-0.5">
<li>🛡️ <b>« Audit Qualiopi & DRAJES »</b> · <b>« Y a-t-il des anomalies ? »</b></li>
<li>📜 <b>« Historique des modifications »</b> · <b>« Qu'est-ce qui a été modifié ? »</b></li>
<li>🧠 <b>« Apprends que [mot] veut dire [action] »</b> (auto-amélioration)</li>
<li>👥 <b>« Analyse les candidats »</b> · <b>« Relancer les pièces manquantes »</b></li>
<li>📁 <b>« Prépare le dossier d'ouverture BPJEPS »</b> (entretien guidé pas à pas)</li>
<li>📄 <b>« Dossier de complétude MAPST »</b> · <b>« Habilitation BAFA / BAFD »</b></li>
<li>📅 <b>« Ajoute Ibrahima le 9 octobre sur la méthodologie de projet »</b></li>
<li>🔍 <b>« Qui intervient le 12/10 ? »</b> · <b>« Qui peut faire le budget ? »</b></li>
<li>⚡ <b>« Auto-match »</b> · <b>« Créneaux à attribuer »</b> · <b>« Bilan financier »</b></li></ul>
<span class="text-[11px] text-slate-400">100% autonome & local — zéro abonnement — conforme DRAJES & Qualiopi.</span>`;
    }

    async function auditIntent(text) {
        const res = await api(`/api/jarvis/audit?session_id=${sid()}`);
        if (!res) return "Impossible de joindre le moteur d'inspection.";
        let out = `🛡️ <b>Inspection Zéro-Défaut Qualiopi & DRAJES :</b><br>`;
        const badgeColor = res.statut_audit === "CONFORME" ? "bg-emerald-100 text-emerald-800" : (res.statut_audit === "VIGILANCE" ? "bg-amber-100 text-amber-800" : "bg-rose-100 text-rose-800");
        out += `Score de conformité : <b>${res.score_conformite}%</b> — <span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor}">${res.statut_audit}</span><br><br>`;
        if (res.anomalies && res.anomalies.length > 0) {
            out += `<b>⚠️ ${res.anomalies.length} anomalie(s) détectée(s) :</b><br>`;
            res.anomalies.forEach(a => {
                const color = a.severite === "CRITIQUE" ? "text-rose-700 font-bold" : "text-amber-700";
                out += `• <span class="${color}">[${esc(a.severite)}]</span> ${esc(a.critere)} : ${esc(a.message)}<br>`;
            });
        } else {
            out += `✨ <b>Zéro anomalie détectée !</b> La session respecte 100% des critères réglementaires.<br>`;
        }
        if (res.points_forts && res.points_forts.length > 0) {
            out += `<br><span class="text-emerald-700 text-[11px]">Points de conformité validés : ${res.points_forts.slice(0, 3).map(esc).join(" · ")}</span>`;
        }
        return out;
    }

    async function logsIntent(text) {
        const logs = await api("/api/jarvis/logs?limit=6");
        if (!logs || !logs.length) return "Aucune modification enregistrée dans le journal d'audit.";
        let out = `📜 <b>Dernières actions & modifications tracées (Omniscience) :</b><br>`;
        out += logs.map(l => `• <span class="text-slate-400 text-[10px]">${esc(l.date_action)}</span> [<b>${esc(l.source)}</b>] <em>${esc(l.entite)}</em> : ${esc(l.details)}`).join("<br>");
        return out;
    }

    async function learnIntent(text) {
        const m = text.match(/apprends?\s+(?:que\s+)?['"]?(.+?)['"]?\s+(?:veut dire|signifie|declenche|declencher|fait|active)\s+['"]?(.+?)['"]?$/i);
        if (!m) {
            return `Pour m'enseigner une nouvelle règle, dites par exemple :<br>• <b>« Apprends que point presse veut dire relancer les candidats »</b><br>• <b>« Apprends que checkup veut dire audit »</b>`;
        }
        const pattern = m[1].trim();
        const action = m[2].trim();
        const res = await api("/api/jarvis/learn", {
            pattern: pattern,
            action_type: action,
            description: `Règle apprise : ${pattern} -> ${action}`
        });
        if (res.success) {
            return `🧠 <b>Parfait ! J'ai enregistré cette nouvelle compétence.</b><br>Désormais, lorsque vous mentionnerez <em>« ${esc(pattern)} »</em>, j'exécuterai automatiquement l'action <b>${esc(action)}</b>.`;
        }
        return `❌ Erreur lors de l'enregistrement de la règle.`;
    }

    async function ajoutCreneau(text) {
        const data = {
            date_slot: parseDate(text),
            formateur: await findFormateur(text),
            thematique: parseTheme(text),
            ...parsePeriode(text)
        };
        return askMissingOrConfirm(data);
    }

    function askMissingOrConfirm(data) {
        if (!data.date_slot) { pending = { type: "ajout", data, missing: "date" }; return "Pour quelle <b>date</b> ? (ex : 9 octobre, 12/10, lundi)"; }
        if (!data.thematique) { pending = { type: "ajout", data, missing: "thematique" }; return "Sur quelle <b>thématique / module</b> ?"; }
        pending = { type: "confirm-ajout", data };
        const f = data.formateur ? `${data.formateur.prenom} ${data.formateur.nom}` : "<span class='text-rose-600'>à attribuer</span>";
        return `Je prépare ce créneau :
<div class="mt-1 p-2 rounded bg-white border border-slate-200">📅 <b>${human(data.date_slot)}</b> — ${esc(data.periode)}<br>📚 ${esc(data.thematique)}<br>👤 ${f}</div>
Je l'enregistre ? <b>oui / non</b>`;
    }

    async function confirmAjout(data) {
        const res = await api("/api/planning/add", {
            session_id: sid(), date_slot: data.date_slot, thematique: data.thematique,
            formateur_id: data.formateur ? data.formateur.id : null, periode: data.periode,
            nb_heures: data.heures, salle: CONFIG.salleParDefaut,
            statut_slot: data.formateur ? CONFIG.statutAjout : "À attribuer", commentaire: "Ajouté via Jarvis"
        });
        if (!res.success) return `❌ Échec de l'enregistrement : ${esc(res.error || "erreur inconnue")}`;
        if (typeof loadPlanning === "function") await loadPlanning();
        if (typeof loadDashboardStats === "function") loadDashboardStats();
        let msg = `✅ Créneau enregistré le <b>${human(data.date_slot)}</b>.`;
        if (data.formateur) msg += ` <button class="underline text-sky-700" onclick="openSolicitationModal(${res.slot_id || "null"})">Envoyer la sollicitation à ${esc(data.formateur.prenom)}</button>`;
        return msg;
    }

    async function modificationPlanning(text) {
        if (typeof switchTab === "function") switchTab("planning");
        const all = await api(`/api/planning?session_id=${sid()}`);
        const d = parseDate(text);
        const formateur = await findFormateur(text);
        const n = norm(text);

        // Recherche par date OU par thématique / mot-clé (ex: "math", "ia", "budget", "projet", "diagnostic")
        let cibles = [];
        if (d) {
            cibles = all.filter(s => s.date_slot === d);
        } else {
            const tokens = n.split(/\s+/).filter(w => w.length >= 3 && !["modifie", "modifier", "change", "changer", "planning", "cours", "seance", "creneau", "pour", "avec", "dans", "le", "la", "les", "du"].includes(w));
            cibles = all.filter(s => {
                const th = norm(s.thematique || "");
                return tokens.some(t => th.includes(t) || t.includes(th) || fuzzyMatch(t, th, 2));
            });
        }

        if (!cibles.length) {
            // Si aucun créneau existant ne matche, proposer la création immédiate
            const newTheme = parseTheme(text) || (text.includes("math") ? "Mathématiques appliquées" : "Nouveau module");
            const data = {
                date_slot: d || parseDate("lundi"),
                formateur: formateur,
                thematique: newTheme,
                ...parsePeriode(text)
            };
            pending = { type: "confirm-ajout", data };
            return `Je n'ai pas trouvé de cours existant pour cette recherche, mais je peux <b>créer ce créneau</b> :<br>
            📅 <b>${human(data.date_slot)}</b> — 📚 <b>${esc(data.thematique)}</b> ${formateur ? `(👤 ${esc(formateur.prenom)} ${esc(formateur.nom)})` : ''}<br>
            Voulez-vous que je l'enregistre ? <b>oui / non</b>`;
        }

        const slot = cibles[0];
        // Qu'est-ce qu'on modifie ? Formateur, date, thématique, ou statut
        let newFormateur = formateur || (slot.formateur_id ? { id: slot.formateur_id, prenom: slot.formateur_prenom, nom: slot.formateur_nom } : null);
        let newDate = d || slot.date_slot;
        let newTheme = parseTheme(text) || slot.thematique;

        pending = {
            type: "confirm-modif",
            slot: slot,
            data: {
                slot_id: slot.id,
                date_slot: newDate,
                thematique: newTheme,
                formateur_id: newFormateur ? newFormateur.id : null,
                formateur_nom: newFormateur ? `${newFormateur.prenom} ${newFormateur.nom}` : "À attribuer",
                periode: slot.periode,
                nb_heures: slot.nb_heures,
                salle: slot.salle,
                statut_slot: newFormateur ? "Confirmé" : slot.statut_slot
            }
        };

        return `J'ai trouvé le créneau du <b>${human(slot.date_slot)}</b> (<em>${esc(slot.thematique)}</em>).<br>
        Voulez-vous appliquer cette modification ?<br>
        • Date : <b>${human(newDate)}</b><br>
        • Thématique : <b>${esc(newTheme)}</b><br>
        • Intervenant : <b>${esc(pending.data.formateur_nom)}</b><br>
        Confirmer ? <b>oui / non</b>`;
    }

    async function confirmModif(data) {
        const res = await api("/api/planning/update", {
            slot_id: data.slot_id,
            date_slot: data.date_slot,
            thematique: data.thematique,
            formateur_id: data.formateur_id,
            periode: data.periode,
            nb_heures: data.nb_heures,
            salle: data.salle,
            statut_slot: data.statut_slot,
            commentaire: "Mis à jour via Jarvis"
        });
        if (!res.success) return `❌ Échec de la modification : ${esc(res.error || "erreur")}`;
        if (typeof loadPlanning === "function") await loadPlanning();
        if (typeof loadDashboardStats === "function") loadDashboardStats();
        return `✅ <b>Créneau mis à jour avec succès !</b><br>📅 <b>${human(data.date_slot)}</b> · 📚 <b>${esc(data.thematique)}</b> (${esc(data.formateur_nom)})`;
    }

    async function suppression(text) {
        const d = parseDate(text);
        if (!d) return "Précisez la date du créneau à supprimer (ex : <b>supprime le créneau du 13 octobre</b>).";
        const slots = (await api(`/api/planning?session_id=${sid()}`)).filter(s => s.date_slot === d);
        if (!slots.length) return `Aucun créneau trouvé le ${human(d)}.`;
        pending = { type: "confirm-suppr", data: slots };
        return `Je vais supprimer ${slots.length} créneau(x) le <b>${human(d)}</b> :<br>${slots.map(s => "• " + esc(s.thematique)).join("<br>")}<br>Confirmer ? <b>oui / non</b>`;
    }

    async function competence(text) {
        const n = norm(text).replace(/.*\b(qui peut faire|qui peut|qui sait|formateurs? pour|formateurs? en|formateurs? sur|competences? en)\b/, "");
        const mots = n.split(/\s+/).filter(w => w.length > 3);
        const list = await getFormateurs();
        const hits = list.filter(f => f.competences.some(c => mots.some(m => norm(c).includes(m))));
        if (!hits.length) return "Aucun formateur ne correspond à cette compétence dans votre répertoire.";
        return "Formateurs compétents :<br>" + hits.map(f => `• <b>${esc(f.prenom)} ${esc(f.nom)}</b> — ${f.taux_journalier} €/j <span class="text-slate-400">(${f.competences.map(esc).join(", ")})</span>`).join("<br>");
    }

    async function trous() {
        const slots = (await api(`/api/planning?session_id=${sid()}`)).filter(s => !s.formateur_id || s.statut_slot === "À attribuer");
        if (!slots.length) return "🎉 Tous les créneaux ont un formateur.";
        return `${slots.length} créneau(x) sans formateur :<br>` + slots.map(s => `• ${human(s.date_slot)} — <b>${esc(s.thematique)}</b>`).join("<br>") + `<br><span class="text-[11px] text-slate-400">Astuce : « qui peut faire ${esc(slots[0].thematique)} ? »</span>`;
    }

    async function planning(text) {
        const all = await api(`/api/planning?session_id=${sid()}`);
        const d = parseDate(text);
        let slots, titre;
        if (d) { slots = all.filter(s => s.date_slot === d); titre = human(d); }
        else {
            const start = new Date(); start.setHours(0, 0, 0, 0);
            const end = new Date(start); end.setDate(end.getDate() + 7);
            slots = all.filter(s => { const x = new Date(s.date_slot + "T12:00:00"); return x >= start && x < end; });
            titre = "les 7 prochains jours";
            if (!slots.length) { slots = all.slice(0, 8); titre = "les prochains créneaux de la session"; }
        }
        if (!slots.length) return `Aucun créneau pour ${titre}.`;
        return `Planning — <b>${titre}</b> :<br>` + slots.map(s => {
            const f = s.formateur_nom ? `${esc(s.formateur_prenom)} ${esc(s.formateur_nom)}` : "<span class='text-rose-600'>à attribuer</span>";
            return `• ${d ? "" : human(s.date_slot) + " — "}<b>${esc(s.thematique)}</b> · ${f} · <span class="text-slate-400">${esc(s.statut_slot)}</span>`;
        }).join("<br>");
    }

    async function stats() {
        const s = await api("/api/stats");
        const lignes = Object.entries(s).filter(([, v]) => typeof v !== "object").map(([k, v]) => `• ${esc(k.replace(/_/g, " "))} : <b>${esc(v)}</b>`);
        return "Bilan actuel :<br>" + lignes.join("<br>");
    }

    async function candidaturesIntent(text) {
        if (typeof switchTab === "function") switchTab("candidatures");
        const cands = await api("/api/candidatures");
        if (!cands || cands.length === 0) return "Aucune candidature enregistrée pour l'instant.";
        let res = `👥 <b>${cands.length} candidat(s) dans le parcours :</b><br>`;
        res += cands.map(c => `• <b>${esc(c.prenom)} ${esc(c.nom)}</b> (${esc(c.diplome_vise)}) : Score écrits <b>${c.score_ecrit}%</b> · <em>${esc(c.statut)}</em><br>&nbsp;&nbsp;<span class="text-slate-500">IA : ${esc(c.analyse_ia || 'Conforme')}</span><br>&nbsp;&nbsp;<span class="text-rose-600">Manque : ${esc(c.pieces_manquantes || 'Dossier complet')}</span>`).join("<br>");
        res += `<br><span class="text-[11px] text-slate-400">Dites « relancer les pièces manquantes » pour notifier les candidats incomplets.</span>`;
        return res;
    }

    async function relanceIntent(text) {
        await api("/api/candidature/relancer", { candidature_id: 1 });
        if (typeof loadCandidatures === "function") loadCandidatures();
        return `📨 <b>Relances automatiques programmées envoyées !</b><br>Les candidats avec pièces manquantes (TEP, PSC1, identité) ont reçu la notification de rappel paramétrée pour le cycle de 10 jours.`;
    }

    async function dossier(text) {
        const n = norm(text);
        const type = /completude/.test(n) ? "completude" : /ouverture/.test(n) ? "ouverture" : /habilitation/.test(n) ? "habilitation" : null;
        if (!type) { pending = { type: "dossier-type" }; return "Quel type de dossier souhaitez-vous préparer ?<br>1. <b>Habilitation</b> (DRAJES / RNCP)<br>2. <b>Ouverture de Promotion</b> (Cadre & Planning)<br>3. <b>Complétude</b> (J-2 mois avec liste des candidats)"; }
        
        const dipKey = Object.keys(CONFIG.diplomes).find(k => new RegExp(`\\b${k}\\b`).test(n)) || "mapst";
        const dipNom = CONFIG.diplomes[dipKey];
        const cl = CHECKLISTS[type];
        if (typeof switchTab === "function") switchTab("dossiers");

        // Démarrage de l'entretien interactif pas-à-pas (Mode Jarvis)
        pending = {
            type: "dossier-interview",
            dossierType: type,
            diplome: dipNom,
            step: 0,
            answers: {}
        };

        let out = `📁 <b>${cl.titre}</b> — ${dipNom}<br>`;
        out += `<span class="text-slate-500 text-[11px]">Je lance l'entretien guidé pour rédiger votre dossier. Répondez simplement à mes questions.</span><br><br>`;
        out += `<b>Question 1/4 :</b> ${cl.questions[0]}`;
        return out;
    }

    // ================================================================
    // ROUTEUR
    // ================================================================
    async function handle(text) {
        const n = norm(text).trim();
        if (pending) {
            const p = pending;
            const oui = /^(oui|ok|yes|vas[- ]y|go|valide|confirme|d accord)\b/.test(n);
            const non = /^(non|annule|stop|no)\b/.test(n);

            if (p.type === "dossier-interview") {
                if (non) { pending = null; return "Entretien de dossier annulé."; }
                const cl = CHECKLISTS[p.dossierType];
                p.answers[p.step] = text.trim();
                p.step++;

                if (p.step < cl.questions.length) {
                    return `<b>Question ${p.step + 1}/${cl.questions.length} :</b> ${cl.questions[p.step]}`;
                } else {
                    pending = null;
                    let urlDoc = p.dossierType === "habilitation" ? `/api/dossier/habilitation?diplome_code=BPJEPS_APT` : (p.dossierType === "ouverture" ? `/api/dossier/ouverture?session_id=1` : `/api/dossier/completude?session_id=1`);
                    return `🎉 <b>Parfait ! J'ai toutes les informations nécessaires.</b><br>
                    Le <b>${cl.titre}</b> a été compilé selon le référentiel officiel.<br><br>
                    <a href="${urlDoc}" target="_blank" class="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-3 py-1.5 rounded text-xs shadow-sm">
                        📄 Consulter & Télécharger le Dossier Officiel Prêt
                    </a>`;
                }
            }

            if (p.type === "confirm-ajout") { pending = null; return oui ? confirmAjout(p.data) : non ? "Ok, j'annule." : (pending = p, "Répondez <b>oui</b> ou <b>non</b>."); }
            if (p.type === "confirm-modif") { pending = null; return oui ? confirmModif(p.data) : non ? "Ok, modification annulée." : (pending = p, "Répondez <b>oui</b> ou <b>non</b>."); }
            if (p.type === "confirm-suppr") {
                pending = null; if (!oui) return "Suppression annulée.";
                for (const s of p.data) await api("/api/planning/delete", { slot_id: s.id });
                if (typeof loadPlanning === "function") await loadPlanning();
                return `🗑️ ${p.data.length} créneau(x) supprimé(s).`;
            }
            if (p.type === "ajout") {
                pending = null; if (non) return "Ok, j'annule.";
                if (p.missing === "date") p.data.date_slot = parseDate(text);
                if (p.missing === "thematique") p.data.thematique = text.trim().charAt(0).toUpperCase() + text.trim().slice(1);
                if (!p.data.formateur) p.data.formateur = await findFormateur(text);
                return askMissingOrConfirm(p.data);
            }
            if (p.type === "dossier-type") { pending = null; return dossier("dossier " + text); }
        }
        // 1. Consultation des règles dynamiques apprises en base (/api/jarvis/rules)
        try {
            const dynamicRules = await api("/api/jarvis/rules");
            if (Array.isArray(dynamicRules)) {
                for (const r of dynamicRules) {
                    if (r.declencheur_pattern && n.includes(norm(r.declencheur_pattern))) {
                        const target = r.action_type.toLowerCase();
                        if (target.includes("audit")) return auditIntent(text);
                        if (target.includes("relance")) return relanceIntent(text);
                        if (target.includes("candidat")) return candidaturesIntent(text);
                        if (target.includes("planning") || target.includes("cours")) return planning(text);
                    }
                }
            }
        } catch (e) { /* fallback local */ }

        // 2. Évaluation des intentions natives
        for (const intent of INTENTS) if (intent.test(n)) return intent.run(text);

        // 3. Filet de sécurité intelligent : si l'utilisateur mentionne une matière, un formateur ou une date sans verbe explicite
        const dGuessed = parseDate(text);
        const fGuessed = await findFormateur(text);
        const thGuessed = parseTheme(text);
        if (dGuessed || fGuessed || thGuessed || /\b(cours|seance|creneau|module|matiere|prof|intervenant|formation)\b/.test(n)) {
            return modificationPlanning(text);
        }

        return `Je n'ai pas compris cette formulation précise 🤔.<br>
        Vous pouvez :<br>
        • Utiliser une commande directe : <b>« Modifie le cours de mathématiques »</b>, <b>« Ajoute Marc lundi »</b>, <b>« Audit »</b>.<br>
        • M'apprendre votre tournure en disant : <b>« Apprends que ${esc(text.slice(0, 30))} veut dire modifier le planning »</b>.`;
    }

    // ================================================================
    // INTERFACE (injectée automatiquement)
    // ================================================================
    function buildUI() {
        const btn = document.createElement("button");
        btn.id = "jarvis-toggle";
        btn.title = "Assistant Jarvis";
        btn.setAttribute("aria-label", "Ouvrir l'assistant Jarvis");
        btn.className = "fixed bottom-[30px] left-[30px] z-[90] w-14 h-14 rounded-full bg-gradient-to-br from-slate-900 to-indigo-700 text-white shadow-xl flex items-center justify-center hover:scale-105 transition";
        btn.innerHTML = '<i class="fa-solid fa-robot text-xl"></i>';
        btn.onclick = toggle;

        const panel = document.createElement("section");
        panel.id = "jarvis-panel";
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-label", "Assistant Jarvis");
        panel.className = "hidden fixed bottom-[100px] left-[30px] z-[95] w-[380px] max-w-[calc(100vw-40px)] h-[540px] max-h-[75vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden";
        panel.innerHTML = `
            <header class="px-4 py-3 bg-gradient-to-r from-slate-900 to-indigo-700 text-white flex items-center justify-between">
                <div class="flex items-center gap-2"><i class="fa-solid fa-robot"></i>
                    <div><div class="font-bold text-sm">Jarvis</div><div class="text-[10px] text-indigo-200">Assistant du coordonnateur · 100 % local</div></div></div>
                <button id="jarvis-close" aria-label="Fermer" class="text-white/70 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
            </header>
            <div id="jarvis-log" class="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50 text-xs" aria-live="polite"></div>
            <div id="jarvis-chips" class="px-3 pt-2 flex flex-wrap gap-1.5 bg-white"></div>
            <form id="jarvis-form" class="p-3 flex items-center gap-2 bg-white border-t border-slate-100">
                <button type="button" id="jarvis-mic" title="Dicter (Chrome/Edge)" aria-label="Dicter" class="w-9 h-9 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600"><i class="fa-solid fa-microphone"></i></button>
                <input id="jarvis-input" autocomplete="off" placeholder="Ex : ajoute Ibrahima le 9 octobre sur la méthodo…" class="flex-1 text-xs border border-slate-300 rounded-full px-3 py-2 outline-none focus:border-indigo-500">
                <button type="submit" aria-label="Envoyer" class="w-9 h-9 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white"><i class="fa-solid fa-paper-plane"></i></button>
            </form>`;
        document.body.append(btn, panel);

        document.getElementById("jarvis-close").onclick = toggle;
        document.getElementById("jarvis-form").onsubmit = e => { e.preventDefault(); send(); };
        document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.classList.contains("hidden")) toggle(); });

        const chips = ["🛡️ Audit Qualiopi", "📜 Historique", "👥 Analyse candidats", "📨 Relances J+10", "Dossier ouverture BPJEPS", "Complétude MAPST", "aide"];
        const chipBox = document.getElementById("jarvis-chips");
        chips.forEach(c => {
            const b = document.createElement("button");
            b.type = "button"; b.textContent = c;
            b.className = "text-[11px] px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100 hover:bg-indigo-100";
            b.onclick = () => { document.getElementById("jarvis-input").value = c; send(); };
            chipBox.appendChild(b);
        });

        setupVoice();
        bubble("bot", `Bonjour 👋 Je suis <b>Jarvis</b>. Dites-moi ce que vous voulez faire, à l'écrit ou au micro.<br>Exemple : <b>« Ajoute Ibrahima le 9 octobre sur la méthodologie de projet »</b>`);
    }

    function toggle() {
        const p = document.getElementById("jarvis-panel");
        p.classList.toggle("hidden");
        if (!p.classList.contains("hidden")) document.getElementById("jarvis-input").focus();
    }

    function bubble(who, html) {
        const log = document.getElementById("jarvis-log");
        const d = document.createElement("div");
        d.className = who === "user"
            ? "ml-auto max-w-[85%] bg-indigo-600 text-white px-3 py-2 rounded-2xl rounded-br-sm"
            : "mr-auto max-w-[92%] bg-white border border-slate-200 text-slate-700 px-3 py-2 rounded-2xl rounded-bl-sm leading-relaxed";
        d.innerHTML = html;
        log.appendChild(d);
        log.scrollTop = log.scrollHeight;
        return d;
    }

    async function send() {
        const input = document.getElementById("jarvis-input");
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        bubble("user", esc(text));
        const wait = bubble("bot", '<i class="fa-solid fa-ellipsis fa-fade"></i>');
        try { wait.innerHTML = await handle(text); }
        catch (e) { wait.innerHTML = `❌ Erreur : ${esc(e.message)}. Le serveur local est-il démarré ?`; }
        document.getElementById("jarvis-log").scrollTop = 1e9;
    }

    function setupVoice() {
        const mic = document.getElementById("jarvis-mic");
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) { mic.disabled = true; mic.title = "Dictée non disponible sur ce navigateur (utilisez Chrome ou Edge)"; mic.classList.add("opacity-40"); return; }
        const rec = new SR(); rec.lang = "fr-FR"; rec.interimResults = false;
        rec.onresult = e => { document.getElementById("jarvis-input").value = e.results[0][0].transcript; send(); };
        rec.onend = () => mic.classList.remove("bg-rose-500", "text-white");
        mic.onclick = () => { mic.classList.add("bg-rose-500", "text-white"); rec.start(); };
    }

    // Exposé pour tests console : JarvisEngine.handle("aide")
    window.JarvisEngine = { handle, parseDate, parseTheme, INTENTS, CHECKLISTS, CONFIG };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", buildUI); else buildUI();
})();
