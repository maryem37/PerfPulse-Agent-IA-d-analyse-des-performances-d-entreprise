// ──────────────────────────────────────────────────────────
// PerfPulse AI - Dashboard Application Logic
// ──────────────────────────────────────────────────────────

const AGENTS = [
  { id: 'extract', name: 'Extract', desc: 'Lecture du modèle PBIX et extraction des 9 tables' },
  { id: 'kpi', name: 'Calcul KPI', desc: 'Calcul CA, Marge, Évolution temporelle' },
  { id: 'detect', name: 'Détection', desc: 'Détection statistique des anomalies (Z-Score)' },
  { id: 'analyse', name: 'Analyse', desc: 'Décomposition des causes racines par dimension' },
  { id: 'write', name: 'Rédaction IA', desc: 'Génération des commentaires d\'analyse avec Groq' },
  { id: 'validate', name: 'Validation', desc: 'Contrôle anti-hallucination & conformité' },
  { id: 'report', name: 'Rapports', desc: 'Production des rapports HTML & exports CSV' },
];

let globalData = null;
let chartCA = null;
let chartMarge = null;
let chartSeverity = null;
let chartKpiBar = null;

// ──────────────────────────────────────────────────────────
// Initialization
// ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  renderStepper();
  checkStatus();
  setupUploadZone();
  setupFilters();
  setupTrendFilters();
  setupSectionNavigation();

  document.getElementById('btn-run').addEventListener('click', startPipeline);
  document.getElementById('btn-reset').addEventListener('click', resetPipeline);
  document.getElementById('btn-refresh').addEventListener('click', refreshDashboard);
});

async function refreshDashboard() {
  const button = document.getElementById('btn-refresh');
  button.disabled = true;
  button.textContent = 'Actualisation…';
  try {
    const statusResponse = await fetch('/api/status', { cache: 'no-store' });
    const status = await statusResponse.json();
    if (status.pbix && status.pbix.name) {
      document.getElementById('current-pbix-name').textContent = status.pbix.name;
      document.getElementById('current-pbix-size').textContent = `${status.pbix.size_mb} Mo`;
      document.getElementById('badge-pbix-name').textContent = status.pbix.name;
    }
    if (!status.has_results) {
      clearDashboardResults();
      document.getElementById('live-log-text').textContent = 'Aucun résultat de pipeline disponible.';
      return;
    }
    const dataResponse = await fetch('/api/data', { cache: 'no-store' });
    const data = await dataResponse.json();
    if (data && data.ready) {
      globalData = data;
      renderAll(data);
      document.getElementById('live-log-text').textContent = 'Résultats actualisés.';
    }
  } catch (error) {
    console.error('Erreur actualisation:', error);
    document.getElementById('live-log-text').textContent = 'Impossible d’actualiser les résultats.';
  } finally {
    button.disabled = false;
    button.textContent = '↻ Actualiser';
  }
}

function setupTrendFilters() {
  ['filter-kpi', 'filter-date-start', 'filter-date-end'].forEach(id => {
    document.getElementById(id).addEventListener('change', event => {
      const start = document.getElementById('filter-date-start');
      const end = document.getElementById('filter-date-end');
      if (start.value && end.value && start.value > end.value) {
        if (event.target.id === 'filter-date-start') end.value = start.value;
        else start.value = end.value;
      }
      if (globalData) renderCharts(globalData);
    });
  });
}

function initializeTrendFilters(series) {
  if (!series || !series.length) return;
  const months = series.map(item => item.mois).sort();
  const start = document.getElementById('filter-date-start');
  const end = document.getElementById('filter-date-end');
  start.min = end.min = months[0];
  start.max = end.max = months[months.length - 1];
  if (!start.value || start.value < start.min || start.value > start.max) start.value = start.min;
  if (!end.value || end.value < end.min || end.value > end.max) end.value = end.max;
}

function setupSectionNavigation() {
  const links = [...document.querySelectorAll('.side-link')];
  const targets = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
  const markActive = id => links.forEach(link => {
    link.classList.toggle('active', link.getAttribute('href') === `#${id}`);
  });
  links.forEach(link => link.addEventListener('click', () => markActive(link.getAttribute('href').slice(1))));
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) markActive(visible.target.id);
    }, { rootMargin: '-20% 0px -65% 0px', threshold: [0, 0.2, 0.5] });
    targets.forEach(target => observer.observe(target));
  }
}

function clearDashboardResults() {
  globalData = null;
  [chartCA, chartMarge, chartSeverity, chartKpiBar].forEach(chart => {
    if (chart) chart.destroy();
  });
  chartCA = chartMarge = chartSeverity = chartKpiBar = null;
  ['stat-ca', 'stat-marge', 'stat-alertes', 'stat-val'].forEach(id => {
    document.getElementById(id).textContent = '—';
  });
  ['stat-ca-sub', 'stat-marge-sub', 'stat-alertes-sub', 'stat-val-sub'].forEach(id => {
    document.getElementById(id).textContent = 'En attente de la nouvelle exécution.';
  });
  document.getElementById('synthesis-content').innerHTML = '<p>Aucune synthèse disponible. Exécutez l’analyse.</p>';
  document.getElementById('analyses-container').innerHTML = '<p>Aucune analyse disponible.</p>';
  document.getElementById('table-body').innerHTML = '<tr><td colspan="7" style="text-align:center">Aucune alerte trouvée</td></tr>';
  document.getElementById('progress-fill').style.width = '0%';
}

async function resetPipeline() {
  const button = document.getElementById('btn-reset');
  button.disabled = true;
  try {
    const response = await fetch('/api/reset', { method: 'POST' });
    if (!response.ok) throw new Error('La réinitialisation a échoué.');
    clearDashboardResults();
    AGENTS.forEach(agent => setStepState(agent.id, '', 'En attente'));
    document.getElementById('live-log-text').textContent = 'Pipeline réinitialisé. Aucune ancienne donnée affichée.';
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
  }
}

// Render the 7 agent step cards
function renderStepper() {
  const container = document.getElementById('stepper-cards');
  container.innerHTML = AGENTS.map((a, idx) => `
    <div class="step-card" id="step-${a.id}">
      <div class="step-num">${idx + 1}</div>
      <div class="step-name">${a.name}</div>
      <div class="step-desc">${a.desc}</div>
      <div class="step-msg" id="msg-${a.id}">En attente</div>
    </div>
  `).join('');
}

// Check backend status & load previous data if present
async function checkStatus() {
  try {
    const res = await fetch('/api/status', { cache: 'no-store' });
    const data = await res.json();

    if (data.pbix && data.pbix.name) {
      document.getElementById('current-pbix-name').textContent = data.pbix.name;
      document.getElementById('current-pbix-size').textContent = `${data.pbix.size_mb} Mo`;
      document.getElementById('badge-pbix-name').textContent = data.pbix.name;
    }

    if (data.has_results) {
      loadExistingData();
    }
  } catch (err) {
    console.warn('Erreur vérification statut:', err);
  }
}

// Load existing results from backend
async function loadExistingData() {
  try {
    const res = await fetch('/api/data', { cache: 'no-store' });
    const data = await res.json();
    if (data && data.ready) {
      globalData = data;
      renderAll(data);
      // Marquer toutes les étapes comme terminées
      AGENTS.forEach(a => {
        const card = document.getElementById(`step-${a.id}`);
        const msg = document.getElementById(`msg-${a.id}`);
        if (card) { card.className = 'step-card done'; }
        if (msg) { msg.textContent = 'Terminé'; }
      });
      document.getElementById('progress-fill').style.width = '100%';
      document.getElementById('live-log-text').textContent = 'Résultats chargés depuis la dernière exécution.';
      document.getElementById('live-spinner').style.display = 'none';
    }
  } catch (err) {
    console.error('Erreur chargement données:', err);
  }
}

// ──────────────────────────────────────────────────────────
// File Upload
// ──────────────────────────────────────────────────────────

function setupUploadZone() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');

  dropzone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileUpload(files[0]);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFileUpload(fileInput.files[0]);
  });
}

async function handleFileUpload(file) {
  if (!file.name.endsWith('.pbix')) {
    alert('Veuillez sélectionner un fichier Power BI (.pbix)');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  document.getElementById('live-log-text').textContent = `Import de ${file.name} en cours...`;
  document.getElementById('live-spinner').style.display = 'inline-block';

  try {
    const res = await fetch('/api/upload-pbix', {
      method: 'POST',
      body: formData,
    });
    const result = await res.json();

    if (result.success) {
      document.getElementById('current-pbix-name').textContent = result.name;
      document.getElementById('current-pbix-size').textContent = `${result.size_mb} Mo`;
      document.getElementById('badge-pbix-name').textContent = result.name;
      document.getElementById('live-log-text').textContent = `Fichier ${result.name} importé avec succès (${result.tables_count} tables détectées). Prêt à exécuter !`;
      document.getElementById('live-spinner').style.display = 'none';
      alert(`Fichier ${result.name} importé avec succès ! Cliquez sur "Lancer l'analyse" pour démarrer les agents.`);
    } else {
      alert(`Erreur d'import : ${result.error}`);
    }
  } catch (err) {
    alert(`Erreur réseau : ${err.message}`);
  }
}

// ──────────────────────────────────────────────────────────
// Pipeline Execution with SSE Stream
// ──────────────────────────────────────────────────────────

function startPipeline() {
  clearDashboardResults();
  const btn = document.getElementById('btn-run');
  btn.disabled = true;
  btn.innerHTML = `<span class="live-spinner" style="margin-right:6px"></span> Exécution...`;

  // Reset stepper cards
  AGENTS.forEach(a => {
    const card = document.getElementById(`step-${a.id}`);
    const msg = document.getElementById(`msg-${a.id}`);
    if (card) card.className = 'step-card';
    if (msg) msg.textContent = 'En attente';
  });

  const progressFill = document.getElementById('progress-fill');
  progressFill.style.width = '5%';
  document.getElementById('live-spinner').style.display = 'inline-block';
  document.getElementById('live-log-text').textContent = 'Initialisation du pipeline d\'agents...';

  // Mark first step active
  setStepState('extract', 'active', 'En cours...');

  // Start Server-Sent Events
  const evtSource = new EventSource('/api/run-stream');

  evtSource.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    if (msg.event === 'agent_start') {
      setStepState(msg.agent, 'active', msg.message);
      document.getElementById('live-log-text').textContent = msg.message;
      updateProgressByAgent(msg.agent, 0.4);
    }
    else if (msg.event === 'agent_complete') {
      setStepState(msg.agent, 'done', msg.message);
      document.getElementById('live-log-text').textContent = msg.message;
      updateProgressByAgent(msg.agent, 1.0);

      // Make next agent active
      const nextAgent = getNextAgent(msg.agent);
      if (nextAgent) {
        setStepState(nextAgent.id, 'active', 'En cours d\'exécution...');
      }
    }
    else if (msg.event === 'error') {
      alert(`Erreur pendant l'exécution : ${msg.message}`);
      evtSource.close();
      btn.disabled = false;
      btn.innerHTML = `🚀 Relancer l'analyse`;
      document.getElementById('live-spinner').style.display = 'none';
    }
    else if (msg.event === 'complete') {
      evtSource.close();
      progressFill.style.width = '100%';
      document.getElementById('live-spinner').style.display = 'none';
      document.getElementById('live-log-text').textContent = 'Analyse terminée avec succès ! Tous les agents ont validé le modèle.';
      btn.disabled = false;
      btn.innerHTML = `🚀 Relancer l'analyse`;

      if (msg.data && msg.data.ready) {
        globalData = msg.data;
        renderAll(msg.data);
      }
    }
  };

  evtSource.onerror = (err) => {
    console.error('SSE Error:', err);
    evtSource.close();
    btn.disabled = false;
    btn.innerHTML = `🚀 Relancer l'analyse`;
    document.getElementById('live-spinner').style.display = 'none';
  };
}

function setStepState(agentId, state, text) {
  const card = document.getElementById(`step-${agentId}`);
  const msg = document.getElementById(`msg-${agentId}`);
  if (card) {
    card.className = `step-card ${state}`;
  }
  if (msg) {
    msg.textContent = text;
  }
}

function getNextAgent(currentId) {
  const idx = AGENTS.findIndex(a => a.id === currentId);
  if (idx >= 0 && idx < AGENTS.length - 1) {
    return AGENTS[idx + 1];
  }
  return null;
}

function updateProgressByAgent(agentId, factor) {
  const idx = AGENTS.findIndex(a => a.id === agentId);
  if (idx >= 0) {
    const pct = Math.round(((idx + factor) / AGENTS.length) * 100);
    document.getElementById('progress-fill').style.width = `${pct}%`;
  }
}

// ──────────────────────────────────────────────────────────
// Render Results (Stats, Charts, Synthesis, Analyses, Table)
// ──────────────────────────────────────────────────────────

function renderAll(data) {
  renderStats(data.stats);
  renderSynthesis(data.synthese, data.stats);
  renderCharts(data);
  renderMonthlyAnalyses(data.analyses);
  renderAlertsTable(data.alertes);
}

// 1. KPI Stats Cards
function renderStats(stats) {
  if (!stats) return;
  document.getElementById('stat-ca').textContent = `${(stats.total_ca / 1000000).toFixed(2)} M€`;
  document.getElementById('stat-ca-sub').textContent = `Sur ${stats.nb_mois} mois analysés`;

  document.getElementById('stat-marge').textContent = `${stats.avg_marge_pct.toFixed(1)} %`;
  document.getElementById('stat-marge-sub').textContent = `Marge totale : ${(stats.total_marge / 1000000).toFixed(2)} M€`;

  document.getElementById('stat-alertes').textContent = stats.nb_alertes;
  document.getElementById('stat-alertes-sub').textContent = `${stats.nb_haute} haute(s), ${stats.nb_moyenne} moyenne(s)`;

  document.getElementById('stat-val').textContent = stats.validation_ok ? 'OK' : 'À revoir';
  document.getElementById('stat-val-sub').textContent = 'Chiffres des commentaires comparés aux faits calculés';
}

// 2. Executive Synthesis Card
function renderSynthesis(synthese, stats) {
  const container = document.getElementById('synthesis-content');
  if (synthese) {
    container.innerHTML = `
      <div class="synthesis-badge">
        <span class="pulse-dot"></span> Synthèse Analytique IA Certifiée
      </div>
      <div class="synthesis-text">${synthese}</div>
    `;
  } else {
    container.innerHTML = `<p style="color:var(--text-muted);font-size:14px">Aucune synthèse disponible. Exécutez l'analyse.</p>`;
  }
}

// 3. Interactive Charts (Chart.js)
function renderCharts(data) {
  const series = data.kpi_series || [];
  if (series.length === 0) return;

  initializeTrendFilters(series);
  const selectedMetric = document.getElementById('filter-kpi').value;
  const startMonth = document.getElementById('filter-date-start').value;
  const endMonth = document.getElementById('filter-date-end').value;
  const filteredSeries = series.filter(item => item.mois >= startMonth && item.mois <= endMonth);
  const metricConfig = {
    ca: { key: 'ca', title: "Évolution du chiffre d'affaires", unit: '€', color: '#4263eb' },
    marge: { key: 'marge', title: 'Évolution de la marge', unit: '€', color: '#16a7a1' },
    marge_pct: { key: 'marge_pct', title: 'Évolution du taux de marge', unit: '%', color: '#16a7a1' },
    quantite: { key: 'quantite', title: 'Évolution des quantités', unit: 'unités', color: '#4263eb' },
    panier: { key: 'panier', title: 'Évolution du panier moyen', unit: '€', color: '#4263eb' },
    part_promo: { key: 'part_promo', title: 'Évolution de la part en promotion', unit: '%', color: '#16a7a1' },
  };
  const config = metricConfig[selectedMetric] || metricConfig.ca;
  const labels = filteredSeries.map(s => s.mois);
  const primaryValues = filteredSeries.map(s => s[config.key]);
  const margePctValues = filteredSeries.map(s => s.marge_pct);
  const filteredAlerts = (data.alertes || []).filter(alert =>
    alert.AnneeMois >= startMonth && alert.AnneeMois <= endMonth
  );
  document.getElementById('chart-primary-title').textContent = config.title;

  // Couleurs conditionnelles pour les points d'alertes
  const pointColors = filteredSeries.map(s => {
    if (s.severite === 'haute') return '#e35d6a';
    if (s.severite === 'moyenne') return '#dc9a31';
    return config.color;
  });

  const pointRadius = filteredSeries.map(s => (s.is_alert ? 6 : 3));
  const pointHoverRadius = filteredSeries.map(s => (s.is_alert ? 9 : 5));

  // ── Chart 1 : Courbe d'Évolution Temporelle du CA ──
  const ctxCA = document.getElementById('chart-ca').getContext('2d');
  if (chartCA) chartCA.destroy();

  const gradientCA = ctxCA.createLinearGradient(0, 0, 0, 300);
  gradientCA.addColorStop(0, 'rgba(66, 99, 235, 0.18)');
  gradientCA.addColorStop(1, 'rgba(66, 99, 235, 0.0)');

  chartCA = new Chart(ctxCA, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: config.title,
        data: primaryValues,
        borderColor: config.color,
        borderWidth: 2.5,
        backgroundColor: gradientCA,
        fill: true,
        tension: 0.3,
        pointBackgroundColor: pointColors,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointRadius: pointRadius,
        pointHoverRadius: pointHoverRadius,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleFont: { size: 13, weight: 'bold' },
          bodyFont: { size: 12 },
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function(context) {
              const item = filteredSeries[context.dataIndex];
              const formatted = config.unit === '€'
                ? new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(context.raw)
                : `${Number(context.raw).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} ${config.unit}`;
              let lines = [`${config.title.replace('Évolution ', '')} : ${formatted}`];
              if (item.is_alert) {
                lines.push(`🚨 ALERTE ${item.severite.toUpperCase()} (${item.alert_count} anomalie(s))`);
                item.alertes.forEach(a => {
                  lines.push(`  • ${a.KPI}: Z=${a.ZScore} (${(a.Ecart_pct * 100).toFixed(1)}%)`);
                });
              }
              return lines;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { size: 11 } }
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: {
            color: '#64748b',
            font: { size: 11 },
          callback: value => {
            if (config.unit === '€') return `${(value / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} k€`;
            return `${Number(value).toLocaleString('fr-FR', { maximumFractionDigits: 1 })}${config.unit === '%' ? ' %' : ''}`;
          }
          }
        }
      }
    }
  });

  // ── Chart 2 : Courbe du Taux de Marge (%) ──
  const ctxMarge = document.getElementById('chart-marge').getContext('2d');
  if (chartMarge) chartMarge.destroy();

  const gradientMarge = ctxMarge.createLinearGradient(0, 0, 0, 300);
  gradientMarge.addColorStop(0, 'rgba(22, 167, 161, 0.20)');
  gradientMarge.addColorStop(1, 'rgba(22, 167, 161, 0.0)');

  chartMarge = new Chart(ctxMarge, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Taux de Marge (%)',
        data: margePctValues,
        borderColor: '#16a7a1',
        borderWidth: 2.5,
        backgroundColor: gradientMarge,
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#16a7a1',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          callbacks: {
            label: context => `Taux de Marge : ${context.raw ? context.raw.toFixed(1) : 0} %`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { size: 11 } }
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: {
            color: '#64748b',
            font: { size: 11 },
            callback: value => `${value} %`
          }
        }
      }
    }
  });

  // ── Chart 3 : Donut Répartition Sévérité ──
  const ctxSeverity = document.getElementById('chart-severity').getContext('2d');
  if (chartSeverity) chartSeverity.destroy();

  const nbHaute = filteredAlerts.filter(alert => alert.Severite === 'haute').length;
  const nbMoyenne = filteredAlerts.filter(alert => alert.Severite === 'moyenne').length;

  chartSeverity = new Chart(ctxSeverity, {
    type: 'doughnut',
    data: {
      labels: ['Sévérité Haute', 'Sévérité Moyenne'],
      datasets: [{
        data: [nbHaute, nbMoyenne],
        backgroundColor: ['#e35d6a', '#dc9a31'],
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#334155', font: { size: 12, weight: 'bold' } }
        }
      },
      cutout: '70%',
    }
  });

  // ── Chart 4 : Barres Alertes par KPI ──
  const ctxKpi = document.getElementById('chart-kpi-bar').getContext('2d');
  if (chartKpiBar) chartKpiBar.destroy();

  const kpiCounts = {};
  filteredAlerts.forEach(a => {
    kpiCounts[a.KPI] = (kpiCounts[a.KPI] || 0) + 1;
  });

  chartKpiBar = new Chart(ctxKpi, {
    type: 'bar',
    data: {
      labels: Object.keys(kpiCounts),
      datasets: [{
        label: 'Nombre d\'alertes',
        data: Object.values(kpiCounts),
        backgroundColor: '#4263eb',
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#64748b' } },
        y: { grid: { color: '#f1f5f9' }, ticks: { stepSize: 1, color: '#64748b' } }
      }
    }
  });
}

// 4. Monthly Analyses Accordion
function renderMonthlyAnalyses(analyses) {
  const container = document.getElementById('analyses-container');
  if (!analyses || analyses.length === 0) {
    container.innerHTML = `<p style="color:var(--text-muted);font-size:14px">Aucune analyse disponible.</p>`;
    return;
  }

  container.innerHTML = analyses.map((m, idx) => {
    const maxSev = m.alertes.some(a => a.Severite === 'haute') ? 'haute' : 'moyenne';
    const badgeClass = maxSev === 'haute' ? 'badge-haute' : 'badge-moyenne';
    const isFirst = idx === 0 ? 'open' : '';

    const formatEcart = value => `${Number(value).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} €`;
    const causesP = (m.causes.produits || []).slice(0, 3).map(p => `<li><strong>${p.nom}</strong> : écart ${formatEcart(p.ecart)}</li>`).join('') || '<li>Aucune donnée produit disponible</li>';
    const causesT = (m.causes.territoires || []).slice(0, 3).map(t => `<li><strong>${t.nom}</strong> : écart ${formatEcart(t.ecart)}</li>`).join('') || '<li>Aucune donnée régionale disponible</li>';
    const causesR = '<li>Analyse des revendeurs non calculée</li>';
    const metricLabels = { CA: 'CA', Marge: 'marge (€)', Quantite: 'quantité', CA_Promo: 'CA promotionnel' };
    const dimensionNote = `Classement selon ${metricLabels[m.causes.metrique] || m.causes.metrique || 'la métrique calculée'} ; association observée, pas preuve de causalité.`;

    return `
      <div class="month-item">
        <div class="month-header ${isFirst}" onclick="toggleAccordion(this)">
          <div class="month-title-group">
            <span class="month-name">📅 Mois : ${m.mois}</span>
            <span class="badge ${badgeClass}">${maxSev.toUpperCase()}</span>
            <span class="badge badge-ok">✓ VALIDÉ</span>
          </div>
          <span style="font-size:13px;color:var(--text-muted)">${m.alertes.length} alerte(s) ▼</span>
        </div>
        <div class="month-body ${isFirst}">
          <div class="month-text-box">
            <strong>💬 Diagnostic de l'IA (Groq Llama 3.3) :</strong><br>
            ${m.texte}
          </div>
          <div class="causes-grid">
            <div class="cause-box">
              <h5>📦 Produits avec écart</h5>
              <ul class="cause-list">${causesP}</ul>
            </div>
            <div class="cause-box">
              <h5>🌍 Régions avec écart</h5>
              <ul class="cause-list">${causesT}</ul>
            </div>
            <div class="cause-box">
              <h5>🏢 Revendeurs</h5>
              <ul class="cause-list">${causesR}</ul>
            </div>
          </div>
          <p style="margin-top:12px;color:var(--text-muted);font-size:12px">${dimensionNote}</p>
        </div>
      </div>
    `;
  }).join('');
}

function toggleAccordion(header) {
  header.classList.toggle('open');
  const body = header.nextElementSibling;
  body.classList.toggle('open');
}

// 5. Interactive Table & Search / Filter
function formatAlertValue(alert, value) {
  const number = Number(value);
  if (alert.KPI === 'MargePct' || alert.KPI === 'PartPromo') {
    return `${(number * 100).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} %`;
  }
  return number.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
}

function renderAlertsTable(alertes) {
  const tbody = document.getElementById('table-body');
  if (!alertes || alertes.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:var(--text-muted)">Aucune alerte trouvée</td></tr>`;
    return;
  }

  tbody.innerHTML = alertes.map(a => {
    const sevClass = a.Severite === 'haute' ? 'badge-haute' : 'badge-moyenne';
    const ecartPct = a.Ecart_pct !== null && a.Ecart_pct !== undefined ? `${(a.Ecart_pct * 100).toFixed(1)} %` : '—';
    const ecartAn = a.Ecart_annee_prec !== null && a.Ecart_annee_prec !== undefined ? `${(a.Ecart_annee_prec * 100).toFixed(1)} %` : '—';

    return `
      <tr data-severite="${a.Severite}">
        <td><strong>${a.AnneeMois}</strong></td>
        <td><span style="font-weight:600;color:var(--primary)">${a.KPI}</span></td>
        <td>${formatAlertValue(a, a.Valeur)}</td>
        <td>${formatAlertValue(a, a.Moyenne_ref)}</td>
        <td><strong>${Number(a.ZScore).toFixed(2)}</strong></td>
        <td style="color:${a.Ecart_pct < 0 ? '#e35d6a' : '#23876e'}">${ecartPct}</td>
        <td><span class="badge ${sevClass}">${a.Severite}</span></td>
      </tr>
    `;
  }).join('');
}

function setupFilters() {
  const searchInput = document.getElementById('search-input');
  const pills = document.querySelectorAll('.filter-pill');

  let activeFilter = 'all';

  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      activeFilter = pill.getAttribute('data-filter');
      applyTableFilter();
    });
  });

  searchInput.addEventListener('input', applyTableFilter);

  function applyTableFilter() {
    const term = searchInput.value.toLowerCase();
    const rows = document.querySelectorAll('#table-body tr');

    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      const sev = row.getAttribute('data-severite');
      const matchesSearch = text.includes(term);
      const matchesSev = activeFilter === 'all' || sev === activeFilter;

      row.style.display = (matchesSearch && matchesSev) ? '' : 'none';
    });
  }
}
