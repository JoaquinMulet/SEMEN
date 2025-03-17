#team_formation
import itertools
from collections import defaultdict

def calculate_co_play_counts(match_history):
    """
    Calculate how many times each pair of players has played together
    
    Args:
        match_history (list): List of tuples (player_id, match_id, team)
        
    Returns:
        dict: Nested dictionary mapping player pairs to co-play counts
    """
    co_play_counts = defaultdict(lambda: defaultdict(int))
    
    # Group players by match and team
    match_teams = defaultdict(lambda: defaultdict(list))
    for player_id, match_id, team in match_history:
        match_teams[match_id][team].append(player_id)
    
    # Count co-plays within each team
    for match_id, teams in match_teams.items():
        for team, players in teams.items():
            for player1 in players:
                for player2 in players:
                    if player1 != player2:
                        co_play_counts[player1][player2] += 1
    
    return co_play_counts

def calculate_diversity_score(team1, team2, co_play_counts):
    """
    Calculate the diversity score between two teams
    
    Args:
        team1 (list): List of player_ids in team1
        team2 (list): List of player_ids in team2
        co_play_counts (dict): Nested dictionary mapping player pairs to co-play counts
        
    Returns:
        int: Diversity score (lower is better)
    """
    score = 0
    for player1 in team1:
        for player2 in team2:
            score += co_play_counts[player1][player2]
    return score

def find_optimal_teams(available_players, player_elos, match_history=None):
    """
    Find the optimal team formation for a set of players
    
    Args:
        available_players (list): List of player_ids
        player_elos (dict): Dictionary mapping player_id to ELO rating
        match_history (list, optional): List of tuples (player_id, match_id, team)
        
    Returns:
        tuple: (team1, team2) - Lists of player IDs for each team
    """
    if len(available_players) % 2 != 0:
        raise ValueError("Number of players must be even")
    
    team_size = len(available_players) // 2
    
    # Calculate co-play counts if match history is provided
    co_play_counts = defaultdict(lambda: defaultdict(int))
    if match_history:
        co_play_counts = calculate_co_play_counts(match_history)
    
    # Generate all possible team combinations
    possible_teams = list(itertools.combinations(available_players, team_size))
    
    best_combination = None
    best_elo_difference = float('inf')
    best_diversity_score = float('inf')
    
    for team1 in possible_teams:
        team2 = tuple(set(available_players) - set(team1))
        
        team1_avg_elo = sum(player_elos[p] for p in team1) / team_size
        team2_avg_elo = sum(player_elos[p] for p in team2) / team_size
        
        elo_difference = abs(team1_avg_elo - team2_avg_elo)
        diversity_score = calculate_diversity_score(team1, team2, co_play_counts)
        
        # Prioritize ELO balance, then diversity
        if (elo_difference < best_elo_difference or 
            (elo_difference == best_elo_difference and diversity_score < best_diversity_score)):
            best_combination = (team1, team2)
            best_elo_difference = elo_difference
            best_diversity_score = diversity_score
    
    if best_combination is None:
        # Fallback if no combination found
        mid = len(available_players) // 2
        return available_players[:mid], available_players[mid:]
    
    team1, team2 = best_combination
    return list(team1), list(team2)
