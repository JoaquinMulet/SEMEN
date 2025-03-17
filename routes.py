#Routes
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models import db, Player, Match, PlayerMatch, User, Venue, ScheduledMatch, Registration
from elo import (
    calculate_win_probability, calculate_team_average_elo, calculate_player_elo,
    calculate_player_elo_up_to_match, update_elos_after_match,
    calculate_elo_change_between_last_matches, get_player_draws,
    get_player_stats, get_leaderboard_data
)
from team_formation import find_optimal_teams
from datetime import datetime, timedelta
import pandas as pd
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
import pytz
from sqlalchemy import func


routes = Blueprint('routes', __name__)

# Decorator to restrict access to admin users only
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acceso restringido. Necesitas permisos de administrador.', 'danger')
            return redirect(url_for('routes.index'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get Santiago timezone
def get_santiago_timezone():
    return pytz.timezone('America/Santiago')

# Helper function to convert UTC to Santiago time
def utc_to_santiago(utc_dt):
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(get_santiago_timezone())

# Helper function to convert Santiago time to UTC
def santiago_to_utc(santiago_dt_str):
    santiago_tz = get_santiago_timezone()
    try:
        # Parse the datetime string
        santiago_dt = datetime.strptime(santiago_dt_str, '%Y-%m-%d %H:%M')
        # Localize to Santiago timezone
        santiago_dt = santiago_tz.localize(santiago_dt)
        # Convert to UTC
        return santiago_dt.astimezone(pytz.utc)
    except ValueError:
        return None

@routes.route('/')
def index():
    """Home page with player standings"""
    players = Player.query.all()
    
    # Get match history for each player
    player_data = []
    for player in players:
        matches_played = PlayerMatch.query.filter_by(player_id=player.id).count()
        
        # Calculate win rate
        wins = 0
        draws = 0  # Also track draws for more accurate statistics
        for pm in PlayerMatch.query.filter_by(player_id=player.id).all():
            if pm.match.winning_team == 0:
                # This is a draw
                draws += 1
            elif pm.team == pm.match.winning_team:
                wins += 1
        
        # Calculate losses
        losses = matches_played - wins - draws
        
        # Calculate win rate (counting draws as half a win as in chess)
        win_rate = ((wins + (draws * 0.5)) / matches_played) * 100 if matches_played > 0 else 0
        
        # Calculate current ELO
        current_elo = calculate_player_elo(player.id)
        
        # Calculate ELO change from last match
        elo_change = 0
        try:
            elo_change = calculate_elo_change_between_last_matches(player.id)
        except Exception as e:
            # Handle any errors in calculating ELO change
            print(f"Error calculating ELO change for player {player.id}: {str(e)}")
        
        player_data.append({
            'id': player.id,
            'name': player.name,
            'matches_played': matches_played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'elo': current_elo,
            'elo_change': elo_change
        })
    
    # Sort by ELO (descending)
    player_data = sorted(player_data, key=lambda x: x['elo'], reverse=True)
    
    return render_template('index.html', players=player_data)

@routes.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Inicio de sesión exitoso', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('routes.index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@routes.route('/logout')
@login_required
def logout():
    """Logout route"""
    logout_user()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('routes.index'))

@routes.route('/players')
@login_required
@admin_required
def players():
    """Players management page"""
    players_list = Player.query.all()
    
    # Calculate ELO for each player
    players_data = []
    for player in players_list:
        current_elo = calculate_player_elo(player.id)
        players_data.append({
            'id': player.id,
            'name': player.name,
            'elo': current_elo,
            'initial_elo': player.elo  # El campo 'elo' en la base de datos almacena el ELO inicial
        })
    
    # Sort players by ELO
    players_data = sorted(players_data, key=lambda x: x['elo'], reverse=True)
    
    return render_template('players.html', players=players_data)

@routes.route('/players/add', methods=['POST'])
@login_required
@admin_required
def add_player():
    """Add a new player"""
    name = request.form.get('name')
    initial_elo = request.form.get('elo')
    
    if not name:
        flash('El nombre del jugador es requerido', 'error')
        return redirect(url_for('routes.players'))
    
    # Verificar que el ELO sea un número válido
    if initial_elo is None or not initial_elo.isdigit() or int(initial_elo) < 0:
        # Si no se proporciona un ELO válido, usar el valor predeterminado de 1000
        initial_elo = 1000
    else:
        initial_elo = int(initial_elo)
    
    # Check if player already exists
    existing_player = Player.query.filter_by(name=name).first()
    if existing_player:
        flash(f'El jugador {name} ya existe', 'error')
        return redirect(url_for('routes.players'))
    
    # Create new player
    new_player = Player(name=name, elo=initial_elo)
    db.session.add(new_player)
    db.session.commit()
    
    flash(f'Jugador {name} agregado correctamente con ELO inicial de {initial_elo}', 'success')
    return redirect(url_for('routes.players'))

@routes.route('/players/delete/<int:player_id>', methods=['POST'])
@login_required
@admin_required
def delete_player(player_id):
    """Delete a player"""
    player = db.get_or_404(Player, player_id)
    
    # Check if player has matches
    player_matches = PlayerMatch.query.filter_by(player_id=player_id).first()
    if player_matches:
        flash(f'No se puede eliminar al jugador {player.name} porque tiene partidos registrados', 'error')
        return redirect(url_for('routes.players'))
    
    db.session.delete(player)
    db.session.commit()
    
    flash(f'Jugador {player.name} eliminado correctamente', 'success')
    return redirect(url_for('routes.players'))

@routes.route('/players/edit/<int:player_id>', methods=['POST'])
@login_required
@admin_required
def edit_player(player_id):
    """Edit a player"""
    player = db.get_or_404(Player, player_id)
    
    name = request.form.get('name')
    
    if not name:
        flash('El nombre del jugador es requerido', 'error')
        return redirect(url_for('routes.players'))
    
    # Check if the name is already taken by another player
    existing_player = Player.query.filter(Player.name == name, Player.id != player_id).first()
    if existing_player:
        flash(f'Ya existe un jugador con el nombre {name}', 'error')
        return redirect(url_for('routes.players'))
    
    # Update player
    player.name = name
    db.session.commit()
    
    flash(f'Jugador {name} actualizado correctamente', 'success')
    return redirect(url_for('routes.players'))

@routes.route('/matches', methods=['GET', 'POST'])
@login_required
@admin_required
def matches():
    """Matches page"""
    matches_list = Match.query.order_by(Match.date.desc()).all()
    
    match_data = []
    for match in matches_list:
        team1_players = PlayerMatch.query.filter_by(match_id=match.id, team=1).all()
        team2_players = PlayerMatch.query.filter_by(match_id=match.id, team=2).all()
        
        team1_names = [pm.player.name for pm in team1_players]
        team2_names = [pm.player.name for pm in team2_players]
        
        match_data.append({
            'id': match.id,
            'date': match.date.strftime('%Y-%m-%d'),
            'team1': team1_names,
            'team2': team2_names,
            'winner': match.winning_team,
            'team1_score': match.team1_score,
            'team2_score': match.team2_score
        })
    
    # Get all players for the form
    players_list = Player.query.all()
    players_data = []
    for player in players_list:
        current_elo = calculate_player_elo(player.id)
        players_data.append({
            'id': player.id,
            'name': player.name,
            'elo': current_elo
        })
    
    # Sort players alphabetically by name
    players_data = sorted(players_data, key=lambda x: x['name'])
    
    return render_template('matches.html', matches=match_data, players=players_data)

@routes.route('/matches/add', methods=['POST'])
@login_required
@admin_required
def add_match():
    """Add a new match"""
    date_str = request.form.get('date')
    team1_players_str = request.form.get('team1_players', '')
    team2_players_str = request.form.get('team2_players', '')
    winning_team = int(request.form.get('winning_team'))
    team1_score = int(request.form.get('team1_score', 0))
    team2_score = int(request.form.get('team2_score', 0))
    
    # Validate input
    if not date_str or not team1_players_str or not team2_players_str:
        flash('All fields are required', 'error')
        return redirect(url_for('routes.matches'))
    
    # Validate scores and winning team consistency
    if winning_team == 1 and team1_score <= team2_score:
        flash('El marcador no coincide con el equipo ganador', 'error')
        return redirect(url_for('routes.matches'))
    elif winning_team == 2 and team2_score <= team1_score:
        flash('El marcador no coincide con el equipo ganador', 'error')
        return redirect(url_for('routes.matches'))
    elif winning_team == 0 and team1_score != team2_score:
        flash('El marcador debe ser igual para un empate', 'error')
        return redirect(url_for('routes.matches'))
    
    # Convert player IDs to integers
    if isinstance(team1_players_str, str):
        team1_players = [int(pid) for pid in team1_players_str.split(',')]
    else:  # It's already a list from the form
        team1_players = [int(pid) for pid in team1_players_str]
        
    if isinstance(team2_players_str, str):
        team2_players = [int(pid) for pid in team2_players_str.split(',')]
    else:  # It's already a list from the form
        team2_players = [int(pid) for pid in team2_players_str]
    
    # Convert date string to datetime
    match_date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Create new match
    new_match = Match(
        date=match_date, 
        winning_team=winning_team,
        team1_score=team1_score,
        team2_score=team2_score
    )
    db.session.add(new_match)
    db.session.flush()  # Get the match ID without committing
    
    # Add players to the match
    for player_id in team1_players:
        # Get current ELO for the player
        elo_before = calculate_player_elo(player_id)
        
        # Create player-match association
        player_match = PlayerMatch(
            player_id=player_id,
            match_id=new_match.id,
            team=1,
            elo_before=elo_before,
            elo_after=elo_before  # Will be updated after all players are added
        )
        db.session.add(player_match)
    
    for player_id in team2_players:
        # Get current ELO for the player
        elo_before = calculate_player_elo(player_id)
        
        # Create player-match association
        player_match = PlayerMatch(
            player_id=player_id,
            match_id=new_match.id,
            team=2,
            elo_before=elo_before,
            elo_after=elo_before  # Will be updated after all players are added
        )
        db.session.add(player_match)
    
    # Flush to get all player-match associations
    db.session.flush()
    
    # Update ELOs after the match
    new_elos = update_elos_after_match(
        team1_players, 
        team2_players, 
        winning_team,
        team1_score,
        team2_score
    )
    
    # Update player-match records with new ELOs
    for player_id, new_elo in new_elos.items():
        player_match = PlayerMatch.query.filter_by(player_id=player_id, match_id=new_match.id).first()
        if player_match:
            player_match.elo_after = new_elo
    
    # Commit all changes
    db.session.commit()
    
    flash('Match added successfully', 'success')
    return redirect(url_for('routes.matches'))

@routes.route('/matches/delete/<int:match_id>', methods=['POST'])
@login_required
@admin_required
def delete_match(match_id):
    """Delete a match"""
    match = db.get_or_404(Match, match_id)
    
    # Delete all player-match associations
    PlayerMatch.query.filter_by(match_id=match_id).delete()
    
    # Delete the match
    db.session.delete(match)
    db.session.commit()
    
    flash('Partido eliminado correctamente', 'success')
    return redirect(url_for('routes.matches'))

@routes.route('/team-builder')
@login_required
@admin_required
def team_builder():
    """Team builder page"""
    # Check if a scheduled match ID was provided
    match_id = request.args.get('match_id', None)
    
    if match_id:
        # Get the scheduled match
        scheduled_match = db.get_or_404(ScheduledMatch, match_id)
        
        # Get the registered players for this match
        registrations = Registration.query.filter_by(scheduled_match_id=match_id).all()
        
        if len(registrations) < 2:
            flash('Se necesitan al menos 2 jugadores para formar equipos', 'warning')
            return redirect(url_for('routes.view_registrations', match_id=match_id))
        
        # Get player data for registered players
        players_data = []
        for registration in registrations:
            player = registration.player
            current_elo = calculate_player_elo(player.id)
            players_data.append({
                'id': player.id,
                'name': player.name,
                'elo': current_elo
            })
        
        # Set preselected players
        preselected_players = [player['id'] for player in players_data]
        
        # Sort players alphabetically by name
        players_data = sorted(players_data, key=lambda x: x['name'])
        
        return render_template('team_builder.html', 
                               players=players_data, 
                               preselected_players=preselected_players,
                               scheduled_match=scheduled_match)
    else:
        # Regular team builder without preselected players
        players_list = Player.query.all()
        
        # Calculate ELO for each player
        players_data = []
        for player in players_list:
            current_elo = calculate_player_elo(player.id)
            players_data.append({
                'id': player.id,
                'name': player.name,
                'elo': current_elo
            })
        
        # Sort players alphabetically by name
        players_data = sorted(players_data, key=lambda x: x['name'])
        
        return render_template('team_builder.html', players=players_data)

@routes.route('/api/build-teams', methods=['POST'])
@login_required
@admin_required
def build_teams():
    """API endpoint to build optimal teams"""
    data = request.json
    players = data.get('players', [])
    
    # Validate input
    if not players or len(players) < 2 or len(players) % 2 != 0:
        return jsonify({'error': 'Selección de jugadores inválida'}), 400
    
    # Extract player IDs and ELOs
    player_ids = [player['id'] for player in players]
    player_elos = {player['id']: player['elo'] for player in players}
    
    # Get match history for co-play analysis
    match_history = []
    for pid in player_ids:
        player_matches = PlayerMatch.query.filter_by(player_id=pid).all()
        for pm in player_matches:
            match_history.append((pm.player_id, pm.match_id, pm.team))
    
    try:
        # Find optimal teams
        team1, team2 = find_optimal_teams(player_ids, player_elos, match_history)
        
        # Calculate team average ELOs
        team1_elos = [player_elos[pid] for pid in team1]
        team2_elos = [player_elos[pid] for pid in team2]
        
        team1_avg_elo = calculate_team_average_elo(team1_elos)
        team2_avg_elo = calculate_team_average_elo(team2_elos)
        
        # Calculate win probabilities
        team1_win_probability = calculate_win_probability(team1_avg_elo, team2_avg_elo)
        team2_win_probability = 1 - team1_win_probability
        
        # Get player details
        team1_players = []
        team2_players = []
        
        for pid in team1:
            player_data = next((p for p in players if p['id'] == pid), None)
            if player_data:
                team1_players.append(player_data)
        
        for pid in team2:
            player_data = next((p for p in players if p['id'] == pid), None)
            if player_data:
                team2_players.append(player_data)
        
        return jsonify({
            'team1': team1_players,
            'team2': team2_players,
            'team1_avg_elo': round(team1_avg_elo),
            'team2_avg_elo': round(team2_avg_elo),
            'elo_difference': abs(round(team1_avg_elo - team2_avg_elo)),
            'team1_win_probability': team1_win_probability,
            'team2_win_probability': team2_win_probability
        })
    except Exception as e:
        return jsonify({'error': f'Error al generar equipos: {str(e)}'}), 500

@routes.route('/venues', methods=['GET', 'POST'])
@login_required
@admin_required
def venues():
    """Venues management page"""
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        description = request.form.get('description')
        
        if not name:
            flash('El nombre del estadio es obligatorio', 'danger')
            return redirect(url_for('routes.venues'))
        
        # Check if venue already exists
        existing_venue = Venue.query.filter_by(name=name).first()
        if existing_venue:
            flash(f'El estadio "{name}" ya existe', 'warning')
            return redirect(url_for('routes.venues'))
        
        # Create new venue
        venue = Venue(name=name, address=address, description=description)
        db.session.add(venue)
        db.session.commit()
        
        flash(f'Estadio "{name}" agregado correctamente', 'success')
        return redirect(url_for('routes.venues'))
    
    venues = Venue.query.order_by(Venue.name).all()
    return render_template('venues.html', venues=venues)

@routes.route('/venues/delete/<int:venue_id>', methods=['POST'])
@login_required
@admin_required
def delete_venue(venue_id):
    """Delete a venue"""
    venue = db.get_or_404(Venue, venue_id)
    
    # Check if venue is used in any scheduled match
    scheduled_matches = ScheduledMatch.query.filter_by(venue_id=venue_id).count()
    if scheduled_matches > 0:
        flash(f'No se puede eliminar el estadio "{venue.name}" porque está siendo utilizado en {scheduled_matches} partidos programados', 'danger')
        return redirect(url_for('routes.venues'))
    
    db.session.delete(venue)
    db.session.commit()
    
    flash(f'Estadio "{venue.name}" eliminado correctamente', 'success')
    return redirect(url_for('routes.venues'))

@routes.route('/venues/edit', methods=['POST'])
@login_required
@admin_required
def edit_venue():
    """Edit a venue"""
    venue_id = request.form.get('venue_id')
    name = request.form.get('name')
    address = request.form.get('address')
    description = request.form.get('description')
    
    # Validate input
    if not venue_id or not name:
        flash('Datos incompletos', 'danger')
        return redirect(url_for('routes.venues'))
    
    # Get venue
    venue = db.get_or_404(Venue, venue_id)
    
    # Check if name already exists (for a different venue)
    existing_venue = Venue.query.filter(Venue.name == name, Venue.id != venue.id).first()
    if existing_venue:
        flash(f'Ya existe un estadio con el nombre "{name}"', 'warning')
        return redirect(url_for('routes.venues'))
    
    # Update venue
    venue.name = name
    venue.address = address
    venue.description = description
    
    db.session.commit()
    
    flash(f'Estadio "{name}" actualizado correctamente', 'success')
    return redirect(url_for('routes.venues'))

@routes.route('/schedule-match', methods=['GET', 'POST'])
@login_required
@admin_required
def schedule_match():
    """Schedule a new match"""
    if request.method == 'POST':
        venue_id = request.form.get('venue_id')
        match_date_str = request.form.get('match_date')
        registration_open_date_str = request.form.get('registration_open_date')
        players_per_team = request.form.get('players_per_team')
        
        # Validate inputs
        if not venue_id or not match_date_str or not registration_open_date_str or not players_per_team:
            flash('Todos los campos son obligatorios', 'danger')
            return redirect(url_for('routes.schedule_match'))
        
        # Convert string dates to UTC datetime objects
        match_date = santiago_to_utc(match_date_str)
        registration_open_date = santiago_to_utc(registration_open_date_str)
        
        if not match_date or not registration_open_date:
            flash('Formato de fecha y hora inválido. Use YYYY-MM-DD HH:MM', 'danger')
            return redirect(url_for('routes.schedule_match'))
        
        # Validate match date is in the future
        now_utc = pytz.utc.localize(datetime.utcnow())
        if match_date < now_utc:
            flash('La fecha del partido debe ser en el futuro', 'danger')
            return redirect(url_for('routes.schedule_match'))
        
        # Validate registration open date is before match date
        if registration_open_date > match_date:
            flash('La fecha de apertura de inscripciones debe ser anterior a la fecha del partido', 'danger')
            return redirect(url_for('routes.schedule_match'))
        
        # Validate players per team
        try:
            players_per_team = int(players_per_team)
            if players_per_team < 3 or players_per_team > 11:
                raise ValueError
        except ValueError:
            flash('El número de jugadores por equipo debe ser entre 3 y 11', 'danger')
            return redirect(url_for('routes.schedule_match'))
        
        # Create new scheduled match
        scheduled_match = ScheduledMatch(
            match_date=match_date,
            venue_id=venue_id,
            players_per_team=players_per_team,
            registration_open_date=registration_open_date,
            is_active=True
        )
        
        db.session.add(scheduled_match)
        db.session.commit()
        
        flash('Partido programado correctamente', 'success')
        return redirect(url_for('routes.schedule_match'))
    
    venues = Venue.query.order_by(Venue.name).all()
    
    # Get current time in Santiago timezone for template
    now = utc_to_santiago(datetime.utcnow())
    now_utc = pytz.utc.localize(datetime.utcnow())
    
    # Get all scheduled matches
    all_scheduled_matches = ScheduledMatch.query.order_by(ScheduledMatch.match_date.desc()).all()
    
    # Separar los partidos en próximos e históricos
    upcoming_matches = []
    historic_matches = []
    
    for match in all_scheduled_matches:
        # Asegurar que match_date tenga zona horaria para comparar con now_utc
        match_date = match.match_date
        if match_date.tzinfo is None:
            match_date = pytz.utc.localize(match_date)
        
        # Convertir fechas a Santiago para mostrar
        match.match_date_santiago = utc_to_santiago(match.match_date)
        match.registration_open_date_santiago = utc_to_santiago(match.registration_open_date)
        
        # Verificar si el partido ya pasó o está finalizado
        if match_date < now_utc or match.is_finished:
            historic_matches.append(match)
        else:
            upcoming_matches.append(match)
    
    # Verificar si hay partidos pasados que deberían marcarse como "Por finalizar"
    for match in historic_matches:
        if not match.is_finished and match.is_active:
            # Aquí podríamos marcarlos automáticamente o mostrar un aviso
            pass
    
    # Ordenar históricos del más reciente al más antiguo
    historic_matches.sort(key=lambda x: x.match_date, reverse=True)
    
    # Ordenar próximos del más cercano al más lejano
    upcoming_matches.sort(key=lambda x: x.match_date)
    
    return render_template(
        'schedule_match.html', 
        venues=venues, 
        scheduled_matches=upcoming_matches,
        historic_matches=historic_matches,
        now=now
    )

@routes.route('/scheduled-match/delete/<int:match_id>', methods=['POST'])
@login_required
@admin_required
def delete_scheduled_match(match_id):
    """Delete a scheduled match"""
    scheduled_match = db.get_or_404(ScheduledMatch, match_id)
    
    # Delete all registrations for this match
    Registration.query.filter_by(scheduled_match_id=match_id).delete()
    
    # Delete the scheduled match
    db.session.delete(scheduled_match)
    db.session.commit()
    
    flash('Partido programado eliminado correctamente', 'success')
    return redirect(url_for('routes.schedule_match'))

@routes.route('/scheduled-match/toggle-status/<int:match_id>', methods=['POST'])
@login_required
@admin_required
def toggle_match_status(match_id):
    """Toggle the active status of a scheduled match"""
    scheduled_match = db.get_or_404(ScheduledMatch, match_id)
    
    scheduled_match.is_active = not scheduled_match.is_active
    db.session.commit()
    
    status = "activado" if scheduled_match.is_active else "desactivado"
    flash(f'Partido {status} correctamente', 'success')
    return redirect(url_for('routes.schedule_match'))

@routes.route('/scheduled-match/finish/<int:match_id>', methods=['POST'])
@login_required
@admin_required
def finish_match(match_id):
    """Mark a scheduled match as finished"""
    scheduled_match = db.get_or_404(ScheduledMatch, match_id)
    
    scheduled_match.is_finished = True
    db.session.commit()
    
    flash(f'Partido marcado como finalizado correctamente', 'success')
    return redirect(url_for('routes.schedule_match'))

@routes.route('/view-registrations/<int:match_id>')
@login_required
@admin_required
def view_registrations(match_id):
    """View registrations for a specific match"""
    scheduled_match = db.get_or_404(ScheduledMatch, match_id)
    
    # Get current time in Santiago timezone for template
    now = utc_to_santiago(datetime.utcnow())
    
    # Convert match dates to Santiago timezone
    scheduled_match.match_date_santiago = utc_to_santiago(scheduled_match.match_date)
    scheduled_match.registration_open_date_santiago = utc_to_santiago(scheduled_match.registration_open_date)
    
    return render_template('view_registrations.html', match=scheduled_match, now=now)

@routes.route('/remove-registration/<int:registration_id>', methods=['POST'])
@login_required
@admin_required
def remove_registration(registration_id):
    """Remove a player registration"""
    registration = db.get_or_404(Registration, registration_id)
    match_id = registration.scheduled_match_id
    
    db.session.delete(registration)
    db.session.commit()
    
    flash('Inscripción eliminada correctamente', 'success')
    return redirect(url_for('routes.view_registrations', match_id=match_id))

@routes.route('/register', methods=['GET'])
def register_page():
    """Registration page for players"""
    # Get current time in UTC
    now_utc = pytz.utc.localize(datetime.utcnow())
    
    # Get active scheduled matches that haven't occurred yet and aren't finished
    all_scheduled_matches = ScheduledMatch.query.filter_by(is_active=True).order_by(ScheduledMatch.match_date).all()
    
    # Filtrar manualmente los partidos que ya ocurrieron o están marcados como finalizados
    upcoming_matches = []
    historic_matches = []
    
    for match in all_scheduled_matches:
        # Asegurar que match_date tenga zona horaria para comparar con now_utc
        match_date = match.match_date
        if match_date.tzinfo is None:
            match_date = pytz.utc.localize(match_date)
        
        # Convertir fechas a Santiago para mostrar
        match.match_date_santiago = utc_to_santiago(match.match_date)
        match.registration_open_date_santiago = utc_to_santiago(match.registration_open_date)
        
        # Verificar si el partido ya pasó o está finalizado
        if match_date < now_utc or match.is_finished:
            historic_matches.append(match)
        else:
            upcoming_matches.append(match)
    
    # Ordenar históricos del más reciente al más antiguo
    historic_matches.sort(key=lambda x: x.match_date, reverse=True)
    
    # Ordenar próximos del más cercano al más lejano
    upcoming_matches.sort(key=lambda x: x.match_date)
    
    # Get all players for the selection dropdown
    players = Player.query.order_by(Player.name).all()
    
    # Get current time in Santiago timezone for template
    now = utc_to_santiago(datetime.utcnow())
    
    return render_template(
        'register.html', 
        scheduled_matches=upcoming_matches,
        historic_matches=historic_matches,
        players=players, 
        now=now
    )

@routes.route('/register/<int:match_id>', methods=['POST'])
def register(match_id):
    """Register a player for a match"""
    scheduled_match = db.get_or_404(ScheduledMatch, match_id)
    
    # Check if registration is open
    if not scheduled_match.is_registration_open:
        flash('Las inscripciones para este partido no están abiertas', 'danger')
        return redirect(url_for('routes.register_page'))
    
    player_id = request.form.get('player_id')
    if not player_id:
        flash('Debes seleccionar un jugador', 'danger')
        return redirect(url_for('routes.register_page'))
    
    # Check if player exists
    player = db.get_or_404(Player, player_id)
    
    # Check if player is already registered for this match
    existing_registration = Registration.query.filter_by(
        player_id=player_id, 
        scheduled_match_id=match_id
    ).first()
    
    if existing_registration:
        flash(f'{player.name} ya está inscrito para este partido', 'warning')
        return redirect(url_for('routes.register_page'))
    
    # Create new registration
    registration = Registration(
        player_id=player_id,
        scheduled_match_id=match_id
    )
    
    db.session.add(registration)
    db.session.commit()
    
    flash(f'{player.name} inscrito correctamente para el partido', 'success')
    return redirect(url_for('routes.register_page'))

@routes.route('/player/<int:player_id>')
def player_profile(player_id):
    """Player profile page"""
    player = db.get_or_404(Player, player_id)
    
    # Get player's matches
    player_matches = PlayerMatch.query.filter_by(player_id=player_id).all()
    
    # Get player's stats - ahora importado desde elo.py
    stats = get_player_stats(player_id)
    
    return render_template('player_profile.html', player=player, stats=stats, player_matches=player_matches)

@routes.route('/players/update_elo/<int:player_id>', methods=['POST'])
@login_required
@admin_required
def update_player_elo(player_id):
    """
    Actualiza el nombre y el ELO inicial del jugador.
    """
    try:
        # Obtener el nuevo nombre y ELO del formulario
        new_name = request.form.get('name')
        new_elo = request.form.get('elo')
        
        # Verificar que el nombre no esté vacío
        if not new_name or new_name.strip() == '':
            flash('El nombre del jugador es requerido.', 'error')
            return redirect(url_for('routes.players'))
        
        # Verificar que el ELO sea un número válido
        if new_elo is None or not new_elo.isdigit() or int(new_elo) < 0:
            flash('El ELO debe ser un número positivo.', 'error')
            return redirect(url_for('routes.players'))
        
        new_elo = int(new_elo)  # Convertir a entero después de la verificación
        
        # Obtener el jugador de la base de datos
        player = db.get_or_404(Player, player_id)
        
        # Verificar si el nombre ya existe (solo si ha cambiado)
        if new_name != player.name:
            existing_player = Player.query.filter(Player.name == new_name, Player.id != player_id).first()
            if existing_player:
                flash(f'Ya existe un jugador con el nombre {new_name}', 'error')
                return redirect(url_for('routes.players'))
        
        # Actualizar el nombre y el ELO inicial del jugador
        player.name = new_name
        player.elo = new_elo
        db.session.commit()
        
        flash(f'Jugador actualizado correctamente. Nombre: {new_name}, ELO inicial: {new_elo}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar el jugador: {str(e)}', 'error')
    
    return redirect(url_for('routes.players'))

@routes.route('/players/bulk-update-elo')
@login_required
@admin_required
def bulk_update_elo():
    """Página para actualizar el ELO inicial de múltiples jugadores a la vez"""
    return render_template('bulk_update_elo.html')

@routes.route('/api/players', methods=['GET'])
@login_required
@admin_required
def api_get_players():
    """
    API para obtener la lista de todos los jugadores.
    """
    players_list = Player.query.all()
    
    # Preparar datos de jugadores
    players_data = []
    for player in players_list:
        current_elo = calculate_player_elo(player.id)  # Importado desde elo.py
        players_data.append({
            'id': player.id,
            'name': player.name,
            'elo': current_elo,
            'initial_elo': player.elo
        })
    
    # Ordenar jugadores por ELO
    players_data = sorted(players_data, key=lambda x: x['elo'], reverse=True)
    
    return jsonify({
        'status': 'success',
        'count': len(players_data),
        'players': players_data
    })

@routes.route('/api/players/update-elos', methods=['POST'])
@login_required
@admin_required
def api_update_players_elo():
    """
    API para actualizar los ELO iniciales de múltiples jugadores a la vez.
    """
    try:
        data = request.get_json()
        
        if not data or 'players' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Formato de datos inválido. Se espera un objeto JSON con una lista de jugadores.'
            }), 400
        
        players_data = data['players']
        updated_count = 0
        errors = []
        
        for player_data in players_data:
            # Verificar que el formato de los datos sea correcto
            if 'id' not in player_data or 'elo' not in player_data:
                errors.append(f'Datos de jugador inválidos: {player_data}')
                continue
            
            player_id = player_data['id']
            new_elo = player_data['elo']
            
            # Verificar que el ELO sea un número válido
            if not isinstance(new_elo, (int, float)) or new_elo < 0:
                errors.append(f'ELO inválido para el jugador {player_id}: {new_elo}')
                continue
            
            # Obtener el jugador de la base de datos
            player = db.session.get(Player, player_id)
            if not player:
                errors.append(f'Jugador con ID {player_id} no encontrado')
                continue
            
            # Actualizar el ELO inicial del jugador
            player.elo = int(new_elo)
            updated_count += 1
        
        # Guardar los cambios en la base de datos
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Se actualizaron {updated_count} jugadores correctamente',
            'updated_count': updated_count,
            'errors': errors
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Error al actualizar los jugadores: {str(e)}'
        }), 500

@routes.route('/api/player/<int:player_id>', methods=['GET', 'PUT', 'DELETE'])
def api_player(player_id):
    """
    API para gestionar un jugador específico.
    """
    try:
        # Obtener el jugador de la base de datos
        player = db.session.get(Player, player_id)
        if not player:
            return jsonify({
                'status': 'error',
                'message': f'Jugador con ID {player_id} no encontrado'
            }), 404
        
        if request.method == 'GET':
            # Obtener datos del jugador
            try:
                # Calcular ELO actual con manejo de errores
                try:
                    current_elo = calculate_player_elo(player_id)  # Importado desde elo.py
                except Exception as e:
                    current_app.logger.error(f"Error al calcular ELO: {str(e)}")
                    current_elo = player.elo  # Usar ELO inicial como fallback
                
                # Calcular cambio de ELO
                try:
                    elo_change = calculate_elo_change_between_last_matches(player_id)  # Importado desde elo.py
                except Exception as e:
                    current_app.logger.error(f"Error al calcular cambio de ELO: {str(e)}")
                    elo_change = 0
                
                # Obtener empates
                try:
                    draws = get_player_draws(player_id)  # Importado desde elo.py
                except Exception as e:
                    current_app.logger.error(f"Error al obtener empates: {str(e)}")
                    draws = 0
                
                return jsonify({
                    'status': 'success',
                    'player': {
                        'id': player.id,
                        'name': player.name,
                        'elo': current_elo,
                        'initial_elo': player.elo,
                        'elo_change': elo_change,
                        'draws': draws
                    }
                })
            except Exception as e:
                current_app.logger.error(f"Error en API player GET: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'Error interno: {str(e)}'
                }), 500
        
        elif request.method == 'PUT':
            try:
                data = request.get_json()
                
                # Actualizar nombre si se proporciona
                if 'name' in data:
                    new_name = data['name']
                    if not new_name or new_name.strip() == '':
                        return jsonify({
                            'status': 'error',
                            'message': 'El nombre del jugador es requerido'
                        }), 400
                    
                    # Verificar si el nombre ya existe (solo si ha cambiado)
                    if new_name != player.name:
                        existing_player = Player.query.filter(Player.name == new_name, Player.id != player_id).first()
                        if existing_player:
                            return jsonify({
                                'status': 'error',
                                'message': f'Ya existe un jugador con el nombre {new_name}'
                            }), 400
                    
                    player.name = new_name
                
                # Actualizar ELO inicial si se proporciona
                if 'initial_elo' in data:
                    new_elo = data['initial_elo']
                    if not isinstance(new_elo, (int, float)) or new_elo < 0:
                        return jsonify({
                            'status': 'error',
                            'message': f'ELO inválido: {new_elo}'
                        }), 400
                    
                    player.elo = int(new_elo)
                
                # Guardar los cambios en la base de datos
                db.session.commit()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Jugador actualizado correctamente',
                    'player': {
                        'id': player.id,
                        'name': player.name,
                        'elo': calculate_player_elo(player_id),  # Importado desde elo.py
                        'initial_elo': player.elo
                    }
                })
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error en API player PUT: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'Error al actualizar el jugador: {str(e)}'
                }), 500
        
        elif request.method == 'DELETE':
            try:
                # Verificar si el jugador tiene partidos asociados
                player_matches = PlayerMatch.query.filter_by(player_id=player_id).first()
                if player_matches:
                    return jsonify({
                        'status': 'error',
                        'message': 'No se puede eliminar el jugador porque tiene partidos asociados'
                    }), 400
                
                # Eliminar el jugador
                db.session.delete(player)
                db.session.commit()
                
                return jsonify({
                    'status': 'success',
                    'message': f'Jugador {player.name} eliminado correctamente'
                })
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error en API player DELETE: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'Error al eliminar el jugador: {str(e)}'
                }), 500
                
        else:
            return jsonify({
                'status': 'error',
                'message': 'Método no permitido'
            }), 405
            
    except Exception as e:
        current_app.logger.error(f"Error global en api_player: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error interno del servidor'
        }), 500

@routes.route('/api/player-elo-history', methods=['GET'])
def api_player_elo_history():
    """
    API para obtener el historial de ELO de los jugadores
    """
    try:
        # Obtener y validar parámetros
        player_ids = request.args.getlist('player_ids')
        limit = request.args.get('limit', 10, type=int)
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        interval = request.args.get('interval', 'match')
        
        # Validar intervalo
        if interval not in ['match', 'day', 'week', 'month']:
            return jsonify({'error': f'Invalid interval: {interval}. Must be one of: match, day, week, month'}), 400
        
        # Procesar fechas si se proporcionan
        from_date = None
        to_date = None
        if from_date_str:
            try:
                from_date = datetime.fromisoformat(from_date_str)
            except ValueError:
                return jsonify({'error': f'Invalid from_date format: {from_date_str}. Use ISO format (YYYY-MM-DD)'}), 400
        
        if to_date_str:
            try:
                to_date = datetime.fromisoformat(to_date_str)
            except ValueError:
                return jsonify({'error': f'Invalid to_date format: {to_date_str}. Use ISO format (YYYY-MM-DD)'}), 400
        
        # Verificar que from_date sea anterior a to_date si ambas están presentes
        if from_date and to_date and from_date > to_date:
            return jsonify({'error': 'from_date must be earlier than to_date'}), 400
        
        # Si no se especifican jugadores, usar los mejores según el límite
        if not player_ids:
            # Cache temporal para no recalcular ELO varias veces
            elo_cache = {}
            
            # Obtener todos los jugadores
            all_players = Player.query.all()
            top_players_data = []
            
            for player in all_players:
                # Usar la cache para evitar cálculos repetidos
                if player.id not in elo_cache:
                    try:
                        elo_cache[player.id] = calculate_player_elo(player.id)  # Importado desde elo.py
                    except Exception as e:
                        # Registrar error pero continuar con otros jugadores
                        current_app.logger.error(f"Error calculating ELO for player {player.id}: {str(e)}")
                        elo_cache[player.id] = 1000  # Valor por defecto
                
                top_players_data.append({
                    'id': player.id,
                    'name': player.name,
                    'elo': elo_cache[player.id]
                })
            
            # Ordenar y limitar
            top_players_data = sorted(top_players_data, key=lambda x: x['elo'], reverse=True)[:limit]
            player_ids = [str(p['id']) for p in top_players_data]
        
        # Convertir IDs a enteros
        try:
            player_ids = [int(pid) for pid in player_ids]
        except ValueError as e:
            return jsonify({'error': f'Invalid player_id format: {str(e)}'}), 400
        
        # Verificar existencia de los jugadores
        existing_players = Player.query.filter(Player.id.in_(player_ids)).all()
        existing_ids = [player.id for player in existing_players]
        missing_ids = set(player_ids) - set(existing_ids)
        
        if missing_ids:
            return jsonify({'error': f'Players not found: {list(missing_ids)}'}), 404
        
        # Construir consulta para partidos con filtros
        matches_query = Match.query.order_by(Match.date)
        
        if from_date:
            matches_query = matches_query.filter(Match.date >= from_date)
        if to_date:
            matches_query = matches_query.filter(Match.date <= to_date)
        
        matches = matches_query.all()
        
        if not matches:
            return jsonify({'error': 'No matches found for the specified criteria'}), 404
        
        elo_history = {}
        
        # Cache para la función calculate_player_elo_up_to_match
        elo_up_to_match_cache = {}
        # Cache para evitar recursión en calculate_player_elo_at_match_start
        elo_at_match_start_cache = {}
        
        for player_id in player_ids:
            player_elos = []
            player = Player.query.get(player_id)
            
            # Agrupar por intervalo si no es 'match'
            if interval == 'match':
                for match in matches:
                    # Usar key única para la cache
                    cache_key = f"{player_id}_{match.id}"
                    
                    if cache_key not in elo_up_to_match_cache:
                        try:
                            elo_up_to_match_cache[cache_key] = calculate_player_elo_up_to_match(
                                player_id, match.id, elo_up_to_match_cache, elo_at_match_start_cache
                            )  # Importado desde elo.py
                        except Exception as e:
                            current_app.logger.error(f"Error calculating ELO for player {player_id} up to match {match.id}: {str(e)}")
                            # Verificar si el jugador participó en este partido
                            participation = PlayerMatch.query.filter_by(player_id=player_id, match_id=match.id).first()
                            if not participation:
                                # Si no participó, usar el último ELO conocido o el inicial
                                if player_elos:
                                    elo_up_to_match_cache[cache_key] = player_elos[-1]['elo']
                                else:
                                    elo_up_to_match_cache[cache_key] = player.elo
                            else:
                                # Error en un partido en el que participó
                                elo_up_to_match_cache[cache_key] = None
                    
                    # Solo añadir puntos con valor de ELO válido
                    if elo_up_to_match_cache[cache_key] is not None:
                        player_elos.append({
                            'match_id': match.id,
                            'date': match.date.isoformat(),
                            'elo': elo_up_to_match_cache[cache_key]
                        })
            else:
                # Implementación para intervalos (day, week, month)
                interval_elos = {}
                
                for match in matches:
                    cache_key = f"{player_id}_{match.id}"
                    
                    if cache_key not in elo_up_to_match_cache:
                        try:
                            elo_up_to_match_cache[cache_key] = calculate_player_elo_up_to_match(
                                player_id, match.id, elo_up_to_match_cache, elo_at_match_start_cache
                            )  # Importado desde elo.py
                        except Exception as e:
                            current_app.logger.error(f"Error calculating ELO for player {player_id} up to match {match.id}: {str(e)}")
                            if player_elos:
                                elo_up_to_match_cache[cache_key] = player_elos[-1].get('elo', player.elo)
                            else:
                                elo_up_to_match_cache[cache_key] = player.elo
                    
                    # Determinar la clave del intervalo
                    if interval == 'day':
                        interval_key = match.date.date().isoformat()
                    elif interval == 'week':
                        # ISO week format: YYYY-WNN
                        year, week, _ = match.date.isocalendar()
                        interval_key = f"{year}-W{week:02d}"
                    elif interval == 'month':
                        interval_key = f"{match.date.year}-{match.date.month:02d}"
                    
                    # Almacenar el último ELO para cada intervalo
                    if elo_up_to_match_cache[cache_key] is not None:
                        interval_elos[interval_key] = {
                            'date': interval_key,
                            'elo': elo_up_to_match_cache[cache_key],
                            'match_id': match.id,
                            'match_date': match.date.isoformat()
                        }
                
                # Convertir de diccionario a lista y ordenar
                player_elos = list(interval_elos.values())
                player_elos.sort(key=lambda x: x['date'])
            
            elo_history[player_id] = {
                'player_name': player.name,
                'history': player_elos
            }
        
        return jsonify({
            'data': elo_history,
            'metadata': {
                'player_count': len(player_ids),
                'interval': interval,
                'from_date': from_date_str,
                'to_date': to_date_str,
                'match_count': len(matches)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in api_player_elo_history: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@routes.route('/change_password', methods=['GET', 'POST'])
@login_required
@admin_required
def change_password():
    """Change password for admin user"""
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validar que ambas contraseñas coincidan
        if new_password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('routes.change_password'))
        
        # Validar longitud mínima
        if len(new_password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres', 'danger')
            return redirect(url_for('routes.change_password'))
        
        user = User.query.filter_by(is_admin=True).first()  # Get the admin user
        
        if user:
            user.set_password(new_password)  # Set the new password
            db.session.commit()  # Save changes
            flash('Contraseña actualizada con éxito', 'success')
            return redirect(url_for('routes.index'))
        else:
            flash('Usuario admin no encontrado', 'danger')
            return redirect(url_for('routes.change_password'))
            
    return render_template('change_password.html')