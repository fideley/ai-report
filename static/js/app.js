// Configuration globale
const API_BASE_URL = 'http://localhost:8000'; // Ajustez selon votre configuration
const UPDATE_INTERVAL = 3000; // 3 secondes

// Variables globales pour les graphiques
let charts = {};
let chartData = {
    labels: [],
    power: { p1: [], p2: [], total: [] },
    voltage: { u1: [], u2: [] },
    current: { i1: [], i2: [], lamp1: [], lamp2: [] },
    lampPower: { lamp1: [], lamp2: [] },
    energy: { s1: [], s2: [], total: [] },
    status: { s1: [], s2: [], lamp1: [], lamp2: [] }
};

// Variable pour le graphique d'énergie journalière
let dailyEnergyChart = null;

// Pagination pour l'historique
let historyCurrentPage = 0;
const historyItemsPerPage = 20;

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    
    // Initialiser les graphiques
    initializeCharts();
    
    // Charger les données initiales
    loadLatestData();
    loadSystemStats();
    loadHistory();
    loadLogs();
    
    // Démarrer les mises à jour automatiques
    setInterval(loadLatestData, UPDATE_INTERVAL);
    setInterval(updateCharts, UPDATE_INTERVAL);
    
    // Event listeners pour les onglets
    document.getElementById('charts-tab').addEventListener('shown.bs.tab', function () {
        // Redimensionner les graphiques quand l'onglet devient visible
        Object.values(charts).forEach(chart => chart.resize());
    });
    
    // Initialiser la date d'aujourd'hui pour le graphique d'énergie journalière
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('dailyEnergyDate').value = today;
    
    // Charger automatiquement le graphique pour aujourd'hui après un délai
    setTimeout(() => {
        loadDailyEnergyChart();
    }, 2000);
});

// Fonction pour afficher les messages d'erreur
function showError(message, containerId = null) {
    const errorHtml = `<div class="error-message"><i class="fas fa-exclamation-triangle me-2"></i>${message}</div>`;
    
    if (containerId) {
        document.getElementById(containerId).innerHTML = errorHtml;
    } else {
        console.error(message);
    }
    
    // Mettre à jour le statut de connexion
    updateConnectionStatus(false);
}

// Mettre à jour le statut de connexion
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connectionStatus');
    if (connected) {
        statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Connecté';
        statusElement.className = 'badge bg-success me-3';
    } else {
        statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Déconnecté';
        statusElement.className = 'badge bg-danger me-3';
    }
}

// Charger les dernières données
async function loadLatestData() {
  try {
      const response = await fetch(`${API_BASE_URL}/data/latest`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      
      // Debug des données reçues
      debugReceivedData(data);
      
      updateDashboard(data);
      addToChartData(data);
      updateConnectionStatus(true);
      
      // Mettre à jour le timestamp
      document.getElementById('lastUpdate').textContent = 
          `Dernière MAJ: ${new Date().toLocaleTimeString()}`;
      
  } catch (error) {
      console.error('Erreur lors du chargement des données:', error);
      showError(`Erreur de connexion à l'API: ${error.message}`);
  }
}

// Mettre à jour le dashboard avec les dernières données
function updateDashboard(data) {
  console.log('Données reçues:', data); // Debug
  
  // Source 1 - Nettoyage des espaces
  const etatS1Clean = data.etatS1 ? data.etatS1.trim() : 'OFF';
  const etatS2Clean = data.etatS2 ? data.etatS2.trim() : 'OFF';
  
  updateSourceStatus('source1Status', etatS1Clean, '1');
  document.getElementById('u1Value').textContent = `${data.U1?.toFixed(1) || '--'} V`;
  document.getElementById('i1Value').textContent = `${data.I1?.toFixed(2) || '--'} A`;
  document.getElementById('p1Value').textContent = `${data.P1?.toFixed(0) || '--'} W`;

  // Source 2
  updateSourceStatus('source2Status', etatS2Clean, '2');
  document.getElementById('u2Value').textContent = `${data.U2?.toFixed(1) || '--'} V`;
  document.getElementById('i2Value').textContent = `${data.I2?.toFixed(2) || '--'} A`;
  document.getElementById('p2Value').textContent = `${data.P2?.toFixed(0) || '--'} W`;

  // Lampes - Nettoyage des espaces
  const etatLamp1Clean = data.etatLamp1 ? data.etatLamp1.trim() : 'OFF';
  const etatLamp2Clean = data.etatLamp2 ? data.etatLamp2.trim() : 'OFF';
  
  updateLampStatus('lamp1Status', 'lamp1State', etatLamp1Clean);
  updateLampStatus('lamp2Status', 'lamp2State', etatLamp2Clean);
  document.getElementById('powerLamp1Value').textContent = `${data.powerLamp1?.toFixed(0) || '--'} W`;
  document.getElementById('powerLamp2Value').textContent = `${data.powerLamp2?.toFixed(0) || '--'} W`;

  // Énergie
  const sourceActive = data.sourceActive ? data.sourceActive.trim() : '--';
  document.getElementById('activeSource').textContent = sourceActive;
  document.getElementById('energyS1Value').textContent = `${data.savedEnergyS1?.toFixed(3) || '--'} kWh`;
  document.getElementById('energyS2Value').textContent = `${data.savedEnergyS2?.toFixed(3) || '--'} kWh`;
  document.getElementById('energyTotalValue').textContent = `${data.savedEnergyT?.toFixed(3) || '--'} kWh`;

  // État système
  document.getElementById('systemActiveSource').textContent = sourceActive;
  const chargeActive = data.chargeActive ? data.chargeActive.trim() : '--';
  document.getElementById('systemActiveCharge').textContent = chargeActive;
  
  const totalPower = (data.P1 || 0) + (data.P2 || 0);
  document.getElementById('systemTotalPower').textContent = `${totalPower.toFixed(0)} W`;
  
  // Debug console
  console.log(`États mis à jour: S1=${etatS1Clean}, S2=${etatS2Clean}, L1=${etatLamp1Clean}, L2=${etatLamp2Clean}`);
  document.getElementById('lamp1CurrentState').textContent = etatLamp1Clean;
  document.getElementById('lamp2CurrentState').textContent = etatLamp2Clean;
}


// Mettre à jour le statut d'une source
function updateSourceStatus(elementId, etat, sourceNum) {
  const element = document.getElementById(elementId);
  const indicator = element.querySelector('.status-indicator');
  const text = element.querySelector('span:last-child');
  
  console.log(`Mise à jour Source ${sourceNum}: état = "${etat}"`); // Debug
  
  if (etat === 'ON' || etat === 'ON ') { // Gérer les espaces en fin
      indicator.className = 'status-indicator status-on';
      text.textContent = `SOURCE ${sourceNum} ON`;
      text.className = 'text-success fw-bold';
  } else {
      indicator.className = 'status-indicator status-off';
      text.textContent = `SOURCE ${sourceNum} OFF`;
      text.className = 'text-muted';
  }
}

// Mettre à jour le statut d'une lampe
function updateLampStatus(statusElementId, stateElementId, etat) {
  const statusElement = document.getElementById(statusElementId);
  const stateElement = document.getElementById(stateElementId);
  const indicator = statusElement.querySelector('.status-indicator');
  
  const etatClean = etat ? etat.trim() : 'OFF';
  
  if (etatClean === 'ON') {
      indicator.className = 'status-indicator status-on';
      stateElement.textContent = 'ON';
      stateElement.className = 'text-success fw-bold';
  } else {
      indicator.className = 'status-indicator status-off';
      stateElement.textContent = 'OFF';
      stateElement.className = 'text-muted';
  }
}

// Fonction de debug pour vérifier les données reçues
function debugReceivedData(data) {
console.group('🔍 DEBUG - Données reçues');
console.log('Raw data:', data);
console.log('États bruts:');
console.log(`  etatS1: "${data.etatS1}" (length: ${data.etatS1?.length})`);
console.log(`  etatS2: "${data.etatS2}" (length: ${data.etatS2?.length})`);
console.log(`  etatLamp1: "${data.etatLamp1}" (length: ${data.etatLamp1?.length})`);
console.log(`  etatLamp2: "${data.etatLamp2}" (length: ${data.etatLamp2?.length})`);
console.log('États nettoyés:');
console.log(`  etatS1: "${data.etatS1?.trim()}"`);
console.log(`  etatS2: "${data.etatS2?.trim()}"`);
console.log(`  etatLamp1: "${data.etatLamp1?.trim()}"`);
console.log(`  etatLamp2: "${data.etatLamp2?.trim()}"`);
console.groupEnd();
}


// Charger les statistiques système
async function loadSystemStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/data/stats`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const stats = await response.json();
        displaySystemStats(stats);
        
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
        showError(`Erreur lors du chargement des statistiques: ${error.message}`, 'systemStats');
    }
}

// Afficher les statistiques système
function displaySystemStats(stats) {
    const container = document.getElementById('systemStats');
    
    if (stats.error) {
        container.innerHTML = `<div class="text-center text-muted">${stats.error}</div>`;
        return;
    }

    container.innerHTML = `
        <div class="row g-3">
            <div class="col-md-6">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-2">Lectures Totales</h6>
                    <div class="h4 mb-0 text-primary">${stats.total_readings?.toLocaleString() || 0}</div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-2">Puissance Actuelle</h6>
                    <div class="h4 mb-0 text-success">${stats.current_power?.total_watts?.toFixed(0) || 0} W</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-2">Énergie S1</h6>
                    <div class="h5 mb-0 text-info">${stats.energy_consumption?.source_1_kwh?.toFixed(3) || 0} kWh</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-2">Énergie S2</h6>
                    <div class="h5 mb-0 text-info">${stats.energy_consumption?.source_2_kwh?.toFixed(3) || 0} kWh</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-2">Énergie Totale</h6>
                    <div class="h5 mb-0 text-warning">${stats.energy_consumption?.total_kwh?.toFixed(3) || 0} kWh</div>
                </div>
            </div>
        </div>
    `;
}

// Initialiser les graphiques
function initializeCharts() {
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                type: 'linear',
                position: 'bottom',
                title: { display: true, text: 'Temps' }
            },
            y: {
                beginAtZero: true
            }
        },
        plugins: {
            legend: { position: 'top' }
        },
        animation: { duration: 0 }
    };

    // Graphique de puissance
    charts.power = new Chart(document.getElementById('powerChart'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'P1 (W)', data: [], borderColor: '#2563eb', backgroundColor: 'rgba(37, 99, 235, 0.1)' },
                { label: 'P2 (W)', data: [], borderColor: '#059669', backgroundColor: 'rgba(5, 150, 105, 0.1)' },
                { label: 'Total (W)', data: [], borderColor: '#dc2626', backgroundColor: 'rgba(220, 38, 38, 0.1)' }
            ]
        },
        options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, title: { display: true, text: 'Puissance (W)' } } } }
    });

    // Graphique de tension
    charts.voltage = new Chart(document.getElementById('voltageChart'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'U1 (V)', data: [], borderColor: '#d97706', backgroundColor: 'rgba(217, 119, 6, 0.1)' },
                { label: 'U2 (V)', data: [], borderColor: '#0891b2', backgroundColor: 'rgba(8, 145, 178, 0.1)' }
            ]
        },
        options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, title: { display: true, text: 'Tension (V)' } } } }
    });

    // Graphique de courant
    charts.current = new Chart(document.getElementById('currentChart'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'I1 (A)', data: [], borderColor: '#7c3aed', backgroundColor: 'rgba(124, 58, 237, 0.1)' },
                { label: 'I2 (A)', data: [], borderColor: '#db2777', backgroundColor: 'rgba(219, 39, 119, 0.1)' },
                { label: 'I Lamp1 (A)', data: [], borderColor: '#ea580c', backgroundColor: 'rgba(234, 88, 12, 0.1)' },
                { label: 'I Lamp2 (A)', data: [], borderColor: '#65a30d', backgroundColor: 'rgba(101, 163, 13, 0.1)' }
            ]
        },
        options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, title: { display: true, text: 'Courant (A)' } } } }
    });

    // Graphique puissance lampes
    charts.lampPower = new Chart(document.getElementById('lampPowerChart'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'Lampe 1 (W)', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)' },
                { label: 'Lampe 2 (W)', data: [], borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)' }
            ]
        },
        options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, title: { display: true, text: 'Puissance Lampes (W)' } } } }
    });

    // Graphique énergie
    charts.energy = new Chart(document.getElementById('energyChart'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'Énergie S1 (kWh)', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)' },
                { label: 'Énergie S2 (kWh)', data: [], borderColor: '#06b6d4', backgroundColor: 'rgba(6, 182, 212, 0.1)' },
                { label: 'Énergie Totale (kWh)', data: [], borderColor: '#8b5cf6', backgroundColor: 'rgba(139, 92, 246, 0.1)' }
            ]
        },
        options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, title: { display: true, text: 'Énergie (kWh)' } } } }
    });

    // Graphique états (step chart)
    charts.status = new Chart(document.getElementById('statusChart'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'Source 1', data: [], borderColor: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', stepped: true },
                { label: 'Source 2', data: [], borderColor: '#22c55e', backgroundColor: 'rgba(34, 197, 94, 0.1)', stepped: true },
                { label: 'Lampe 1', data: [], borderColor: '#f97316', backgroundColor: 'rgba(249, 115, 22, 0.1)', stepped: true },
                { label: 'Lampe 2', data: [], borderColor: '#a855f7', backgroundColor: 'rgba(168, 85, 247, 0.1)', stepped: true }
            ]
        },
        options: { 
            ...commonOptions, 
            scales: { 
                ...commonOptions.scales, 
                y: { 
                    min: 0, 
                    max: 1.2, 
                    ticks: { 
                        stepSize: 1,
                        callback: function(value) {
                            return value === 1 ? 'ON' : value === 0 ? 'OFF' : '';
                        }
                    },
                    title: { display: true, text: 'État' }
                } 
            } 
        }
    });

    // Graphique d'énergie journalière
    charts.dailyEnergy = new Chart(document.getElementById('dailyEnergyChart'), {
        type: 'bar',
        data: {
            labels: ['Lampe 1', 'Lampe 2', 'Source 1', 'Source 2', 'Total Système'],
            datasets: [{
                label: 'Consommation (kWh)',
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(16, 185, 129, 0.8)', 
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(34, 197, 94, 0.8)',
                    'rgba(139, 92, 246, 0.8)'
                ],
                borderColor: [
                    'rgb(245, 158, 11)',
                    'rgb(16, 185, 129)',
                    'rgb(59, 130, 246)', 
                    'rgb(34, 197, 94)',
                    'rgb(139, 92, 246)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                x: {
                    title: { display: true, text: 'Appareils' }
                },
                y: {
                    ...commonOptions.scales.y,
                    title: { display: true, text: 'Énergie (kWh)' }
                }
            },
            plugins: {
                ...commonOptions.plugins,
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(3) + ' kWh';
                        }
                    }
                }
            }
        }
    });
}

// Ajouter des données aux graphiques
function addToChartData(data) {
    const now = Date.now();
    const maxPoints = 50; // Limiter le nombre de points affichés
    
    // Ajouter les nouveaux points
    chartData.labels.push(now);
    chartData.power.p1.push({ x: now, y: data.P1 || 0 });
    chartData.power.p2.push({ x: now, y: data.P2 || 0 });
    chartData.power.total.push({ x: now, y: (data.P1 || 0) + (data.P2 || 0) });
    
    chartData.voltage.u1.push({ x: now, y: data.U1 || 0 });
    chartData.voltage.u2.push({ x: now, y: data.U2 || 0 });
    
    chartData.current.i1.push({ x: now, y: data.I1 || 0 });
    chartData.current.i2.push({ x: now, y: data.I2 || 0 });
    chartData.current.lamp1.push({ x: now, y: data.currentLamp1 || 0 });
    chartData.current.lamp2.push({ x: now, y: data.currentLamp2 || 0 });
    
    chartData.lampPower.lamp1.push({ x: now, y: data.powerLamp1 || 0 });
    chartData.lampPower.lamp2.push({ x: now, y: data.powerLamp2 || 0 });
    
    chartData.energy.s1.push({ x: now, y: data.savedEnergyS1 || 0 });
    chartData.energy.s2.push({ x: now, y: data.savedEnergyS2 || 0 });
    chartData.energy.total.push({ x: now, y: data.savedEnergyT || 0 });
    
    chartData.status.s1.push({ x: now, y: data.etatS1 === 'ON' ? 1 : 0 });
    chartData.status.s2.push({ x: now, y: data.etatS2 === 'ON' ? 1 : 0 });
    chartData.status.lamp1.push({ x: now, y: data.etatLamp1 === 'ON' ? 1 : 0 });
    chartData.status.lamp2.push({ x: now, y: data.etatLamp2 === 'ON' ? 1 : 0 });
    
    // Limiter le nombre de points (garder seulement les plus récents)
    if (chartData.labels.length > maxPoints) {
        chartData.labels.shift();
        Object.keys(chartData).forEach(category => {
            if (category !== 'labels') {
                Object.keys(chartData[category]).forEach(key => {
                    chartData[category][key].shift();
                });
            }
        });
    }
}

// Mettre à jour tous les graphiques
function updateCharts() {
    if (!charts.power) return; // Graphiques pas encore initialisés
    
    // Mettre à jour les données des graphiques
    charts.power.data.datasets[0].data = chartData.power.p1;
    charts.power.data.datasets[1].data = chartData.power.p2;
    charts.power.data.datasets[2].data = chartData.power.total;
    charts.power.update('none');
    
    charts.voltage.data.datasets[0].data = chartData.voltage.u1;
    charts.voltage.data.datasets[1].data = chartData.voltage.u2;
    charts.voltage.update('none');
    
    charts.current.data.datasets[0].data = chartData.current.i1;
    charts.current.data.datasets[1].data = chartData.current.i2;
    charts.current.data.datasets[2].data = chartData.current.lamp1;
    charts.current.data.datasets[3].data = chartData.current.lamp2;
    charts.current.update('none');
    
    charts.lampPower.data.datasets[0].data = chartData.lampPower.lamp1;
    charts.lampPower.data.datasets[1].data = chartData.lampPower.lamp2;
    charts.lampPower.update('none');
    
    charts.energy.data.datasets[0].data = chartData.energy.s1;
    charts.energy.data.datasets[1].data = chartData.energy.s2;
    charts.energy.data.datasets[2].data = chartData.energy.total;
    charts.energy.update('none');
    
    charts.status.data.datasets[0].data = chartData.status.s1;
    charts.status.data.datasets[1].data = chartData.status.s2;
    charts.status.data.datasets[2].data = chartData.status.lamp1;
    charts.status.data.datasets[3].data = chartData.status.lamp2;
    charts.status.update('none');
}

// Fonction pour charger le graphique d'énergie journalière
async function loadDailyEnergyChart() {
    try {
        const selectedDate = document.getElementById('dailyEnergyDate').value;
        if (!selectedDate) {
            alert('Veuillez sélectionner une date');
            return;
        }
        
        const response = await fetch(`${API_BASE_URL}/data/daily-energy?date=${selectedDate}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Mettre à jour le graphique
        charts.dailyEnergy.data.datasets[0].data = [
            data.lamp1_energy || 0,
            data.lamp2_energy || 0, 
            data.source1_energy || 0,
            data.source2_energy || 0,
            data.total_energy || 0
        ];
        
        charts.dailyEnergy.update();
        
        console.log('Graphique d\'énergie journalière mis à jour:', data);
        
    } catch (error) {
        console.error('Erreur lors du chargement de l\'énergie journalière:', error);
        showError(`Erreur lors du chargement de l'énergie journalière: ${error.message}`);
    }
}

// Charger l'historique des données
async function loadHistory(page = 0) {
    try {
        const startDate = document.getElementById('historyStartDate').value;
        const endDate = document.getElementById('historyEndDate').value;
        
        let url = `${API_BASE_URL}/data/history?limit=${historyItemsPerPage}&offset=${page * historyItemsPerPage}`;
        
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const history = await response.json();
        displayHistory(history, page);
        
    } catch (error) {
        console.error('Erreur lors du chargement de l\'historique:', error);
        showError(`Erreur lors du chargement de l'historique: ${error.message}`, 'historyTableBody');
    }
}

// Afficher l'historique dans le tableau
function displayHistory(history, page) {
    const tbody = document.getElementById('historyTableBody');
    
    if (!history || history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Aucune donnée trouvée</td></tr>';
        return;
    }
    
    tbody.innerHTML = history.map(item => `
        <tr>
            <td class="text-nowrap">${new Date(item.timestamp).toLocaleString()}</td>
            <td>${item.U1?.toFixed(1) || '--'} / ${item.U2?.toFixed(1) || '--'}</td>
            <td>${item.I1?.toFixed(2) || '--'} / ${item.I2?.toFixed(2) || '--'}</td>
            <td>${item.P1?.toFixed(0) || '--'} / ${item.P2?.toFixed(0) || '--'}</td>
            <td>${item.powerLamp1?.toFixed(0) || '--'} / ${item.powerLamp2?.toFixed(0) || '--'}</td>
            <td>
                <small>S1: ${item.savedEnergyS1?.toFixed(3) || '--'}</small><br>
                <small>S2: ${item.savedEnergyS2?.toFixed(3) || '--'}</small><br>
                <small>T: ${item.savedEnergyT?.toFixed(3) || '--'}</small>
            </td>
            <td>
                <small class="d-block">S1: <span class="badge ${item.etatS1 === 'ON' ? 'bg-success' : 'bg-secondary'}">${item.etatS1}</span></small>
                <small class="d-block">S2: <span class="badge ${item.etatS2 === 'ON' ? 'bg-success' : 'bg-secondary'}">${item.etatS2}</span></small>
                <small class="d-block">L1: <span class="badge ${item.etatLamp1 === 'ON' ? 'bg-warning text-dark' : 'bg-secondary'}">${item.etatLamp1}</span></small>
                <small class="d-block">L2: <span class="badge ${item.etatLamp2 === 'ON' ? 'bg-warning text-dark' : 'bg-secondary'}">${item.etatLamp2}</span></small>
            </td>
        </tr>
    `).join('');
    
    // Mettre à jour la pagination
    updateHistoryPagination(page, history.length === historyItemsPerPage);
}

// Mettre à jour la pagination de l'historique
function updateHistoryPagination(currentPage, hasMore) {
    const pagination = document.getElementById('historyPagination');
    let paginationHtml = '';
    
    // Bouton précédent
    if (currentPage > 0) {
        paginationHtml += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadHistory(${currentPage - 1}); return false;">Précédent</a>
            </li>
        `;
    }
    
    // Page actuelle
    paginationHtml += `
        <li class="page-item active">
            <span class="page-link">Page ${currentPage + 1}</span>
        </li>
    `;
    
    // Bouton suivant
    if (hasMore) {
        paginationHtml += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadHistory(${currentPage + 1}); return false;">Suivant</a>
            </li>
        `;
    }
    
    pagination.innerHTML = paginationHtml;
}

// Générer un rapport d'énergie
async function generateReport() {
    try {
        const startDate = document.getElementById('reportStartDate').value;
        const endDate = document.getElementById('reportEndDate').value;
        
        if (!startDate || !endDate) {
            alert('Veuillez sélectionner une période complète');
            return;
        }
        
        let url = `${API_BASE_URL}/data/energy-report?start_date=${startDate}&end_date=${endDate}`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const report = await response.json();
        displayReport(report);
        
    } catch (error) {
        console.error('Erreur lors de la génération du rapport:', error);
        showError(`Erreur lors de la génération du rapport: ${error.message}`, 'reportContent');
    }
}

// Afficher le rapport d'énergie
function displayReport(report) {
    const container = document.getElementById('reportContent');
    
    if (report.error) {
        container.innerHTML = `<div class="text-center text-muted">${report.error}</div>`;
        return;
    }
    
    container.innerHTML = `
        <div class="row g-4">
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body">
                        <h6 class="card-title text-primary">
                            <i class="fas fa-calendar me-2"></i>Période Analysée
                        </h6>
                        <p class="mb-1"><strong>Début:</strong> ${new Date(report.period.start).toLocaleString()}</p>
                        <p class="mb-1"><strong>Fin:</strong> ${new Date(report.period.end).toLocaleString()}</p>
                        <p class="mb-0"><strong>Durée:</strong> ${report.period.duration_hours.toFixed(1)} heures</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body">
                        <h6 class="card-title text-success">
                            <i class="fas fa-bolt me-2"></i>Consommation d'Énergie
                        </h6>
                        <p class="mb-1"><strong>Source 1:</strong> ${report.energy_consumption.source_1_kwh} kWh</p>
                        <p class="mb-1"><strong>Source 2:</strong> ${report.energy_consumption.source_2_kwh} kWh</p>
                        <p class="mb-0"><strong>Total:</strong> ${report.energy_consumption.total_kwh} kWh</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body">
                        <h6 class="card-title text-info">
                            <i class="fas fa-chart-bar me-2"></i>Puissance Moyenne
                        </h6>
                        <p class="mb-1"><strong>Source 1:</strong> ${report.average_power.source_1_watts} W</p>
                        <p class="mb-0"><strong>Source 2:</strong> ${report.average_power.source_2_watts} W</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card bg-light">
                    <div class="card-body">
                        <h6 class="card-title text-warning">
                            <i class="fas fa-percent me-2"></i>Taux d'Utilisation
                        </h6>
                        <p class="mb-1"><strong>Source 1:</strong> ${report.usage_statistics.source_1_usage_percentage}%</p>
                        <p class="mb-1"><strong>Source 2:</strong> ${report.usage_statistics.source_2_usage_percentage}%</p>
                        <p class="mb-0"><strong>Lectures totales:</strong> ${report.usage_statistics.total_readings}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Charger les logs
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE_URL}/logs?lines=100`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const logsData = await response.json();
        displayLogs(logsData);
        
    } catch (error) {
        console.error('Erreur lors du chargement des logs:', error);
        document.getElementById('logsContainer').innerHTML = 
            `<div class="text-center text-danger">Erreur lors du chargement des logs: ${error.message}</div>`;
    }
}

// Afficher les logs
function displayLogs(logsData) {
    const container = document.getElementById('logsContainer');
    
    if (logsData.error) {
        container.innerHTML = `<div class="text-center text-danger">${logsData.error}</div>`;
        return;
    }
    
    if (!logsData.logs || logsData.logs.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">Aucun log disponible</div>';
        return;
    }
    
    const logsHtml = logsData.logs.map(log => {
        // Coloriser les logs selon leur niveau
        let className = '';
        if (log.includes('ERROR')) className = 'text-danger';
        else if (log.includes('WARNING')) className = 'text-warning';
        else if (log.includes('INFO')) className = 'text-info';
        
        return `<div class="${className}">${log}</div>`;
    }).join('');
    
    container.innerHTML = logsHtml;
    
    // Scroll vers le bas pour voir les logs les plus récents
    container.scrollTop = container.scrollHeight;
}

// Fonction utilitaire pour définir les dates par défaut
function setDefaultDates() {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    // Format pour datetime-local input
    const formatDateTime = (date) => {
        return date.toISOString().slice(0, 16);
    };
    
    // Définir les dates par défaut pour l'historique
    document.getElementById('historyStartDate').value = formatDateTime(yesterday);
    document.getElementById('historyEndDate').value = formatDateTime(now);
    
    // Définir les dates par défaut pour les rapports
    document.getElementById('reportStartDate').value = formatDateTime(yesterday);
    document.getElementById('reportEndDate').value = formatDateTime(now);
}

// Contrôle des lampes
async function controlLamp(lampId, action) {
    try {
        const response = await fetch(`${API_BASE_URL}/control/lamp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                lamp_id: lampId,
                action: action
            })
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const result = await response.json();
        
        // Afficher le résultat
        showControlStatus(`Commande envoyée: Lampe ${lampId} ${action}`, 'success');
        
        console.log('Commande envoyée:', result);
        
    } catch (error) {
        console.error('Erreur lors du contrôle de la lampe:', error);
        showControlStatus(`Erreur: ${error.message}`, 'error');
    }
}

// Fonction pour afficher le statut des commandes
function showControlStatus(message, type) {
    const statusDiv = document.getElementById('controlStatus');
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    
    statusDiv.innerHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Effacer automatiquement après 5 secondes
    setTimeout(() => {
        statusDiv.innerHTML = '';
    }, 5000);
}

// Initialiser les dates par défaut quand la page se charge
document.addEventListener('DOMContentLoaded', function() {
    setDefaultDates();
});