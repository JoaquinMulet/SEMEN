/**
 * dark-mode.js - Sistema modular para gestión de temas claro/oscuro
 * Este archivo puede ser incluido en todas las páginas que requieran soporte para temas
 */

window.ThemeManager = (function() {
    // Objeto que almacenará todas las funciones públicas
    const manager = {};
    
    // Inicializa el tema
    manager.initTheme = function() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        manager.updateThemeIcon();
    };
    
    // Obtiene el tema actual
    manager.getCurrentTheme = function() {
        return document.documentElement.getAttribute('data-theme') || 'dark';
    };
    
    // Actualiza el icono según el tema actual
    manager.updateThemeIcon = function() {
        const darkModeToggle = document.getElementById('darkModeToggle');
        if (!darkModeToggle) return;
        
        const currentTheme = manager.getCurrentTheme();
        const sunIcon = darkModeToggle.querySelector('.sun-icon');
        const moonIcon = darkModeToggle.querySelector('.moon-icon');
        
        if (sunIcon && moonIcon) {
            if (currentTheme === 'dark') {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'inline-block';
            } else {
                sunIcon.style.display = 'inline-block';
                moonIcon.style.display = 'none';
            }
        }
    };
    
    // Alterna entre temas claro y oscuro
    manager.toggleTheme = function() {
        const currentTheme = manager.getCurrentTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        // Actualiza el tooltip durante la transición
        const darkModeTooltip = document.getElementById('darkModeTooltip');
        if (darkModeTooltip) {
            darkModeTooltip.textContent = `Cambiando a modo ${newTheme === 'dark' ? 'oscuro' : 'claro'}...`;
            darkModeTooltip.style.display = 'block';
        }
        
        // Aplica el nuevo tema
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Aplica efecto de transición
        document.body.classList.add('theme-transition');
        setTimeout(() => {
            document.body.classList.add('visible');
        }, 50);
        
        // Actualiza el icono
        manager.updateThemeIcon();
        
        // Actualiza cualquier gráfico si existe
        if (manager.updateCharts) {
            manager.updateCharts(newTheme);
        }
        
        // Completa la transición
        setTimeout(() => {
            document.body.classList.remove('theme-transition', 'visible');
            
            if (darkModeTooltip) {
                darkModeTooltip.textContent = `Modo ${newTheme === 'dark' ? 'oscuro' : 'claro'} activado`;
                
                setTimeout(() => {
                    darkModeTooltip.style.display = 'none';
                }, 2000);
            }
        }, 500);
        
        // Dispara un evento personalizado para que otros scripts puedan reaccionar
        document.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: newTheme } 
        }));
        
        return newTheme;
    };
    
    // Función para actualizar gráficos de Chart.js al cambiar de tema
    manager.updateCharts = function(theme) {
        // Si Chart.js no está cargado, no hacemos nada
        if (typeof Chart === 'undefined') return;
        
        try {
            // Buscar todos los canvas de gráficos en la página
            const canvases = document.querySelectorAll('canvas');
            canvases.forEach(canvas => {
                let chart = null;
                
                // Intentar diferentes formas de obtener el gráfico
                if (canvas.__chart__) {
                    chart = canvas.__chart__;
                } else if (window.Chart && window.Chart.getChart) {
                    try {
                        chart = Chart.getChart(canvas);
                    } catch (e) {
                        // Ignorar errores de Chart.getChart
                    }
                } else if (window[canvas.id]) {
                    chart = window[canvas.id];
                }
                
                // Si encontramos un gráfico, actualizarlo
                if (chart && chart.options) {
                    const isDark = theme === 'dark';
                    
                    // Configuraciones por defecto
                    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
                    const textColor = isDark ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)';
                    const tooltipBg = isDark ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.95)';
                    const tooltipText = isDark ? 'rgba(255, 255, 255, 0.8)' : 'rgba(0, 0, 0, 0.8)';
                    
                    // Actualizar el contenedor del gráfico
                    const chartContainer = canvas.closest('.chart-container');
                    if (chartContainer) {
                        chartContainer.style.backgroundColor = isDark ? '#1E1E1E' : '#FFFFFF';
                    }
                    
                    // Actualizar escalas
                    if (chart.options.scales) {
                        Object.keys(chart.options.scales).forEach(axisKey => {
                            const axis = chart.options.scales[axisKey];
                            if (axis.grid) axis.grid.color = gridColor;
                            if (axis.ticks) axis.ticks.color = textColor;
                        });
                    }
                    
                    // Actualizar plugins
                    if (chart.options.plugins) {
                        // Leyenda
                        if (chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                            chart.options.plugins.legend.labels.color = textColor;
                        }
                        
                        // Tooltip
                        if (chart.options.plugins.tooltip) {
                            chart.options.plugins.tooltip.backgroundColor = tooltipBg;
                            chart.options.plugins.tooltip.titleColor = tooltipText;
                            chart.options.plugins.tooltip.bodyColor = tooltipText;
                        }
                    }
                    
                    // Aplicar actualización
                    chart.update('none');
                }
            });
        } catch (err) {
            console.warn('Error al actualizar gráficos:', err);
        }
    };
    
    // Configura los eventos para el botón de tema
    manager.setupEvents = function() {
        const darkModeToggle = document.getElementById('darkModeToggle');
        const darkModeTooltip = document.getElementById('darkModeTooltip');
        
        if (darkModeToggle) {
            // Evento de clic para cambiar el tema
            darkModeToggle.addEventListener('click', manager.toggleTheme);
            
            // Eventos para mostrar/ocultar tooltip
            if (darkModeTooltip) {
                darkModeToggle.addEventListener('mouseenter', () => {
                    const currentTheme = manager.getCurrentTheme();
                    darkModeTooltip.textContent = currentTheme === 'dark' 
                        ? 'Cambiar a modo claro' 
                        : 'Cambiar a modo oscuro';
                    darkModeTooltip.style.display = 'block';
                });
                
                darkModeToggle.addEventListener('mouseleave', () => {
                    darkModeTooltip.style.display = 'none';
                });