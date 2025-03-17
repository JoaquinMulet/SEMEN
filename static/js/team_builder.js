document.addEventListener('DOMContentLoaded', function() {
    const playerCheckboxes = document.querySelectorAll('.player-checkbox');
    const buildTeamsBtn = document.getElementById('build-teams-btn');
    const teamsContainer = document.getElementById('teams-container');
    const noTeamsMessage = document.getElementById('no-teams-message');
    const team1PlayersList = document.getElementById('team1-players-list');
    const team2PlayersList = document.getElementById('team2-players-list');
    const team1Elo = document.getElementById('team1-elo');
    const team2Elo = document.getElementById('team2-elo');
    const eloDifference = document.getElementById('elo-difference');
    const team1WinProb = document.getElementById('team1-win-prob');
    const team2WinProb = document.getElementById('team2-win-prob');
    const regenerateTeamsBtn = document.getElementById('regenerate-teams-btn');
    const saveMatchBtn = document.getElementById('save-match-btn');
    const fieldContainer = document.getElementById('field-container');
    const team1Formation = document.getElementById('team1-formation');
    const team2Formation = document.getElementById('team2-formation');
    
    // Set today's date as default for match date
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    document.getElementById('match-date').value = `${year}-${month}-${day}`;
    
    // Auto-build teams for preselected players
    if (document.querySelectorAll('.player-checkbox:checked').length > 1) {
        setTimeout(() => {
            buildTeamsBtn.click();
        }, 500);
    }
    
    // Validate score and winner consistency
    const team1ScoreInput = document.getElementById('team1_score');
    const team2ScoreInput = document.getElementById('team2_score');
    const team1WinRadio = document.getElementById('save-team1-win');
    const team2WinRadio = document.getElementById('save-team2-win');
    const drawRadio = document.getElementById('save-draw');
    
    function updateWinnerBasedOnScore() {
        const team1Score = parseInt(team1ScoreInput.value) || 0;
        const team2Score = parseInt(team2ScoreInput.value) || 0;
        
        if (team1Score > team2Score) {
            team1WinRadio.checked = true;
        } else if (team2Score > team1Score) {
            team2WinRadio.checked = true;
        } else {
            drawRadio.checked = true;
        }
    }
    
    team1ScoreInput.addEventListener('change', updateWinnerBasedOnScore);
    team2ScoreInput.addEventListener('change', updateWinnerBasedOnScore);
    
    // Validate form before submission
    document.getElementById('saveMatchForm').addEventListener('submit', function(event) {
        const team1Score = parseInt(team1ScoreInput.value) || 0;
        const team2Score = parseInt(team2ScoreInput.value) || 0;
        const selectedWinner = document.querySelector('input[name="winning_team"]:checked').value;
        
        let isValid = true;
        let errorMessage = '';
        
        if (selectedWinner === '1' && team1Score <= team2Score) {
            errorMessage = 'Si el Equipo 1 gana, debe tener más goles que el Equipo 2';
            isValid = false;
        } else if (selectedWinner === '2' && team2Score <= team1Score) {
            errorMessage = 'Si el Equipo 2 gana, debe tener más goles que el Equipo 1';
            isValid = false;
        } else if (selectedWinner === '0' && team1Score !== team2Score) {
            errorMessage = 'En caso de empate, ambos equipos deben tener el mismo número de goles';
            isValid = false;
        }
        
        if (!isValid) {
            event.preventDefault();
            alert(errorMessage);
        }
    });
    
    // Función para determinar la formación según la cantidad de jugadores
    function getFormation(playerCount) {
        if (playerCount === 6) return "2-1-2"; // 2 defensas, 1 mediocampista, 2 delanteros (+ 1 arquero)
        if (playerCount === 7) return "4-2"; // 4 defensas, 2 delanteros (+ 1 arquero)
        if (playerCount === 8) return "4-3"; // 4 defensas, 3 delanteros (+ 1 arquero)
        if (playerCount === 9) return "4-4"; // 4 defensas, 4 delanteros (+ 1 arquero)
        if (playerCount === 10) return "4-4-1"; // 4 defensas, 4 mediocampistas, 1 delantero (+ 1 arquero)
        if (playerCount === 11) return "4-4-2"; // 4 defensas, 4 mediocampistas, 2 delanteros (+ 1 arquero)
        return "4-4-2"; // Formación por defecto
    }
    
    // Función para posicionar jugadores en el campo
    function positionPlayers(team, formation, isTeam1) {
        const positions = [];
        const formationParts = formation.split('-').map(n => parseInt(n));
        
        // Verificar si es la formación 2-1-2 para equipos de 6 jugadores (5 + arquero)
        const isFormation212 = formation === "2-1-2" && team.length === 6;
        
        // Siempre añadir un portero
        positions.push({ role: 'GK', x: isTeam1 ? 10 : 90, y: 50 });
        
        let playerIndex = 0;
        let currentY = 0;
        
        // Posicionar defensas
        if (formationParts[0]) {
            const defSpacing = 100 / (formationParts[0] + 1);
            for (let i = 0; i < formationParts[0]; i++) {
                currentY = defSpacing * (i + 1);
                positions.push({ 
                    role: 'DEF', 
                    x: isTeam1 ? 25 : 75, 
                    y: currentY 
                });
            }
        }
        
        // Posicionar mediocampistas
        if (formationParts[1]) {
            const midSpacing = 100 / (formationParts[1] + 1);
            for (let i = 0; i < formationParts[1]; i++) {
                currentY = midSpacing * (i + 1);
                positions.push({ 
                    role: 'MID', 
                    x: isTeam1 ? 40 : 60, 
                    y: currentY 
                });
            }
        }
        
        // Posicionar delanteros
        if (formationParts[2]) {
            const fwdSpacing = 100 / (formationParts[2] + 1);
            for (let i = 0; i < formationParts[2]; i++) {
                currentY = fwdSpacing * (i + 1);
                positions.push({ 
                    role: 'FWD', 
                    x: isTeam1 ? 45 : 55, 
                    y: currentY 
                });
            }
        } else if (formationParts.length === 2) {
            // Si solo hay dos números en la formación, el segundo son los delanteros
            const fwdSpacing = 100 / (formationParts[1] + 1);
            for (let i = 0; i < formationParts[1]; i++) {
                currentY = fwdSpacing * (i + 1);
                positions.push({ 
                    role: 'FWD', 
                    x: isTeam1 ? 45 : 55, 
                    y: currentY 
                });
            }
        }
        
        // Si es formación 2-1-2, ajustar posiciones para que sea más evidente
        if (isFormation212) {
            // Reemplazar las posiciones con la formación 2-1-2 específica
            positions.length = 0; // Limpiar el array
            
            // Portero
            positions.push({ role: 'GK', x: isTeam1 ? 5 : 95, y: 50 });
            
            // 2 Defensas
            positions.push({ role: 'DEF', x: isTeam1 ? 20 : 80, y: 30 });
            positions.push({ role: 'DEF', x: isTeam1 ? 20 : 80, y: 70 });
            
            // 1 Mediocampista
            positions.push({ role: 'MID', x: isTeam1 ? 32.5 : 67.5, y: 50 });
            
            // 2 Delanteros - Ajustados para evitar superposición
            positions.push({ role: 'FWD', x: isTeam1 ? 45 : 55, y: 30 });
            positions.push({ role: 'FWD', x: isTeam1 ? 45 : 55, y: 70 });
        }
        
        // Elegir un capitán al azar
        const captainIndex = Math.floor(Math.random() * team.length);
        
        // Asignar jugadores a posiciones
        const result = [];
        for (let i = 0; i < Math.min(team.length, positions.length); i++) {
            result.push({
                ...team[i],
                position: positions[i],
                isCaptain: i === captainIndex
            });
        }
        
        return result;
    }
    
    // Build teams
    buildTeamsBtn.addEventListener('click', function() {
        // Get selected players
        const selectedPlayers = [];
        playerCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                selectedPlayers.push({
                    id: parseInt(checkbox.value),
                    name: checkbox.dataset.playerName,
                    elo: parseInt(checkbox.dataset.playerElo)
                });
            }
        });
        
        // Check if we have enough players
        if (selectedPlayers.length < 2) {
            alert('Selecciona al menos 2 jugadores para formar equipos.');
            return;
        }
        
        if (selectedPlayers.length % 2 !== 0) {
            alert('Selecciona un número par de jugadores para formar equipos equilibrados.');
            return;
        }
        
        // Call API to build teams
        fetch('/api/build-teams', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ players: selectedPlayers })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            
            // Display teams
            displayTeams(data);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al generar equipos. Inténtalo de nuevo.');
        });
    });
    
    function displayTeams(data) {
        // Show teams container
        teamsContainer.classList.remove('d-none');
        noTeamsMessage.classList.add('d-none');
        
        // Clear previous teams
        team1PlayersList.innerHTML = '';
        team2PlayersList.innerHTML = '';
        
        // Determinar formación según cantidad de jugadores
        const team1Count = data.team1.length;
        const team2Count = data.team2.length;
        
        const team1FormationStr = getFormation(team1Count);
        const team2FormationStr = getFormation(team2Count);
        
        // Actualizar texto de formación
        if (team1Formation) team1Formation.textContent = team1FormationStr;
        if (team2Formation) team2Formation.textContent = team2FormationStr;
        
        // Posicionar jugadores en el campo
        const team1Positioned = positionPlayers(data.team1, team1FormationStr, true);
        const team2Positioned = positionPlayers(data.team2, team2FormationStr, false);
        
        // Limpiar campo - Solo limpiamos los jugadores, no la estructura de la cancha
        if (fieldContainer) {
            // Eliminar jugadores existentes
            const existingPlayers = fieldContainer.querySelectorAll('.field-player');
            existingPlayers.forEach(player => player.remove());
            
            // Obtener el elemento ground donde colocaremos los jugadores
            const groundElement = fieldContainer.querySelector('.ground');
            
            // Crear jugadores en el campo
            team1Positioned.forEach(player => {
                const playerEl = document.createElement('div');
                playerEl.className = 'field-player team1-player';
                playerEl.style.left = `${player.position.x}%`;
                playerEl.style.top = `${player.position.y}%`;
                playerEl.innerHTML = `
                    <div class="player-icon team1-icon">${player.name.charAt(0)}</div>
                    <div class="player-name">${player.name}</div>
                `;
                if (player.isCaptain) {
                    playerEl.innerHTML += '<div class="player-captain">C</div>';
                }
                groundElement.appendChild(playerEl);
            });
            
            team2Positioned.forEach(player => {
                const playerEl = document.createElement('div');
                playerEl.className = 'field-player team2-player';
                playerEl.style.left = `${player.position.x}%`;
                playerEl.style.top = `${player.position.y}%`;
                playerEl.innerHTML = `
                    <div class="player-icon team2-icon">${player.name.charAt(0)}</div>
                    <div class="player-name">${player.name}</div>
                `;
                if (player.isCaptain) {
                    playerEl.innerHTML += '<div class="player-captain">C</div>';
                }
                groundElement.appendChild(playerEl);
            });
        }
        
        // Display team 1
        data.team1.forEach((player, index) => {
            const li = document.createElement('li');
            li.className = 'list-group-item player-item';
            const position = index === 0 ? 'POR' : (index <= 2 ? 'DEF' : (index <= 3 ? 'MED' : 'DEL'));
            li.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="player-number">${index + 1}</div>
                    <div class="player-name">${player.name}${player.isCaptain ? ' (C)' : ''}</div>
                    <div class="player-position">${position}</div>
                    <div class="player-elo">ELO: ${player.elo}</div>
                </div>
            `;
            team1PlayersList.appendChild(li);
        });
        
        // Display team 2
        data.team2.forEach((player, index) => {
            const li = document.createElement('li');
            li.className = 'list-group-item player-item';
            const position = index === 0 ? 'POR' : (index <= 2 ? 'DEF' : (index <= 3 ? 'MED' : 'DEL'));
            li.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="player-number">${index + 1}</div>
                    <div class="player-name">${player.name}${player.isCaptain ? ' (C)' : ''}</div>
                    <div class="player-position">${position}</div>
                    <div class="player-elo">ELO: ${player.elo}</div>
                </div>
            `;
            team2PlayersList.appendChild(li);
        });
        
        // Update statistics
        team1Elo.textContent = data.team1_avg_elo;
        team2Elo.textContent = data.team2_avg_elo;
        eloDifference.textContent = Math.abs(data.team1_avg_elo - data.team2_avg_elo).toFixed(0);
        team1WinProb.textContent = (data.team1_win_probability * 100).toFixed(1) + '%';
        team2WinProb.textContent = (data.team2_win_probability * 100).toFixed(1) + '%';
    }
    
    // Regenerate teams
    regenerateTeamsBtn.addEventListener('click', function() {
        buildTeamsBtn.click();
    });
    
    // Save match
    saveMatchBtn.addEventListener('click', function() {
        // Create hidden inputs for team players
        const team1Inputs = document.getElementById('team1-players-inputs');
        const team2Inputs = document.getElementById('team2-players-inputs');
        
        team1Inputs.innerHTML = '';
        team2Inputs.innerHTML = '';
        
        // Get team 1 players
        const team1Players = [];
        team1PlayersList.querySelectorAll('li').forEach(li => {
            const playerName = li.querySelector('.player-name').textContent;
            const playerCheckbox = document.querySelector(`.player-checkbox[data-player-name="${playerName}"]`);
            if (playerCheckbox) {
                team1Players.push(playerCheckbox.value);
            }
        });
        
        // Get team 2 players
        const team2Players = [];
        team2PlayersList.querySelectorAll('li').forEach(li => {
            const playerName = li.querySelector('.player-name').textContent;
            const playerCheckbox = document.querySelector(`.player-checkbox[data-player-name="${playerName}"]`);
            if (playerCheckbox) {
                team2Players.push(playerCheckbox.value);
            }
        });
        
        // Create hidden inputs with all player IDs in a single field
        const team1Input = document.createElement('input');
        team1Input.type = 'hidden';
        team1Input.name = 'team1_players';
        team1Input.value = team1Players.join(',');
        team1Inputs.appendChild(team1Input);
        
        const team2Input = document.createElement('input');
        team2Input.type = 'hidden';
        team2Input.name = 'team2_players';
        team2Input.value = team2Players.join(',');
        team2Inputs.appendChild(team2Input);
        
        // Show modal
        const saveMatchModal = new bootstrap.Modal(document.getElementById('saveMatchModal'));
        saveMatchModal.show();
    });
});
