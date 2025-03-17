import math
from models import Player, PlayerMatch, Match
from flask import current_app
from sqlalchemy import and_, or_, func
from datetime import datetime

def calculate_elo_change(player_elo, opponent_elo, result, k_factor=32, goal_difference=0):
    """
    Calcula el cambio de ELO basado en el resultado del partido
    
    Args:
        player_elo: ELO actual del jugador
        opponent_elo: ELO del oponente o equipo oponente
        result: Resultado (1 para victoria, 0.5 para empate, 0 para derrota)
        k_factor: Factor K que determina la magnitud del cambio (por defecto: 32)
        goal_difference: Diferencia de goles/puntos (para ajustar el cambio)
        
    Returns:
        float: Cambio en el ELO
    """
    # Calcular probabilidad esperada de victoria (fórmula de ELO)
    expected = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))
    
    # Ajustar el factor K según la diferencia de goles (opcional)
    if goal_difference > 0:
        # Aumentar el factor K para victorias/derrotas con gran diferencia
        k_factor = k_factor * (1 + 0.1 * min(goal_difference, 5))
    
    # Calcular el cambio de ELO
    return k_factor * (result - expected)

def calculate_win_probability(team1_avg_elo, team2_avg_elo):
    """
    Calculate the probability of team1 winning against team2
    
    Args:
        team1_avg_elo (int): Average ELO rating of team1
        team2_avg_elo (int): Average ELO rating of team2
        
    Returns:
        float: Probability of team1 winning (between 0 and 1)
    """
    return 1 / (1 + math.pow(10, (team2_avg_elo - team1_avg_elo) / 400))

def calculate_team_average_elo(player_elos):
    """
    Calculate the average ELO rating of a team
    
    Args:
        player_elos (list): List of ELO ratings of players in the team
        
    Returns:
        float: Average ELO rating of the team
    """
    if not player_elos:
        return 1000  # Valor por defecto para equipos sin datos
    
    return sum(player_elos) / len(player_elos)

def calculate_player_elo(player_id):
    """
    Calcula el ELO actual de un jugador basado en todos sus partidos
    
    Args:
        player_id: ID del jugador
        
    Returns:
        int: ELO actual del jugador
    """
    # Obtener el jugador
    player = Player.query.get(player_id)
    if not player:
        raise ValueError(f"Player with ID {player_id} not found")
    
    # Obtener todos los partidos en orden cronológico
    player_matches = PlayerMatch.query.filter_by(player_id=player_id).join(
        Match, PlayerMatch.match_id == Match.id
    ).order_by(Match.date).all()
    
    if not player_matches:
        return player.elo  # Sin partidos, devolver ELO inicial
    
    # Calcular ELO hasta el último partido jugado
    latest_match = Match.query.join(
        PlayerMatch, Match.id == PlayerMatch.match_id
    ).filter(
        PlayerMatch.player_id == player_id
    ).order_by(Match.date.desc()).first()
    
    if not latest_match:
        return player.elo
    
    # Utilizar caches vacíos para este cálculo único
    return calculate_player_elo_up_to_match(player_id, latest_match.id, {}, {})

def calculate_player_elo_up_to_match(player_id, match_id, elo_cache=None, elo_at_match_start_cache=None):
    """
    Calcula el ELO de un jugador hasta un partido específico
    
    Args:
        player_id: ID del jugador
        match_id: ID del partido hasta el cual calcular
        elo_cache: Caché para evitar recálculos (opcional)
        elo_at_match_start_cache: Caché para evitar recursión (opcional)
        
    Returns:
        int: ELO del jugador después del partido especificado
    """
    # Inicializar caches si no se proporcionan
    if elo_cache is None:
        elo_cache = {}
    if elo_at_match_start_cache is None:
        elo_at_match_start_cache = {}
    
    # Revisar si ya está en caché
    cache_key = f"{player_id}_{match_id}"
    if cache_key in elo_cache:
        return elo_cache[cache_key]
    
    # Obtener el jugador
    player = Player.query.get(player_id)
    if not player:
        raise ValueError(f"Player with ID {player_id} not found")
    
    # Comenzar con el ELO inicial
    elo = player.elo
    
    # Obtener todos los partidos hasta el especificado en orden cronológico
    subquery = Match.query.filter(Match.id <= match_id).subquery()
    player_matches = PlayerMatch.query.filter_by(player_id=player_id).join(
        subquery, PlayerMatch.match_id == subquery.c.id
    ).join(Match).order_by(Match.date).all()
    
    if not player_matches:
        elo_cache[cache_key] = elo  # Guardar en caché
        return elo  # Sin partidos, devolver ELO inicial
    
    for pm in player_matches:
        # Obtener todos los jugadores en este partido
        match_players = PlayerMatch.query.filter_by(match_id=pm.match_id).all()
        
        # Separar por equipos
        team1_players = [p for p in match_players if p.team == 1]
        team2_players = [p for p in match_players if p.team == 2]
        
        if not team1_players or not team2_players:
            continue  # Saltar partidos con datos incompletos
        
        # Calcular ELO promedio para cada equipo en este momento
        if pm.team == 1:
            # Jugador está en equipo 1, calcular ELO promedio del equipo 2
            team2_elos = []
            for p in team2_players:
                try:
                    player_elo_key = f"start_{p.player_id}_{pm.match_id}"
                    if player_elo_key not in elo_at_match_start_cache:
                        elo_at_match_start_cache[player_elo_key] = calculate_player_elo_at_match_start(
                            p.player_id, pm.match_id, elo_cache, elo_at_match_start_cache
                        )
                    team2_elos.append(elo_at_match_start_cache[player_elo_key])
                except Exception as e:
                    if current_app:
                        current_app.logger.warning(f"Error getting ELO for player {p.player_id}: {str(e)}")
                    # Si hay error, usar ELO actual o inicial
                    team2_elos.append(Player.query.get(p.player_id).elo)
            
            if team2_elos:  # Verificar que hay datos
                opponent_team_avg_elo = calculate_team_average_elo(team2_elos)
                result = 1 if pm.match.winning_team == 1 else (0.5 if pm.match.winning_team == 0 else 0)
            else:
                continue  # Saltar si no hay datos válidos
        else:
            # Jugador está en equipo 2, calcular ELO promedio del equipo 1
            team1_elos = []
            for p in team1_players:
                try:
                    player_elo_key = f"start_{p.player_id}_{pm.match_id}"
                    if player_elo_key not in elo_at_match_start_cache:
                        elo_at_match_start_cache[player_elo_key] = calculate_player_elo_at_match_start(
                            p.player_id, pm.match_id, elo_cache, elo_at_match_start_cache
                        )
                    team1_elos.append(elo_at_match_start_cache[player_elo_key])
                except Exception as e:
                    if current_app:
                        current_app.logger.warning(f"Error getting ELO for player {p.player_id}: {str(e)}")
                    # Si hay error, usar ELO actual o inicial
                    team1_elos.append(Player.query.get(p.player_id).elo)
            
            if team1_elos:  # Verificar que hay datos
                opponent_team_avg_elo = calculate_team_average_elo(team1_elos)
                result = 1 if pm.match.winning_team == 2 else (0.5 if pm.match.winning_team == 0 else 0)
            else:
                continue  # Saltar si no hay datos válidos
        
        # Calcular cambio de ELO para este partido
        try:
            # Verificar si el partido tiene atributos de puntuación
            goal_difference = 0
            if hasattr(pm.match, 'team1_score') and hasattr(pm.match, 'team2_score'):
                goal_difference = abs(pm.match.team1_score - pm.match.team2_score)
            
            elo_change = calculate_elo_change(elo, opponent_team_avg_elo, result, goal_difference=goal_difference)
            elo += elo_change
        except Exception as e:
            if current_app:
                current_app.logger.warning(f"Error calculating ELO change for player {player_id} in match {pm.match_id}: {str(e)}")
            # Continuar con el siguiente partido
    
    # Guardar en caché y devolver
    result_elo = round(elo)
    elo_cache[cache_key] = result_elo
    return result_elo

def calculate_player_elo_at_match_start(player_id, match_id, elo_cache=None, elo_at_match_start_cache=None):
    """
    Calcula el ELO de un jugador justo antes de un partido específico
    
    Args:
        player_id: ID del jugador
        match_id: ID del partido
        elo_cache: Caché para evitar recálculos (opcional)
        elo_at_match_start_cache: Caché para evitar recursión (opcional)
        
    Returns:
        int: ELO del jugador justo antes del partido
    """
    # Inicializar caches si no se proporcionan
    if elo_cache is None:
        elo_cache = {}
    if elo_at_match_start_cache is None:
        elo_at_match_start_cache = {}
    
    # Revisar si ya está en caché
    cache_key = f"start_{player_id}_{match_id}"
    if cache_key in elo_at_match_start_cache:
        return elo_at_match_start_cache[cache_key]
    
    # Obtener el jugador
    player = Player.query.get(player_id)
    if not player:
        # Usar valor por defecto si no se encuentra el jugador
        elo_at_match_start_cache[cache_key] = 1000
        return 1000
    
    # Obtener el partido actual para su fecha
    current_match = Match.query.get(match_id)
    if not current_match:
        raise ValueError(f"Match with ID {match_id} not found")
    
    # Obtener el último partido jugado antes de este
    previous_match = Match.query.filter(
        Match.date < current_match.date
    ).join(
        PlayerMatch, Match.id == PlayerMatch.match_id
    ).filter(
        PlayerMatch.player_id == player_id
    ).order_by(Match.date.desc()).first()
    
    if not previous_match:
        # Sin partidos previos, devolver ELO inicial
        elo_at_match_start_cache[cache_key] = player.elo
        return player.elo
    
    # Calcular ELO hasta el partido anterior
    result = calculate_player_elo_up_to_match(player_id, previous_match.id, elo_cache, elo_at_match_start_cache)
    
    # Guardar en caché y devolver
    elo_at_match_start_cache[cache_key] = result
    return result

def update_elos_after_match(team1_player_ids, team2_player_ids, winning_team, team1_score=0, team2_score=0):
    """
    Calculate new ELO ratings for all players after a match
    
    Args:
        team1_player_ids (list): List of player_ids for team1
        team2_player_ids (list): List of player_ids for team2
        winning_team (int): 1 if team1 won, 2 if team2 won, 0 for draw
        team1_score (int): Goals scored by team1
        team2_score (int): Goals scored by team2
        
    Returns:
        dict: Dictionary mapping player_id to new ELO rating
    """
    # Get current ELO ratings for all players
    team1_players = [(pid, calculate_player_elo(pid)) for pid in team1_player_ids]
    team2_players = [(pid, calculate_player_elo(pid)) for pid in team2_player_ids]
    
    team1_elos = [elo for _, elo in team1_players]
    team2_elos = [elo for _, elo in team2_players]
    
    team1_avg_elo = calculate_team_average_elo(team1_elos)
    team2_avg_elo = calculate_team_average_elo(team2_elos)
    
    # Determine results (including draws)
    if winning_team == 0:  # Draw
        result_team1 = 0.5
        result_team2 = 0.5
    else:
        result_team1 = 1 if winning_team == 1 else 0
        result_team2 = 1 if winning_team == 2 else 0
    
    # Calculate goal differences
    team1_goal_diff = abs(team1_score - team2_score)
    team2_goal_diff = team1_goal_diff  # Same difference for both teams
    
    new_elos = {}
    
    # Calculate new ELO ratings for team1 players
    for player_id, elo in team1_players:
        elo_change = calculate_elo_change(elo, team2_avg_elo, result_team1, goal_difference=team1_goal_diff)
        new_elos[player_id] = round(elo + elo_change)
    
    # Calculate new ELO ratings for team2 players
    for player_id, elo in team2_players:
        elo_change = calculate_elo_change(elo, team1_avg_elo, result_team2, goal_difference=team2_goal_diff)
        new_elos[player_id] = round(elo + elo_change)
    
    return new_elos

def calculate_elo_change_between_last_matches(player_id):
    """
    Calcula la diferencia de ELO entre el último y el penúltimo partido del jugador.
    
    Args:
        player_id (int): ID del jugador
        
    Returns:
        int: Diferencia de ELO (positiva si mejoró, negativa si empeoró, 0 si no hay cambio o no hay suficientes partidos)
    """
    try:
        # Obtener los últimos dos partidos del jugador en orden cronológico inverso
        last_matches = Match.query.join(
            PlayerMatch, Match.id == PlayerMatch.match_id
        ).filter(
            PlayerMatch.player_id == player_id
        ).order_by(Match.date.desc()).limit(2).all()
            
        if len(last_matches) < 2:
            return 0  # No hay suficientes partidos para calcular el cambio
            
        # Calcular ELO después del último partido
        last_match_elo = calculate_player_elo_up_to_match(player_id, last_matches[0].id, {}, {})
            
        # Calcular ELO después del penúltimo partido
        prev_match_elo = calculate_player_elo_up_to_match(player_id, last_matches[1].id, {}, {})
        
        # Calcular la diferencia
        return last_match_elo - prev_match_elo
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error al calcular el cambio de ELO para el jugador {player_id}: {str(e)}")
        return 0

def get_player_draws(player_id):
    """
    Obtiene la cantidad de partidos empatados por un jugador.
    
    Args:
        player_id (int): ID del jugador
        
    Returns:
        int: Número de partidos empatados
    """
    try:
        # Contar los partidos donde el jugador participó y el resultado fue empate (winning_team = 0)
        draws_count = Player.query.session.query(func.count(Match.id)).join(
            PlayerMatch, Match.id == PlayerMatch.match_id
        ).filter(
            PlayerMatch.player_id == player_id,
            Match.winning_team == 0
        ).scalar()
        
        return draws_count or 0
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error al obtener los empates del jugador {player_id}: {str(e)}")
        return 0

def get_player_stats(player_id):
    """
    Obtiene estadísticas completas de un jugador.
    
    Args:
        player_id (int): ID del jugador
        
    Returns:
        dict: Diccionario con estadísticas del jugador
    """
    player = Player.query.get(player_id)
    if not player:
        return None
    
    # Obtener número de partidos jugados
    matches_played = PlayerMatch.query.filter_by(player_id=player_id).count()
    
    # Obtener victorias
    wins = Player.query.session.query(func.count(Match.id)).join(
        PlayerMatch, Match.id == PlayerMatch.match_id
    ).filter(
        PlayerMatch.player_id == player_id,
        or_(
            and_(PlayerMatch.team == 1, Match.winning_team == 1),
            and_(PlayerMatch.team == 2, Match.winning_team == 2)
        )
    ).scalar() or 0
    
    # Obtener empates
    draws = get_player_draws(player_id)
    
    # Calcular derrotas
    losses = matches_played - wins - draws
    
    # Calcular porcentaje de victorias (contando empates como medio punto)
    win_rate = round((wins + (draws * 0.5)) / matches_played * 100, 1) if matches_played > 0 else 0
    
    # Calcular ELO actual
    try:
        current_elo = calculate_player_elo(player_id)
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error al calcular ELO para el jugador {player_id}: {str(e)}")
        current_elo = player.elo
    
    # Calcular cambio de ELO desde el último partido
    try:
        elo_change = calculate_elo_change_between_last_matches(player_id)
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error al calcular cambio de ELO para el jugador {player_id}: {str(e)}")
        elo_change = 0
    
    return {
        'id': player.id,
        'name': player.name,
        'elo': current_elo,
        'initial_elo': player.elo,
        'elo_change': elo_change,
        'matches_played': matches_played,
        'wins': wins,
        'draws': draws,
        'losses': losses,
        'win_rate': win_rate
    }

def get_leaderboard_data():
    """
    Obtiene los datos para la tabla de clasificación incluyendo empates.
    
    Returns:
        list: Lista de diccionarios con datos de clasificación de jugadores
    """
    players = Player.query.all()
    leaderboard_data = []
    
    for player in players:
        try:
            # Obtener estadísticas del jugador
            stats = get_player_stats(player.id)
            if stats:
                leaderboard_data.append(stats)
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error al obtener datos de clasificación para el jugador {player.id}: {str(e)}")
            # Continuar con el siguiente jugador
    
    # Ordenar por ELO de mayor a menor
    leaderboard_data = sorted(leaderboard_data, key=lambda x: x['elo'], reverse=True)
    
    return leaderboard_data