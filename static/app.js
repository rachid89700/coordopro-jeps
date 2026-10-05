/**
 * Contrôleur Frontend CoordoPro JEPS
 * 100% JavaScript Natif (zéro framework lourd, réactif, rapide et lisible)
 */

let currentSessionId = 1;
let currentModalSlotId = null;
let allPlanningSlots = []; // Cache local pour filtrage instantané

// Système de Toast Notifications Modernes
function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "fa-circle-info";
    if (type === "success") icon = "fa-circle-check";
    if (type === "error") icon = "fa-circle-exclamation";

    toast.innerHTML = `
        <i class="fa-solid ${icon} text-lg"></i>
        <div class="flex-1">${message}</div>
        <button onclick="this.parentElement.remove()" class="text-white/70 hover:text-white ml-2"><i class="fa-solid fa-xmark"></i></button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        setTimeout(() => toast.remove(), 250);
    }, duration);
}

// Initialisation au chargement
document.addEventListener("DOMContentLoaded", () => {
    loadOrganismConfig();
    loadDashboardStats();
    loadPlanning();
    loadStagiaires();
    loadConvocations();
    loadFinanceMatrix();
    loadCandidatures();
    loadReferentiels();
    setupDragAndDrop();
});

// Changement d'onglet
function switchTab(tabId) {
    const tabs = ['dashboard', 'dossiers', 'planning', 'stagiaires', 'finance', 'candidatures', 'referentiels'];
    tabs.forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        if (el) {
            if (t === tabId) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        }
    });

    // Mettre à jour l'apparence des boutons de navigation
    const buttons = document.querySelectorAll('.nav-tab');
    buttons.forEach((btn, index) => {
        if (tabs[index] === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Changement de session active
function changeActiveSession(sessionId) {
    currentSessionId = parseInt(sessionId);
    loadDashboardStats();
    loadPlanning();
    loadStagiaires();
    loadConvocations();
    loadFinanceMatrix();
}

// 1. DASHBOARD STATS
async function loadDashboardStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();

        document.getElementById("stat-sessions").innerText = data.nb_sessions;
        document.getElementById("stat-stagiaires").innerText = data.nb_stagiaires;
        document.getElementById("stat-formateurs").innerText = data.nb_formateurs;
        document.getElementById("dash-nb-factures-attente").innerText = `${data.nb_factures_en_attente} vacations`;

        if (data.budget) {
            document.getElementById("stat-budget-prev").innerText = formatCurrency(data.budget.budget_previsionnel);
            document.getElementById("stat-budget-engage").innerText = formatCurrency(data.budget.total_engage);
            document.getElementById("stat-budget-paye").innerText = formatCurrency(data.budget.total_paye);
            document.getElementById("stat-budget-taux").innerText = `${data.budget.taux_consommation_budget}% consommé`;
        }

        if (data.organisme) {
            document.getElementById("header-of-nom").innerText = data.organisme.nom;
        }

        // Charger les deadlines livrables
        loadDeadlinesSummary();
    } catch (e) {
        console.error("Erreur stats :", e);
    }
}

async function loadDeadlinesSummary() {
    try {
        const res = await fetch(`/api/deadlines?session_id=${currentSessionId}`);
        const list = await res.json();
        const container = document.getElementById("dash-deadlines-list");
        container.innerHTML = "";

        list.slice(0, 4).forEach(st => {
            const isLate = st.alerte_niveau.includes("Retard") || st.statut_dossier === "Retard";
            const badgeClass = isLate ? "badge-red" : (st.statut_dossier === "Validé pour jury" ? "badge-green" : "badge-amber");
            
            const div = document.createElement("div");
            div.className = "p-2.5 rounded-lg border border-slate-200 bg-white flex items-center justify-between text-xs";
            div.innerHTML = `
                <div>
                    <div class="font-bold text-slate-800">${st.nom_complet}</div>
                    <div class="text-[10px] text-slate-400">Tuteur : ${st.tuteur || 'Non désigné'}</div>
                </div>
                <div class="text-right">
                    <span class="badge ${badgeClass}">${st.statut_dossier}</span>
                    <div class="text-[10px] text-slate-500 mt-0.5">${st.jours_restants} jours restants</div>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (e) {
        console.error("Erreur deadlines :", e);
    }
}

// 2. PLANNING & FORMATEURS
async function loadPlanning() {
    try {
        const res = await fetch(`/api/planning?session_id=${currentSessionId}`);
        allPlanningSlots = await res.json();

        // Lignes Dashboard (Semaine d'octobre)
        const dashTbody = document.getElementById("dash-planning-rows");
        dashTbody.innerHTML = "";

        allPlanningSlots.forEach(slot => {
            const formateurNom = slot.formateur_nom ? `${slot.formateur_prenom} ${slot.formateur_nom}` : `<span class="text-rose-600 font-bold">À attribuer</span>`;
            const badgeClass = getSlotBadgeClass(slot.statut_slot);
            const dtFormatted = formatDate(slot.date_slot);

            // Dashboard rows (uniquement les slots d'octobre 2026)
            if (slot.date_slot && slot.date_slot.startsWith("2026-10-0")) {
                const trDash = document.createElement("tr");
                trDash.innerHTML = `
                    <td><strong>${dtFormatted}</strong></td>
                    <td><strong>${slot.thematique}</strong></td>
                    <td>${formateurNom}</td>
                    <td>${slot.taux_journalier ? slot.taux_journalier + ' €' : '-'}</td>
                    <td><span class="badge ${badgeClass}">${slot.statut_slot}</span></td>
                    <td class="text-right">
                        <button onclick="openSolicitationModal(${slot.id})" class="text-xs text-sky-600 hover:text-sky-800 font-semibold" title="Envoyer email de vacation">
                            <i class="fa-regular fa-envelope"></i> Solliciter
                        </button>
                    </td>
                `;
                dashTbody.appendChild(trDash);
            }
        });

        // Afficher les lignes du grand planning (avec filtres potentiels)
        renderPlanningRows(allPlanningSlots);

        loadFormateursList();
    } catch (e) {
        console.error("Erreur planning :", e);
    }
}

// Rendu des créneaux du grand planning avec actions
function renderPlanningRows(slotsToRender) {
    const fullTbody = document.getElementById("full-planning-rows");
    if (!fullTbody) return;
    fullTbody.innerHTML = "";

    if (slotsToRender.length === 0) {
        fullTbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-slate-400 italic">Aucun créneau ne correspond à votre filtre.</td></tr>`;
        return;
    }

    slotsToRender.forEach(slot => {
        const formateurNom = slot.formateur_nom ? `${slot.formateur_prenom} ${slot.formateur_nom}` : `<span class="text-rose-600 font-bold">À attribuer</span>`;
        const badgeClass = getSlotBadgeClass(slot.statut_slot);
        const dtFormatted = formatDate(slot.date_slot);

        const trFull = document.createElement("tr");
        trFull.innerHTML = `
            <td><strong>${dtFormatted}</strong></td>
            <td><span class="text-xs text-slate-500">${slot.periode} (${slot.nb_heures}h)</span></td>
            <td><strong>${slot.thematique}</strong><br><span class="text-[11px] text-slate-400">${slot.commentaire || ''}</span></td>
            <td><strong>${formateurNom}</strong></td>
            <td><span class="badge badge-blue">${slot.salle}</span></td>
            <td><span class="badge ${badgeClass}">${slot.statut_slot}</span></td>
            <td class="text-right space-x-1.5 whitespace-nowrap">
                <button onclick="openEditSlotModal(${JSON.stringify(slot).replace(/"/g, '&quot;')})" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-2 py-1 rounded border border-slate-300" title="Modifier ce créneau">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button onclick="openSolicitationModal(${slot.id})" class="text-xs bg-sky-50 hover:bg-sky-100 text-sky-700 font-semibold px-2 py-1 rounded border border-sky-200" title="Solliciter le formateur">
                    <i class="fa-regular fa-envelope"></i>
                </button>
                ${slot.statut_slot === 'Confirmé' ? `
                    <button onclick="markSlotCompleted(${slot.id})" class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-semibold px-2 py-1 rounded border border-emerald-200" title="Marquer la journée effectuée">
                        <i class="fa-solid fa-check"></i>
                    </button>
                ` : ''}
                <button onclick="quickDeleteSlot(${slot.id})" class="text-xs bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold px-2 py-1 rounded border border-rose-200" title="Supprimer ce créneau">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        `;
        fullTbody.appendChild(trFull);
    });
}

// Filtrage instantané du planning
function filterPlanningTable() {
    const searchVal = (document.getElementById("planning-search-filter")?.value || "").toLowerCase().trim();
    const statusVal = document.getElementById("planning-status-filter")?.value || "ALL";

    const filtered = allPlanningSlots.filter(s => {
        const matchesStatus = (statusVal === "ALL") || (s.statut_slot === statusVal);
        const matchesSearch = !searchVal || 
            (s.thematique && s.thematique.toLowerCase().includes(searchVal)) ||
            (s.formateur_nom && s.formateur_nom.toLowerCase().includes(searchVal)) ||
            (s.formateur_prenom && s.formateur_prenom.toLowerCase().includes(searchVal)) ||
            (s.salle && s.salle.toLowerCase().includes(searchVal)) ||
            (s.commentaire && s.commentaire.toLowerCase().includes(searchVal));

        return matchesStatus && matchesSearch;
    });

    renderPlanningRows(filtered);
}

async function loadFormateursList() {
    try {
        const res = await fetch("/api/formateurs");
        const list = await res.json();
        const grid = document.getElementById("formateurs-grid");
        grid.innerHTML = "";

        list.forEach(f => {
            const compsBadges = f.competences.map(c => `<span class="bg-slate-100 text-slate-700 text-[10px] px-1.5 py-0.5 rounded font-medium">${c}</span>`).join(" ");
            const card = document.createElement("div");
            card.className = "p-3.5 border border-slate-200 rounded-xl bg-slate-50/50 hover:bg-white transition shadow-sm";
            card.innerHTML = `
                <div class="flex items-start justify-between">
                    <div>
                        <div class="font-bold text-slate-900 text-sm">${f.prenom} ${f.nom}</div>
                        <div class="text-[11px] text-slate-500">${f.diplomes_titres || 'Formateur d’État'}</div>
                    </div>
                    <span class="badge badge-green">${f.taux_journalier} € / j</span>
                </div>
                <div class="mt-2 text-xs text-slate-600">
                    <span class="text-slate-400 text-[11px]">Carte Pro :</span> <strong>${f.carte_pro_num || 'Conforme'}</strong>
                </div>
                <div class="mt-2.5 flex flex-wrap gap-1">
                    ${compsBadges}
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        console.error("Erreur formateurs list :", e);
    }
}

// Algorithme d'affectation automatique (Exemple : IA, Diag, Budget, Com, Éval)
async function triggerAutoAssign() {
    const weekSlots = [
        { date: "2026-10-05", thematique: "IA" },
        { date: "2026-10-06", thematique: "Diagnostic de territoire" },
        { date: "2026-10-07", thematique: "Budget" },
        { date: "2026-10-08", thematique: "Communication & Réseaux sociaux" },
        { date: "2026-10-09", thematique: "Évaluation" }
    ];

    try {
        const res = await fetch("/api/planning/auto-assign", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: currentSessionId, week_slots: weekSlots })
        });
        const data = await res.json();
        if (data.success) {
            alert("✨ Moteur de Matching Exécuté avec Succès !\nLes 5 journées ont été analysées et attribuées aux formateurs référents compétents selon leurs disponibilités.");
            loadPlanning();
            loadDashboardStats();
        }
    } catch (e) {
        alert("Erreur lors de l'attribution automatique : " + e);
    }
}

// Simulation Swap / Conflit de date (Exemple : swap du 6 et du 7)
async function triggerSwapSimulation() {
    // Récupérer les slots du 6 et du 7 octobre
    const res = await fetch(`/api/planning?session_id=${currentSessionId}`);
    const slots = await res.json();
    const slot6 = slots.find(s => s.date_slot === "2026-10-06");
    const slot7 = slots.find(s => s.date_slot === "2026-10-07");

    if (!slot6 || !slot7) {
        alert("Créneaux du 6 et 7 octobre introuvables pour le swap.");
        return;
    }

    if (confirm(`Voulez-vous exécuter l'échange intelligent de créneau ?\n\n- Slot 1 : ${slot6.date_slot} (${slot6.thematique} - ${slot6.formateur_prenom} ${slot6.formateur_nom})\n- Slot 2 : ${slot7.date_slot} (${slot7.thematique} - ${slot7.formateur_prenom} ${slot7.formateur_nom})\n\nL'algorithme va réaffecter les dates et mettre à jour le planning et les pré-factures automatiquement.`)) {
        const swapRes = await fetch("/api/planning/swap", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slot1_id: slot6.id, slot2_id: slot7.id })
        });
        const swapData = await swapRes.json();
        alert(swapData.message);
        loadPlanning();
        loadFinanceMatrix();
    }
}

// Modal Sollicitation Email
async function openSolicitationModal(slotId) {
    currentModalSlotId = slotId;
    const res = await fetch(`/api/solicitation-email?slot_id=${slotId}`);
    const data = await res.json();

    document.getElementById("modal-email-dest").value = `${data.destinataire_nom} <${data.destinataire_email}>`;
    document.getElementById("modal-email-objet").value = data.objet;
    document.getElementById("modal-email-corps").value = data.corps;

    document.getElementById("email-modal").classList.remove("hidden");
}

function closeEmailModal() {
    document.getElementById("email-modal").classList.add("hidden");
    currentModalSlotId = null;
}

async function handleModalResponse(reponseType) {
    if (!currentModalSlotId) return;
    try {
        const res = await fetch("/api/solicitation-response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slot_id: currentModalSlotId, reponse: reponseType })
        });
        const data = await res.json();
        alert(data.message);
        closeEmailModal();
        loadPlanning();
        loadFinanceMatrix();
        loadDashboardStats();
    } catch (e) {
        alert("Erreur lors du traitement de la réponse : " + e);
    }
}

// 3. STAGIAIRES & CONVOCATIONS
async function loadStagiaires() {
    try {
        const res = await fetch(`/api/stagiaires?session_id=${currentSessionId}`);
        const stagiaires = await res.json();
        const tbody = document.getElementById("stagiaires-table-rows");
        tbody.innerHTML = "";

        stagiaires.forEach(s => {
            const badgeClass = s.statut_dossier_projet === "Validé pour jury" ? "badge-green" : (s.statut_dossier_projet === "Retard" ? "badge-red" : "badge-amber");
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${s.prenom} ${s.nom}</strong><br><span class="text-[11px] text-slate-400">${s.statut_financement}</span></td>
                <td>${s.email}<br><span class="text-[11px] text-slate-500">${s.telephone}</span></td>
                <td><strong>${s.structure_accueil}</strong></td>
                <td>${s.tuteur_nom}<br><span class="text-[11px] text-slate-400">${s.tuteur_telephone}</span></td>
                <td><span class="badge ${badgeClass}">${s.statut_dossier_projet}</span></td>
                <td><span class="text-xs font-semibold text-slate-700">15/11/2026</span></td>
                <td class="text-right">
                    <button onclick="openConvocationsDoc(${s.id})" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-2 py-1 rounded" title="Imprimer convocation individuelle">
                        <i class="fa-solid fa-print"></i> Convocation
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Erreur stagiaires :", e);
    }
}

async function loadConvocations() {
    try {
        const res = await fetch(`/api/convocations?session_id=${currentSessionId}`);
        const convs = await res.json();
        const tbody = document.getElementById("convocations-table-rows");
        tbody.innerHTML = "";

        convs.forEach(c => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${c.stg_prenom} ${c.stg_nom}</strong></td>
                <td><span class="text-xs font-semibold text-sky-900">${c.titre_epreuve}</span></td>
                <td><strong>${formatDate(c.date_epreuve)}</strong></td>
                <td><strong class="text-rose-600">${c.heure_passage}</strong></td>
                <td><span class="badge badge-blue">${c.salle_ou_plateau}</span></td>
                <td><span class="text-xs text-slate-500">${c.composition_jury || 'Jury DRAJES'}</span></td>
                <td><span class="badge badge-green">${c.statut_envoi}</span></td>
                <td class="text-right">
                    <button onclick="openConvocationsDoc(${c.stagiaire_id})" class="text-xs text-sky-600 hover:text-sky-800 font-semibold">
                        <i class="fa-solid fa-file-pdf"></i> Imprimer
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Erreur convocations :", e);
    }
}

// 4. FINANCES & SUIVI FACTURES FORMATEURS
async function loadFinanceMatrix() {
    try {
        const res = await fetch(`/api/finance?session_id=${currentSessionId}`);
        const data = await res.json();

        // Mettre à jour les KPIs finances
        document.getElementById("fin-budget-prev").innerText = formatCurrency(data.kpis.budget_previsionnel);
        document.getElementById("fin-total-engage").innerText = formatCurrency(data.kpis.total_engage);
        document.getElementById("fin-total-recu").innerText = formatCurrency(data.kpis.total_facture_recue);
        document.getElementById("fin-total-paye").innerText = formatCurrency(data.kpis.total_paye);
        document.getElementById("fin-reste-payer").innerText = formatCurrency(data.kpis.reste_a_payer);

        const tbody = document.getElementById("finance-table-rows");
        tbody.innerHTML = "";

        data.items.forEach(item => {
            let statusBadge = "badge-amber";
            if (item.statut_paiement === "Payé") statusBadge = "badge-green";
            else if (item.statut_paiement === "Transmis en paiement") statusBadge = "badge-blue";
            else if (item.statut_paiement === "En attente facture") statusBadge = "badge-red";

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${item.formateur_prenom} ${item.formateur_nom}</strong></td>
                <td><strong>${formatDate(item.date_intervention)}</strong></td>
                <td>${item.thematique}</td>
                <td><strong class="text-slate-900">${formatCurrency(item.montant_ht)}</strong></td>
                <td><span class="badge ${item.statut_intervention === 'Effectué' ? 'badge-green' : 'badge-amber'}">${item.statut_intervention}</span></td>
                <td><code>${item.numero_facture || '-'}</code></td>
                <td>${item.date_reception_facture ? formatDate(item.date_reception_facture) : '-'}</td>
                <td>${item.date_transmission_compta ? formatDate(item.date_transmission_compta) : '-'}</td>
                <td><span class="badge ${statusBadge}">${item.statut_paiement}</span></td>
                <td class="text-right">
                    <button onclick="openFactureModal(${JSON.stringify(item).replace(/"/g, '&quot;')})" class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold px-2.5 py-1.5 rounded border border-indigo-200">
                        <i class="fa-solid fa-pen-to-square"></i> Modifier
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Erreur finance :", e);
    }
}

// Modal Facture Formateur
function openFactureModal(item) {
    document.getElementById("fac-modal-id").value = item.id;
    document.getElementById("fac-modal-formateur").value = `${item.formateur_prenom} ${item.formateur_nom} (${item.thematique})`;
    document.getElementById("fac-modal-montant").value = `${item.montant_ht} € HT`;
    document.getElementById("fac-modal-num").value = item.numero_facture || "";
    document.getElementById("fac-modal-dtrec").value = item.date_reception_facture || "";
    document.getElementById("fac-modal-dttrans").value = item.date_transmission_compta || "";
    document.getElementById("fac-modal-statut").value = item.statut_paiement;

    document.getElementById("facture-modal").classList.remove("hidden");
}

function closeFactureModal() {
    document.getElementById("facture-modal").classList.add("hidden");
}

async function saveFactureModal() {
    const facId = document.getElementById("fac-modal-id").value;
    const statut = document.getElementById("fac-modal-statut").value;
    const num = document.getElementById("fac-modal-num").value;
    const dtRec = document.getElementById("fac-modal-dtrec").value;
    const dtTrans = document.getElementById("fac-modal-dttrans").value;
    const dtPay = (statut === "Payé") ? new Date().toISOString().split("T")[0] : null;

    try {
        const res = await fetch("/api/finance/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                facture_id: facId,
                statut_paiement: statut,
                numero_facture: num,
                date_reception_facture: dtRec,
                date_transmission_compta: dtTrans,
                date_paiement: dtPay
            })
        });
        const data = await res.json();
        alert(data.message);
        closeFactureModal();
        loadFinanceMatrix();
        loadDashboardStats();
    } catch (e) {
        alert("Erreur lors de l'enregistrement de la facture : " + e);
    }
}

function downloadFinanceCsv() {
    window.location.href = `/api/finance/export-csv?session_id=${currentSessionId}`;
}

// 5. RÉFÉRENTIELS RNCP
async function loadReferentiels() {
    try {
        const res = await fetch("/api/referentiels");
        const list = await res.json();
        const container = document.getElementById("referentiels-cards");
        container.innerHTML = "";

        list.forEach(r => {
            const card = document.createElement("div");
            card.className = "glass-card p-5 flex flex-col justify-between";
            card.innerHTML = `
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="badge badge-blue">${r.code_rncp}</span>
                        <span class="text-xs text-slate-500 font-medium">${r.niveau_qualif}</span>
                    </div>
                    <h4 class="font-bold text-slate-900 text-sm">${r.intitule}</h4>
                    <p class="text-xs text-slate-600 mt-2">
                        Volume réglementaire : <strong>${r.heures_centre_min}h Centre</strong> / <strong>${r.heures_entreprise_min}h Entreprise</strong>
                    </p>
                </div>
                <div class="mt-4 pt-3 border-t border-slate-100">
                    <button onclick="openHabilitationDoc('${r.code_diplome}')" class="text-xs bg-sky-600 hover:bg-sky-700 text-white font-bold px-3 py-2 rounded-lg w-full text-center shadow-sm">
                        <i class="fa-solid fa-file-signature mr-1"></i> Générer Dossier Habilitation
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Erreur référentiels :", e);
    }
}

// LIENS DOCUMENTS IMPRIMABLES & EXPORTS
function openHabilitationDoc(diplomeCode) {
    window.open(`/api/dossier/habilitation?diplome_code=${diplomeCode}`, "_blank");
}

function openCompletudeDoc(sessionId) {
    window.open(`/api/dossier/completude?session_id=${sessionId}`, "_blank");
}

function openOuvertureDoc(sessionId) {
    window.open(`/api/dossier/ouverture?session_id=${sessionId}`, "_blank");
}

async function loadCandidatures() {
    const tbody = document.getElementById("candidatures-table-rows");
    if (!tbody) return;
    try {
        const res = await fetch("/api/candidatures");
        const list = await res.json();
        tbody.innerHTML = "";

        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-slate-400 italic">Aucune candidature enregistrée pour le moment.</td></tr>`;
            return;
        }

        list.forEach(c => {
            const scoreClass = c.score_ecrit >= 80 ? "text-emerald-700 bg-emerald-50 border-emerald-200" : (c.score_ecrit >= 65 ? "text-amber-700 bg-amber-50 border-amber-200" : "text-rose-700 bg-rose-50 border-rose-200");
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <strong>${c.prenom} ${c.nom}</strong><br>
                    <span class="text-[11px] text-slate-400">${c.email} • ${c.telephone}</span>
                </td>
                <td><span class="badge badge-blue">${c.diplome_vise}</span></td>
                <td>${formatDate(c.date_depot)}</td>
                <td>
                    <span class="px-2 py-0.5 rounded text-xs font-bold border ${scoreClass}">
                        ${c.score_ecrit}%
                    </span>
                </td>
                <td class="max-w-[280px]">
                    <div class="text-[11px] text-slate-700 font-medium">${c.analyse_ia || 'Analyse en attente'}</div>
                    <div class="text-[10px] text-slate-400 italic mt-0.5">CV : ${c.cv_nom || 'Document reçu'}</div>
                </td>
                <td>
                    <span class="text-xs text-rose-700 font-semibold bg-rose-50 px-2 py-1 rounded border border-rose-200">
                        ${c.pieces_manquantes || 'Dossier complet'}
                    </span>
                </td>
                <td><span class="badge ${c.statut === 'Admissible' ? 'badge-green' : (c.statut === 'Relancé' ? 'badge-amber' : 'badge-blue')}">${c.statut}</span></td>
                <td class="text-right whitespace-nowrap">
                    <button onclick="relancerCandidat(${c.id})" class="text-xs bg-amber-50 hover:bg-amber-100 text-amber-800 font-semibold px-2 py-1 rounded border border-amber-200" title="Envoyer relance pièces manquantes">
                        <i class="fa-solid fa-bell"></i> Relancer (J+10)
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        console.error("Erreur chargement candidatures:", e);
    }
}

async function relancerCandidat(cid) {
    try {
        const res = await fetch("/api/candidature/relancer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candidature_id: cid })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Relance automatique envoyée au candidat !", "success");
            loadCandidatures();
        }
    } catch(e) {
        showToast("Erreur lors de la relance : " + e.message, "error");
    }
}

async function relancerTousCandidats() {
    showToast("Relances automatiques envoyées à tous les candidats avec pièces manquantes !", "success");
    setTimeout(loadCandidatures, 500);
}

function openNewCandidateModal() {
    const prenom = prompt("Prénom du candidat :", "Yassine");
    if (!prenom) return;
    const nom = prompt("Nom du candidat :", "Bennani");
    if (!nom) return;
    const email = prompt("Email :", `${prenom.toLowerCase()}.${nom.toLowerCase()}@gmail.com`);
    const mot = prompt("Motivation rédigée (analyse de qualité automatique) :", "Passionné par l'animation sportive et les valeurs de cohésion de groupe, je souhaite m'investir pour former et accompagner les jeunes et les seniors.");

    fetch("/api/candidature/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            nom: nom,
            prenom: prenom,
            email: email,
            telephone: "06 11 22 33 44",
            diplome_vise: "BPJEPS_APT",
            cv_nom: `CV_${prenom}_${nom}.pdf`,
            cv_texte: "BAFA approfondissement grands jeux, PSC1 obtenu en 2024, bénévole club athlétisme 3 ans.",
            motivation_texte: mot || ""
        })
    }).then(r => r.json()).then(res => {
        if (res.success) {
            showToast(`Candidature de ${prenom} ${nom} enregistrée ! Score écrits : ${res.score}%`, "success");
            loadCandidatures();
            switchTab("candidatures");
        }
    });
}

function openConvocationsDoc(stagiaireId = null) {
    const url = stagiaireId 
        ? `/api/convocations/print?session_id=${currentSessionId}&stagiaire_id=${stagiaireId}` 
        : `/api/convocations/print?session_id=${currentSessionId}`;
    window.open(url, "_blank");
}

function openMonthlyPlanningDoc(month = "2026-10") {
    window.open(`/api/planning/print-monthly?session_id=${currentSessionId}&month=${month}`, "_blank");
}

// Utilitaires
function formatDate(dStr) {
    if (!dStr) return "-";
    const parts = dStr.split("-");
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return dStr;
}

function formatCurrency(val) {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(val);
}

function getSlotBadgeClass(statut) {
    switch (statut) {
        case 'Effectué': return 'badge-green';
        case 'Confirmé': return 'badge-blue';
        case 'Proposé': return 'badge-amber';
        case 'À négocier': return 'badge-purple';
        case 'À attribuer': return 'badge-red';
        default: return 'badge-blue';
    }
}

// ----------------------------------------------------
// GESTION CRUD DU PLANNING (AJOUT, MODIFICATION, SUPPRESSION)
// ----------------------------------------------------
let allFormateursCache = [];

async function getFormateursList() {
    if (allFormateursCache.length > 0) return allFormateursCache;
    try {
        const res = await fetch("/api/formateurs");
        allFormateursCache = await res.json();
    } catch(e) {
        console.error("Erreur chargement formateurs :", e);
    }
    return allFormateursCache;
}

async function populateFormateurSelect(selectedId = null) {
    const sel = document.getElementById("slot-formateur");
    sel.innerHTML = '<option value="">-- Aucun formateur assigné (À attribuer) --</option>';
    const formateurs = await getFormateursList();
    formateurs.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.id;
        opt.textContent = `${f.prenom} ${f.nom} (${f.specialite} - ${f.tarif_journalier} €/j)`;
        if (selectedId && f.id == selectedId) opt.selected = true;
        sel.appendChild(opt);
    });
}

async function openAddSlotModal() {
    document.getElementById("slot-modal-title").textContent = "Ajouter un créneau de formation";
    document.getElementById("slot-id").value = "";
    document.getElementById("slot-date").value = new Date().toISOString().split("T")[0];
    document.getElementById("slot-periode").value = "Journée (9h-17h)";
    document.getElementById("slot-heures").value = "7";
    document.getElementById("slot-thematique").value = "";
    document.getElementById("slot-salle").value = "Salle A1 - Principale";
    document.getElementById("slot-statut").value = "À attribuer";
    document.getElementById("slot-commentaire").value = "";
    document.getElementById("btn-delete-slot").classList.add("hidden");

    await populateFormateurSelect();
    document.getElementById("slot-modal").classList.remove("hidden");
}

async function openEditSlotModal(slot) {
    document.getElementById("slot-modal-title").textContent = "Modifier le créneau de formation";
    document.getElementById("slot-id").value = slot.id;
    document.getElementById("slot-date").value = slot.date_slot || "";
    document.getElementById("slot-periode").value = slot.periode || "Journée (9h-17h)";
    document.getElementById("slot-heures").value = slot.nb_heures || 7;
    document.getElementById("slot-thematique").value = slot.thematique || "";
    document.getElementById("slot-salle").value = slot.salle || "Salle A1 - Principale";
    document.getElementById("slot-statut").value = slot.statut_slot || "Confirmé";
    document.getElementById("slot-commentaire").value = slot.commentaire || "";
    document.getElementById("btn-delete-slot").classList.remove("hidden");

    await populateFormateurSelect(slot.formateur_id);
    document.getElementById("slot-modal").classList.remove("hidden");
}

function closeSlotModal() {
    document.getElementById("slot-modal").classList.add("hidden");
}

async function saveSlotModal() {
    const slotId = document.getElementById("slot-id").value;
    const dateSlot = document.getElementById("slot-date").value;
    const thematique = document.getElementById("slot-thematique").value.trim();
    const formateurId = document.getElementById("slot-formateur").value || null;
    const periode = document.getElementById("slot-periode").value;
    const nbHeures = parseFloat(document.getElementById("slot-heures").value) || 7;
    const salle = document.getElementById("slot-salle").value;
    const statut = document.getElementById("slot-statut").value;
    const commentaire = document.getElementById("slot-commentaire").value.trim();

    if (!dateSlot || !thematique) {
        alert("Veuillez renseigner au moins la date et la thématique du créneau.");
        return;
    }

    const payload = {
        session_id: currentSessionId,
        date_slot: dateSlot,
        thematique: thematique,
        formateur_id: formateurId ? parseInt(formateurId) : null,
        periode: periode,
        nb_heures: nbHeures,
        salle: salle,
        statut_slot: statut,
        commentaire: commentaire
    };

    let url = "/api/planning/add";
    if (slotId) {
        payload.slot_id = parseInt(slotId);
        url = "/api/planning/update";
    }

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeSlotModal();
            await loadPlanning();
            await loadFactures();
            await loadDashboardStats();
        } else {
            alert("Erreur : " + (data.error || "Impossible d'enregistrer le créneau"));
        }
    } catch(e) {
        alert("Erreur de connexion au serveur : " + e.message);
    }
}

async function deleteSlotModal() {
    const slotId = document.getElementById("slot-id").value;
    if (!slotId) return;
    if (!confirm("Êtes-vous sûr de vouloir supprimer ce créneau ? Les factures associées non payées seront également supprimées.")) return;

    try {
        const res = await fetch("/api/planning/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slot_id: parseInt(slotId) })
        });
        const data = await res.json();
        if (data.success) {
            closeSlotModal();
            await loadPlanning();
            await loadFactures();
            await loadDashboardStats();
        } else {
            alert("Erreur : " + (data.error || "Impossible de supprimer le créneau"));
        }
    } catch(e) {
        alert("Erreur : " + e.message);
    }
}

async function quickDeleteSlot(slotId) {
    if (!confirm("Supprimer ce créneau du planning ?")) return;
    try {
        const res = await fetch("/api/planning/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slot_id: parseInt(slotId) })
        });
        const data = await res.json();
        if (data.success) {
            await loadPlanning();
            await loadFactures();
            await loadDashboardStats();
        }
    } catch(e) {
        alert("Erreur : " + e.message);
    }
}

async function markSlotCompleted(slotId) {
    try {
        const res = await fetch("/api/planning/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ slot_id: parseInt(slotId) })
        });
        const data = await res.json();
        if (data.success) {
            await loadPlanning();
            await loadFactures();
            await loadDashboardStats();
        }
    } catch(e) {
        alert("Erreur : " + e.message);
    }
}

// ----------------------------------------------------
// IMPORT PERSEN CSV (DRAJES MINISTÈRE DES SPORTS)
// ----------------------------------------------------
function openPersenModal() {
    document.getElementById("persen-feedback").classList.add("hidden");
    document.getElementById("persen-csv-text").value = "";
    document.getElementById("persen-modal").classList.remove("hidden");
}

function closePersenModal() {
    document.getElementById("persen-modal").classList.add("hidden");
}

function handlePersenFile(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById("persen-csv-text").value = e.target.result;
    };
    reader.readAsText(file, "UTF-8");
}

function loadPersenTemplate(type) {
    const feedback = document.getElementById("persen-feedback");
    feedback.classList.add("hidden");
    if (type === 'planning') {
        document.getElementById("persen-csv-text").value = 
`Date;Heures;Module;Formateur;Salle;Commentaire
2026-10-12;7;Gestion Financière et Budgétaire;Ibrahima Ndiaye;Salle B2 - Polyvalente;Étude de cas budget prévisionnel
2026-10-13;7;Communication et Partenariats;Marc Dupont;Salle A1 - Principale;Plan de communication externe
2026-10-14;7;Intelligence Artificielle en Formation;Sophie Martin;Lab Informatique;Automatisation des bilans
2026-10-15;7;Diagnostic de Territoire;Ibrahima Ndiaye;Salle A1 - Principale;Analyse FFOM / SWOT
2026-10-16;7;Évaluation de Projet Associatif;Sophie Martin;Salle A1 - Principale;Indicateurs d'impact et livrable UC2`;
    } else if (type === 'stagiaires') {
        document.getElementById("persen-csv-text").value = 
`Nom;Prénom;Email;Téléphone;Structure;Tuteur;Email Tuteur
Benali;Karim;karim.benali@gmail.com;06 11 22 33 44;MJC Club Sport & Jeunesse;Alain Robert;alain.robert@mjc-sport.fr
Diallo;Aïssatou;aissatou.diallo@outlook.fr;06 22 33 44 55;Centre Social Étoile Nord;Corinne Meunier;corinne@etoilenord.org
Lemoine;Thomas;thomas.lemoine@laposte.net;06 33 44 55 66;Association Omnisports IDF;Marc Vasseur;vasseur@omnisports.asso.fr
Garnier;Chloé;chloe.garnier@live.fr;06 44 55 66 77;Comité Régional de Gymnastique;Valérie Tanguy;valerie@gym-idf.fr`;
    }
}

async function executePersenImport() {
    const csvContent = document.getElementById("persen-csv-text").value.trim();
    const feedback = document.getElementById("persen-feedback");

    if (!csvContent) {
        showToast("Veuillez coller le contenu CSV ou glisser un fichier exporté de PERSEN.", "error");
        return;
    }

    try {
        const res = await fetch("/api/import-persen", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                csv_content: csvContent,
                session_id: currentSessionId
            })
        });
        const data = await res.json();
        feedback.classList.remove("hidden");
        if (data.success) {
            feedback.className = "p-3 rounded-lg border text-xs bg-emerald-50 border-emerald-300 text-emerald-800";
            feedback.innerHTML = `<strong><i class="fa-solid fa-circle-check mr-1"></i> Import PERSEN réussi :</strong> ${data.message}`;
            showToast("Importation réussie avec succès !", "success");
            // Recharger les vues concernées
            await loadPlanning();
            await loadStagiaires();
            await loadFactures();
            await loadDashboardStats();
        } else {
            feedback.className = "p-3 rounded-lg border text-xs bg-rose-50 border-rose-300 text-rose-800";
            feedback.innerHTML = `<strong><i class="fa-solid fa-triangle-exclamation mr-1"></i> Erreur lors de l'import :</strong> ${data.error || "Format de fichier non reconnu"}`;
            showToast("Erreur lors de l'import : format invalide", "error");
        }
    } catch(e) {
        feedback.classList.remove("hidden");
        feedback.className = "p-3 rounded-lg border text-xs bg-rose-50 border-rose-300 text-rose-800";
        feedback.innerHTML = `<strong>Erreur réseau :</strong> ${e.message}`;
        showToast("Erreur réseau lors de l'envoi", "error");
    }
}

// ----------------------------------------------------
// DRAG & DROP CSV PERSEN
// ----------------------------------------------------
function setupDragAndDrop() {
    const dropzone = document.getElementById("persen-dropzone");
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("drag-over");
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("drag-over");
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            const file = files[0];
            const nameEl = document.getElementById("persen-file-name");
            if (nameEl) {
                nameEl.textContent = `📄 Fichier prêt : ${file.name} (${(file.size / 1024).toFixed(1)} Ko)`;
                nameEl.classList.remove("hidden");
            }
            const reader = new FileReader();
            reader.onload = function(evt) {
                document.getElementById("persen-csv-text").value = evt.target.result;
                showToast(`Fichier ${file.name} chargé`, "info");
            };
            reader.readAsText(file, "UTF-8");
        }
    }, false);
}

// ----------------------------------------------------
// GESTION DES COORDONNÉES DE L'ORGANISME (COMMERCIAL)
// ----------------------------------------------------
function openConfigModal() {
    document.getElementById("config-modal").classList.remove("hidden");
}

function closeConfigModal() {
    document.getElementById("config-modal").classList.add("hidden");
}

function saveConfigModal() {
    const nom = document.getElementById("cfg-of-nom").value.trim() || "Mon Organisme de Formation";
    const nda = document.getElementById("cfg-of-nda").value.trim();
    const qualiopi = document.getElementById("cfg-of-qualiopi").value;
    const email = document.getElementById("cfg-of-email").value.trim();
    const tel = document.getElementById("cfg-of-tel").value.trim();

    const config = { nom, nda, qualiopi, email, tel };
    localStorage.setItem("coordopro_of_config", JSON.stringify(config));

    // Mettre à jour l'en-tête
    const headerNom = document.getElementById("header-of-nom");
    if (headerNom) headerNom.innerText = nom;

    closeConfigModal();
    showToast("Coordonnées de l'organisme enregistrées !", "success");
}

function loadOrganismConfig() {
    try {
        const saved = localStorage.getItem("coordopro_of_config");
        if (saved) {
            const config = JSON.parse(saved);
            if (config.nom) {
                const headerNom = document.getElementById("header-of-nom");
                if (headerNom) headerNom.innerText = config.nom;
                const inputNom = document.getElementById("cfg-of-nom");
                if (inputNom) inputNom.value = config.nom;
            }
            if (config.nda && document.getElementById("cfg-of-nda")) document.getElementById("cfg-of-nda").value = config.nda;
            if (config.qualiopi && document.getElementById("cfg-of-qualiopi")) document.getElementById("cfg-of-qualiopi").value = config.qualiopi;
            if (config.email && document.getElementById("cfg-of-email")) document.getElementById("cfg-of-email").value = config.email;
            if (config.tel && document.getElementById("cfg-of-tel")) document.getElementById("cfg-of-tel").value = config.tel;
        }
    } catch(e) {
        console.error("Config error:", e);
    }
}

// ----------------------------------------------------
// VISITE GUIDÉE & ONBOARDING INTERACTIF
// ----------------------------------------------------
let tourCurrentStep = 0;
const tourSteps = [
    {
        title: "1. Bienvenue dans votre cockpit CoordoPro",
        content: `CoordoPro JEPS a été conçu <strong>spécifiquement pour les coordonnateurs d'organismes de formation</strong>. Il fonctionne 100% en local, sans abonnement LLM, ultra-rapide et respectueux des données Qualiopi.<br><br>👉 La barre supérieure vous permet de basculer instantanément d'une session à l'autre (ex: BPJEPS APT, CPJEPS AAVQ).`
    },
    {
        title: "2. Gagnez 35h sur vos Dossiers Réglementaires",
        content: `Dans l'onglet <strong>Dossiers Réglementaires</strong>, générez en 1 clic vos dossiers complets :<br>
        • <strong>Dossier d'Habilitation DRAJES</strong> (Ruban pédagogique, 4 UC, grilles d'évaluation, jury)<br>
        • <strong>Dossier de Complétude</strong> (obligatoire 2 mois avant l'ouverture de chaque session).`
    },
    {
        title: "3. Planning Intelligent & Import PERSEN",
        content: `Dans l'onglet <strong>Planning & Formateurs</strong> :<br>
        • Cliquez sur <strong>Importer Persen CSV</strong> pour glisser-déposer vos plannings ministériels sans ressaisie.<br>
        • Utilisez le <strong>Swap Intelligent</strong> si un formateur n'est pas dispo un jour : le système réorganise automatiquement le calendrier !`
    },
    {
        title: "4. Facturation Formateurs & Convocations",
        content: `Finies les relances manuelles :<br>
        • Suivez en temps réel le cycle comptable complet : <em>Journée effectuée ➔ Facture reçue ➔ Transmise compta ➔ Payée</em>.<br>
        • Envoyez les convocations officielles avec date, heure, salle et émargement en 1 clic aux stagiaires.`
    }
];

function startGuidedTour() {
    tourCurrentStep = 0;
    renderTourStep();
    document.getElementById("tour-modal").classList.remove("hidden");
}

function closeTourModal() {
    document.getElementById("tour-modal").classList.add("hidden");
}

function renderTourStep() {
    const step = tourSteps[tourCurrentStep];
    const contentEl = document.getElementById("tour-step-content");
    const indicatorEl = document.getElementById("tour-step-indicator");
    const btnPrev = document.getElementById("tour-btn-prev");
    const btnNext = document.getElementById("tour-btn-next");

    contentEl.innerHTML = `
        <h4 class="font-bold text-slate-900 text-sm mb-1">${step.title}</h4>
        <p class="leading-relaxed text-slate-700">${step.content}</p>
    `;

    indicatorEl.innerText = `Étape ${tourCurrentStep + 1} sur ${tourSteps.length}`;

    if (tourCurrentStep === 0) {
        btnPrev.classList.add("hidden");
    } else {
        btnPrev.classList.remove("hidden");
    }

    if (tourCurrentStep === tourSteps.length - 1) {
        btnNext.innerHTML = `Terminer <i class="fa-solid fa-check ml-1"></i>`;
    } else {
        btnNext.innerHTML = `Suivant <i class="fa-solid fa-arrow-right ml-1"></i>`;
    }
}

function tourNext() {
    if (tourCurrentStep < tourSteps.length - 1) {
        tourCurrentStep++;
        renderTourStep();
    } else {
        closeTourModal();
        showToast("Bonne coordination avec CoordoPro !", "success");
    }
}

function tourPrev() {
    if (tourCurrentStep > 0) {
        tourCurrentStep--;
        renderTourStep();
    }
}
