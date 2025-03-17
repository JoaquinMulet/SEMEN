//stats.js
// Create mock exports object if it doesn't exist (fix for "exports is not defined" error)
if (typeof exports === 'undefined') {
    window.exports = {};
}

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // References to elements
    const eloChart = document.getElementById('eloChart');
    const playerSelectionContainer = document.getElementById('playerSelectionContainer');
    const playerSelection = document.getElementById('playerSelection');
    const showTop5Btn = document.getElementById('showTop5');
    const showTop10Btn = document.getElementById('showTop10');
    const customSelectionBtn = document.getElementById('customSelection');
    const updateChartBtn = document.getElementById('updateChart');
    const playerRows = document.querySelectorAll('.player-row');

    // Paleta de colores más atractiva y accesible
    const colorPalette = [
        '#4361EE', '#3A0CA3', '#7209B7', '#F72585', '#4CC9F0',
        '#4895EF', '#560BAD', '#B5179E', '#F15BB5', '#00BBF9',
        '#0466C8', '#023E8A', '#0077B6', '#0096C7', '#48CAE4',
        '#FF595E', '#FF7961', '#FF924C', '#FFCA3A', '#8AC926',
        '#52B788', '#2D6A4F', '#1B4332', '#081C15', '#D8F3DC'
    ];
    
    // Inicializar tema claro/oscuro según preferencias del usuario
    let isDarkMode = false; // Forzar modo claro
    
    // Declare chart in global scope so it's accessible everywhere
    let chart;
    window.chart = null; // Make chart accessible globally for other scripts
    
    // Configuración de Chart.js con animaciones mejoradas
    Chart.defaults.font.family = "'Inter', 'Helvetica', 'Arial', sans-serif";
    Chart.defaults.color = 'rgba(0, 0, 0, 0.7)';
    Chart.defaults.borderColor = 'rgba(0, 0, 0, 0.05)';

    // Function to set up chart theme based on current theme
    function setupChartTheme() {
        // Get the current theme
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const isDarkMode = currentTheme === 'dark';
        
        // Set chart colors based on theme
        if (window.Chart) {
            // Configure Chart.js defaults based on theme
            Chart.defaults.color = isDarkMode ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)';
            Chart.defaults.borderColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
            
            // Update any existing charts
            if (chart) {
                try {
                    updateChartTheme(isDarkMode);
                } catch (e) {
                    console.warn("Error updating chart theme:", e);
                }
            }
        }
    }

    // This function updates the chart styles when theme changes
    function updateChartTheme(isDarkMode) {
        const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
        const textColor = isDarkMode ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)';
        const legendColor = isDarkMode ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.7)';
        
        if (chart) {
            try {
                // First, update the chart container background
                const chartContainer = document.querySelector('.chart-container');
                if (chartContainer) {
                    chartContainer.style.backgroundColor = isDarkMode ? '#1E1E1E' : '#FFFFFF';
                }
                
                // Safely update chart options
                if (chart.options && chart.options.scales) {
                    // Update X axis if it exists
                    if (chart.options.scales.x) {
                        if (chart.options.scales.x.grid) {
                            chart.options.scales.x.grid.color = gridColor;
                        }
                        if (chart.options.scales.x.ticks) {
                            chart.options.scales.x.ticks.color = textColor;
                        }
                    }
                    
                    // Update Y axis if it exists
                    if (chart.options.scales.y) {
                        if (chart.options.scales.y.grid) {
                            chart.options.scales.y.grid.color = gridColor;
                        }
                        if (chart.options.scales.y.ticks) {
                            chart.options.scales.y.ticks.color = textColor;
                        }
                    }
                }
                
                // Update legend colors safely
                if (chart.options && chart.options.plugins && chart.options.plugins.legend) {
                    if (chart.options.plugins.legend.labels) {
                        chart.options.plugins.legend.labels.color = legendColor;
                    }
                }
                
                // Update tooltip colors safely
                if (chart.options && chart.options.plugins && chart.options.plugins.tooltip) {
                    const tooltip = chart.options.plugins.tooltip;
                    tooltip.backgroundColor = isDarkMode ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)';
                    tooltip.titleColor = isDarkMode ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.8)';
                    tooltip.bodyColor = isDarkMode ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)';
                    tooltip.borderColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
                }
                
                // Apply updates with a try/catch to handle any Chart.js internal errors
                chart.update('none'); // Use 'none' to skip animations for theme changes
            } catch (e) {
                console.warn('Error updating chart theme:', e);
                
                // If direct update fails, try recreating the chart
                try {
                    // Store current datasets
                    const currentDatasets = chart.data.datasets || [];
                    
                    // Get chart canvas
                    const canvas = chart.canvas;
                    const parent = canvas.parentNode;
                    
                    // Destroy old chart
                    chart.destroy();
                    
                    // Create new canvas (to avoid Chart.js caching issues)
                    const newCanvas = document.createElement('canvas');
                    newCanvas.id = 'eloChart';
                    newCanvas.style.width = '100%';
                    newCanvas.style.height = '100%';
                    parent.innerHTML = '';
                    parent.appendChild(newCanvas);
                    
                    // Reinitialize chart
                    chart = initializeChart();
                    window.chart = chart;
                    
                    // Restore datasets
                    if (chart && chart.data) {
                        chart.data.datasets = currentDatasets;
                        chart.update();
                    }
                } catch (err) {
                    console.error('Failed to recreate chart:', err);
                }
            }
        }
    }

    // Make sure our functions are available globally for other scripts
    window.setupChartTheme = setupChartTheme;
    window.updateChartTheme = updateChartTheme;

    // Initialize chart with proper configuration
    function initializeChart() {
        if (!eloChart) return;
        
        const ctx = eloChart.getContext('2d');
        
        // Preparar el fondo según el tema actual
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const backgroundColor = currentTheme === 'dark' ? '#1E1E1E' : '#FFFFFF';
        document.querySelectorAll('.chart-container, .card').forEach(el => {
            el.style.backgroundColor = backgroundColor;
        });
        
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                hover: {
                    mode: 'nearest',
                    intersect: false
                },
                animations: {
                    tension: {
                        duration: 1000,
                        easing: 'easeOutQuad',
                        from: 0.5,
                        to: 0.3
                    },
                    radius: {
                        duration: 400,
                        easing: 'linear'
                    },
                    y: {
                        duration: 1500,
                        easing: 'easeOutElastic'
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            boxHeight: 8,
                            padding: 20,
                            color: document.documentElement.getAttribute('data-theme') === 'dark' ? 
                                   'rgba(255, 255, 255, 0.8)' : 
                                   'rgba(0, 0, 0, 0.7)'
                        },
                        display: true
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: 'rgba(0, 0, 0, 0.8)',
                        bodyColor: 'rgba(0, 0, 0, 0.7)',
                        borderColor: 'rgba(0, 0, 0, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        boxPadding: 6,
                        usePointStyle: true,
                        callbacks: {
                            title: function(context) {
                                // Verificar si es un punto inicial
                                if (context[0].dataset.isInitialPoint && context[0].dataIndex === 0) {
                                    return 'ELO Inicial';
                                }
                                
                                const date = new Date(context[0].parsed.x);
                                return date.toLocaleDateString('es-ES', {
                                    day: 'numeric',
                                    month: 'short',
                                    year: 'numeric'
                                });
                            },
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(1)} ELO`;
                            }
                        }
                    },
                    zoom: {
                        pan: {
                            enabled: true,
                            mode: 'x'
                        },
                        zoom: {
                            wheel: {
                                enabled: true
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'x'
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'dd/MM'
                            },
                            tooltipFormat: 'dd/MM/yyyy',
                            parser: 'yyyy-MM-dd'
                        },
                        title: {
                            display: true,
                            text: 'Fecha',
                            color: 'rgba(0, 0, 0, 0.6)',
                            font: {
                                weight: 500,
                                size: 12
                            },
                            padding: {top: 10, bottom: 0}
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.03)',
                            tickColor: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            color: 'rgba(0, 0, 0, 0.6)',
                            maxRotation: window.innerWidth < 768 ? 45 : 0,
                            minRotation: window.innerWidth < 768 ? 45 : 0
                        },
                        offset: true,
                        border: {
                            dash: [4, 4]
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Puntuación ELO',
                            color: 'rgba(0, 0, 0, 0.6)',
                            font: {
                                weight: 500,
                                size: 12
                            },
                            padding: {top: 0, bottom: 10}
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.03)',
                            tickColor: 'rgba(0, 0, 0, 0.1)',
                            zeroLineColor: 'rgba(0, 0, 0, 0.2)'
                        },
                        ticks: {
                            color: 'rgba(0, 0, 0, 0.6)',
                            callback: function(value) {
                                return value; 
                            },
                            precision: 0
                        },
                        border: {
                            dash: [4, 4]
                        }
                    }
                },
                elements: {
                    line: {
                        tension: 0.3, // Curva suave
                        borderWidth: 3,
                        fill: true,
                        borderJoinStyle: 'round'
                    },
                    point: {
                        radius: 3,
                        hoverRadius: 6,
                        hitRadius: 10,
                        borderWidth: 2
                    }
                },
                layout: {
                    padding: {
                        top: 10,
                        right: 20,
                        bottom: 10,
                        left: 10
                    }
                }
            }
        });
        
        // Store chart in global window for access from other scripts
        window.chart = chart;
        
        // Añadir manejo responsive para cambios de tamaño
        window.addEventListener('resize', function() {
            if (chart) {
                chart.options.scales.x.ticks.maxRotation = window.innerWidth < 768 ? 45 : 0;
                chart.options.scales.x.ticks.minRotation = window.innerWidth < 768 ? 45 : 0;
                chart.update();
            }
        });
        
        return chart;
    }
    
    // Make initializeChart available globally
    window.initializeChart = initializeChart;

    function setActiveButton(button) {
        document.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.classList.remove('btn-light');
            btn.classList.add('btn-outline-light');
        });
        button.classList.remove('btn-outline-light');
        button.classList.add('btn-light');
    }

    function showLoadingSpinner() {
        if (document.getElementById('chart-loader')) return;
        
        const container = document.querySelector('.chart-container');
        if (!container) return;
        
        const spinner = document.createElement('div');
        spinner.id = 'chart-loader';
        spinner.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="mt-2 text-muted">Cargando datos...</p>
        `;
        spinner.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; z-index: 10;';
        container.style.position = 'relative';
        container.appendChild(spinner);
    }

    function hideLoadingSpinner() {
        const spinner = document.getElementById('chart-loader');
        if (spinner) {
            spinner.remove();
        }
    }

    // Esta función carga los datos históricos de ELO
    async function loadEloHistory(playerIds, limit = 10) {
        try {
            showLoadingSpinner();
            
            // Construct URL with query parameters for ELO history
            let url = '/api/player-elo-history?interval=day';
            
            if (playerIds && playerIds.length > 0) {
                playerIds.forEach(id => {
                    url += `&player_ids=${id}`;
                });
            } else {
                url += `&limit=${limit}`;
            }
            
            console.log("Loading data from:", url);
            const response = await fetch(url);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error loading ELO data');
            }
            
            const data = await response.json();
            console.log("Received data:", data);
            
            if (!data.data) {
                throw new Error('Unexpected response format');
            }
            
            // Get initial player information
            let playersInitialData = {};
            
            // Get player IDs from the dataset
            const playerIdsFromData = Object.keys(data.data);
            
            // Load information for each player with improved error handling
            for (const playerId of playerIdsFromData) {
                try {
                    console.log(`Loading player ${playerId} data`);
                    const playerResponse = await fetch(`/api/player/${playerId}`);
                    
                    if (playerResponse.ok) {
                        const playerData = await playerResponse.json();
                        console.log(`Player ${playerId} data:`, playerData);
                        
                        if (playerData.status === 'success' && playerData.player) {
                            playersInitialData[playerId] = {
                                name: playerData.player.name,
                                initial_elo: playerData.player.initial_elo
                            };
                        }
                    } else {
                        // Handle failed API calls gracefully
                        console.warn(`Error loading player ${playerId} data. Status: ${playerResponse.status}`);
                        
                        // Use fallback data from the history response
                        if (data.data[playerId] && data.data[playerId].player_name) {
                            playersInitialData[playerId] = {
                                name: data.data[playerId].player_name,
                                // Use the first ELO entry as a fallback for initial ELO
                                initial_elo: data.data[playerId].history && 
                                            data.data[playerId].history.length > 0 ? 
                                            data.data[playerId].history[0].elo : 1000
                            };
                            console.log(`Using fallback data for player ${playerId}`, playersInitialData[playerId]);
                        }
                    }
                } catch (e) {
                    console.warn(`Error processing player ${playerId} data:`, e);
                    // Continue with next player
                }
            }
            
            console.log("Initial player data:", playersInitialData);
            
            // Add a small delay to appreciate the chart animation
            setTimeout(() => {
                // Update the chart with received data and initial information
                updateChart(data.data, playersInitialData);
                hideLoadingSpinner();
            }, 300);
            
        } catch (error) {
            console.error('Error in loadEloHistory:', error);
            hideLoadingSpinner();
            
            // Show more user-friendly error message
            const container = document.querySelector('.chart-container');
            if (container) {
                const errorMsg = document.createElement('div');
                errorMsg.className = 'alert alert-danger';
                errorMsg.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i> ${error.message}`;
                errorMsg.style.position = 'absolute';
                errorMsg.style.top = '50%';
                errorMsg.style.left = '50%';
                errorMsg.style.transform = 'translate(-50%, -50%)';
                errorMsg.style.maxWidth = '90%';
                container.appendChild(errorMsg);
                
                // Remove message after 5 seconds
                setTimeout(() => {
                    errorMsg.remove();
                }, 5000);
            }
        }
    }

    // Esta función actualiza el gráfico con los datos recibidos
    function updateChart(eloData, playersInitialData) {
        console.log("Actualizando gráfico con:", eloData);
        console.log("Datos iniciales:", playersInitialData);
        
        // Exit early if chart doesn't exist
        if (!chart) {
            console.warn("No chart found to update");
            return;
        }
        
        // Limpiar datasets existentes
        chart.data.datasets = [];
        
        // Añadir cada jugador como un dataset
        let colorIndex = 0;
        const ctx = chart.ctx;
        
        for (const playerId in eloData) {
            const playerData = eloData[playerId];
            const color = colorPalette[colorIndex % colorPalette.length];
            
            // Preparar datos para el gráfico
            const dataPoints = playerData.history.map(point => ({
                x: new Date(point.date),
                y: point.elo
            }));
            
            // Solo agregar si hay puntos
            if (dataPoints.length > 0) {
                // Determinar si añadir punto inicial
                let finalDataPoints = [...dataPoints]; // Crear copia para no modificar el original
                let initialPointAdded = false;
                
                // Añadir punto inicial si tenemos la información
                if (playersInitialData && 
                    playersInitialData[playerId] && 
                    playersInitialData[playerId].initial_elo !== undefined) {
                    
                    console.log(`Añadiendo punto inicial para jugador ${playerId} con ELO: ${playersInitialData[playerId].initial_elo}`);
                    
                    // Verificar si ya tenemos un punto para la fecha más antigua
                    const earliestDate = dataPoints.length > 0 ? 
                        Math.min(...dataPoints.map(p => new Date(p.x).getTime())) :
                        Date.now();
                        
                    // Crear una fecha anterior a la más antigua (7 días antes)
                    const initialDate = new Date(earliestDate);
                    initialDate.setDate(initialDate.getDate() - 7);
                    
                    // Añadir el punto inicial al principio del array
                    finalDataPoints.unshift({
                        x: initialDate,
                        y: playersInitialData[playerId].initial_elo,
                        isInitialPoint: true
                    });
                    
                    initialPointAdded = true;
                    console.log("Punto inicial añadido:", finalDataPoints[0]);
                } else {
                    console.log(`No se encontraron datos iniciales para el jugador ${playerId}`);
                }
                
                // Añadir dataset al gráfico
                chart.data.datasets.push({
                    label: playerData.player_name,
                    data: finalDataPoints,
                    backgroundColor: color, 
                    pointBackgroundColor: '#FFFFFF',
                    borderColor: color,
                    borderWidth: 3,
                    pointRadius: (ctx) => {
                        // Hacer el punto inicial un poco más grande
                        const index = ctx.dataIndex;
                        return index === 0 && initialPointAdded ? 6 : 4;
                    },
                    pointStyle: (ctx) => {
                        // Cambiar el estilo del punto inicial
                        const index = ctx.dataIndex;
                        return index === 0 && initialPointAdded ? 'rect' : 'circle';
                    },
                    pointBorderColor: color,
                    pointBackgroundColor: (ctx) => {
                        const index = ctx.dataIndex;
                        return index === 0 && initialPointAdded ? color : '#fff';
                    },
                    pointHoverRadius: 7,
                    pointHoverBorderWidth: 2,
                    pointHoverBackgroundColor: color,
                    pointHoverBorderColor: '#fff',
                    tension: 0.3,
                    fill: false, 
                    spanGaps: true,
                    order: colorIndex, // Para mantener un orden consistente
                    isInitialPoint: initialPointAdded
                });
                
                colorIndex++;
            }
        }
        
        console.log("Datasets finales:", chart.data.datasets);
        
        // Animación suave al actualizar
        chart.update({
            duration: 800,
            easing: 'easeOutQuad'
        });
        
        // Añadir título dinámico
        updateChartTitle();
    }
    
    function updateChartTitle() {
        if (!chart || !chart.data) return;
        
        const datasetsCount = chart.data.datasets.length;
        let title = '';
        
        if (datasetsCount === 0) {
            title = 'No hay datos disponibles';
        } else if (datasetsCount === 1) {
            title = `Evolución de ELO: ${chart.data.datasets[0].label}`;
        } else if (datasetsCount <= 5) {
            title = `Evolución de ELO: Top ${datasetsCount}`;
        } else {
            title = `Evolución de ELO: ${datasetsCount} jugadores`;
        }
        
        // Actualizar título si existe el plugin
        if (chart.options.plugins.title) {
            chart.options.plugins.title.text = title;
            chart.update();
        }
    }

    function loadTop5() {
        showLoadingSpinner();
        loadEloHistory([], 5);
    }

    function loadTop10() {
        showLoadingSpinner();
        loadEloHistory([], 10);
    }

    function loadCustomPlayers() {
        if (!playerSelection) return;
        
        const selectedOptions = Array.from(playerSelection.selectedOptions);
        const selectedPlayerIds = selectedOptions.map(option => option.value);
        
        if (selectedPlayerIds.length === 0) {
            // Mostrar error con animación y estilo Bootstrap
            const errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-warning alert-dismissible fade show';
            errorAlert.innerHTML = `
                <i class="bi bi-exclamation-triangle me-2"></i>
                Por favor, selecciona al menos un jugador.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            // Insertar antes del contenedor de selección
            if (playerSelectionContainer && playerSelectionContainer.parentNode) {
                playerSelectionContainer.parentNode.insertBefore(errorAlert, playerSelectionContainer);
                
                // Eliminar después de 3 segundos
                setTimeout(() => {
                    errorAlert.classList.remove('show');
                    setTimeout(() => errorAlert.remove(), 300);
                }, 3000);
            }
            
            return;
        }
        
        showLoadingSpinner();
        loadEloHistory(selectedPlayerIds);
    }

    async function loadPlayerDetails(playerId, playerName) {
        try {
            // Cargar datos del jugador
            const response = await fetch(`/api/player/${playerId}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Error al cargar datos del jugador');
            }
            
            const data = await response.json();
            
            if (data.status !== 'success' || !data.player) {
                throw new Error('Formato de respuesta inesperado');
            }
            
            // Mostrar datos básicos del jugador en una tarjeta flotante
            showPlayerCard(data.player);
            
            // Cargar el historial específico para este jugador
            loadEloHistory([playerId]);
            
        } catch (error) {
            console.error('Error:', error);
            hideLoadingSpinner();
            
            // Mostrar mensaje de error estilizado
            const errorToast = document.createElement('div');
            errorToast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed top-0 end-0 m-3';
            errorToast.style.zIndex = '1050';
            errorToast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi bi-exclamation-circle me-2"></i>
                        Error al cargar datos del jugador: ${error.message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            document.body.appendChild(errorToast);
            
            // Mostrar y ocultar después de 3 segundos
            const toast = new bootstrap.Toast(errorToast, { delay: 3000 });
            toast.show();
            setTimeout(() => errorToast.remove(), 3500);
        }
    }

    function showPlayerCard(player) {
        // Eliminar tarjeta existente si la hay
        const existingCard = document.getElementById('player-detail-card');
        if (existingCard) {
            existingCard.remove();
        }
        
        // Crear tarjeta de jugador
        const card = document.createElement('div');
        card.id = 'player-detail-card';
        card.className = 'card position-fixed animate__animated animate__fadeIn';
        card.style.cssText = 'bottom: 20px; right: 20px; width: 300px; z-index: 1000; box-shadow: 0 5px 25px rgba(0,0,0,0.15); border-radius: 12px; overflow: hidden; border: none;';
        
        card.innerHTML = `
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="m-0 fs-6">${player.name}</h5>
                <button type="button" class="btn-close btn-close-white btn-sm" aria-label="Close"></button>
            </div>
            <div class="card-body">
                <div class="d-flex justify-content-between mb-3">
                    <span class="text-muted">ELO Actual</span>
                    <span class="badge bg-light text-dark fs-6 fw-bold">${player.elo}</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="text-muted">ELO Inicial</span>
                    <span class="badge bg-light text-dark">${player.initial_elo}</span>
                </div>
            </div>
        `;
        
        document.body.appendChild(card);
        
        // Añadir evento para cerrar
        card.querySelector('.btn-close').addEventListener('click', function() {
            card.classList.replace('animate__fadeIn', 'animate__fadeOut');
            setTimeout(() => card.remove(), 500);
        });
        
        // Auto cerrar después de 5 segundos
        setTimeout(() => {
            if (document.body.contains(card)) {
                card.classList.replace('animate__fadeIn', 'animate__fadeOut');
                setTimeout(() => card.remove(), 500);
            }
        }, 5000);
    }
    
    // Initialize chart and attach event listeners
    function init() {
        // Initialize chart
        if (eloChart) {
            initializeChart();
            
            // Configure theme after chart is initialized
            setupChartTheme();
            
            // Load initial data
            loadTop5();
            
            // Set up event listeners
            if (showTop5Btn) {
                showTop5Btn.addEventListener('click', function() {
                    setActiveButton(this);
                    loadTop5();
                    if (playerSelectionContainer) {
                        playerSelectionContainer.style.display = 'none';
                    }
                });
            }
            
            if (showTop10Btn) {
                showTop10Btn.addEventListener('click', function() {
                    setActiveButton(this);
                    loadTop10();
                    if (playerSelectionContainer) {
                        playerSelectionContainer.style.display = 'none';
                    }
                });
            }
            
            if (customSelectionBtn) {
                customSelectionBtn.addEventListener('click', function() {
                    setActiveButton(this);
                    if (playerSelectionContainer) {
                        playerSelectionContainer.style.display = 'block';
                    }
                });
            }
            
            if (updateChartBtn) {
                updateChartBtn.addEventListener('click', loadCustomPlayers);
            }
            
            // Make player rows clickable
            playerRows.forEach(row => {
                row.addEventListener('click', function() {
                    const playerId = this.getAttribute('data-player-id');
                    const playerNameEl = this.querySelector('td:nth-child(2) span');
                    const playerName = playerNameEl ? playerNameEl.textContent.trim() : '';
                    
                    // Visual effect on selection
                    playerRows.forEach(r => r.classList.remove('selected-player'));
                    this.classList.add('selected-player');
                    
                    // Show loading spinner
                    showLoadingSpinner();
                    
                    // Load player details
                    loadPlayerDetails(playerId, playerName);
                });
            });
        }
    }
    
    // Call init to start everything
    init();
});