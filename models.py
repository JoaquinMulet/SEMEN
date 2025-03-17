#Models
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Player(db.Model):
    """Player model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    elo = db.Column(db.Integer, default=1000)  # ELO inicial del jugador
    matches = db.relationship('PlayerMatch', backref='player', lazy=True)
    registrations = db.relationship('Registration', backref='player', lazy=True)
    
    def __repr__(self):
        return f'<Player {self.name}>'

class Match(db.Model):
    """Match model"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    winning_team = db.Column(db.Integer, nullable=False)  # 1 or 2 or 0 for draw
    team1_score = db.Column(db.Integer, nullable=False, default=0)
    team2_score = db.Column(db.Integer, nullable=False, default=0)
    players = db.relationship('PlayerMatch', backref='match', lazy=True)
    
    def __repr__(self):
        return f'<Match {self.id} on {self.date}, Result: {self.team1_score}-{self.team2_score}>'

class PlayerMatch(db.Model):
    """Association table between Player and Match"""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    team = db.Column(db.Integer, nullable=False)  # 1 or 2
    elo_before = db.Column(db.Integer, nullable=False)
    elo_after = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<PlayerMatch {self.player_id} in match {self.match_id}>'

class Venue(db.Model):
    """Venue model for match locations"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_matches = db.relationship('ScheduledMatch', backref='venue', lazy=True)
    
    def __repr__(self):
        return f'<Venue {self.name}>'

class ScheduledMatch(db.Model):
    """Model for scheduled matches"""
    id = db.Column(db.Integer, primary_key=True)
    match_date = db.Column(db.DateTime, nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    players_per_team = db.Column(db.Integer, nullable=False, default=5)
    registration_open_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_finished = db.Column(db.Boolean, default=False)  # Nuevo campo para indicar si el partido ya finalizó
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    registrations = db.relationship('Registration', backref='scheduled_match', lazy=True)
    
    def __repr__(self):
        return f'<ScheduledMatch on {self.match_date} at {self.venue.name}>'
    
    @property
    def total_players_needed(self):
        """Get the total number of players needed for the match"""
        return self.players_per_team * 2
    
    @property
    def is_registration_open(self):
        """Check if registration is currently open"""
        import pytz
        
        # Asegurarse de que la fecha actual tenga zona horaria UTC
        now = pytz.utc.localize(datetime.utcnow())
        
        # Asegurarse de que registration_open_date tenga zona horaria
        registration_open_date = self.registration_open_date
        if registration_open_date.tzinfo is None:
            registration_open_date = pytz.utc.localize(registration_open_date)
        
        return (now >= registration_open_date and 
                self.is_active and 
                len(self.registrations) < self.total_players_needed)
    
    @property
    def registered_players_count(self):
        """Get the number of registered players"""
        return len(self.registrations)
    
    @property
    def is_past(self):
        """Check if the match date has passed"""
        import pytz
        
        # Asegurarse de que la fecha actual tenga zona horaria UTC
        now = pytz.utc.localize(datetime.utcnow())
        
        # Asegurarse de que match_date tenga zona horaria
        match_date = self.match_date
        if match_date.tzinfo is None:
            match_date = pytz.utc.localize(match_date)
        
        return now > match_date
    
    @property
    def status(self):
        """Return the status of the match"""
        if not self.is_active:
            return "Cancelado"
        
        if self.is_finished:
            return "Finalizado"
            
        if self.is_past:
            return "Por finalizar"  # Partidos pasados que no han sido marcados como finalizados
            
        if self.is_registration_open:
            return "Inscripciones Abiertas"
            
        if self.registered_players_count >= self.total_players_needed:
            return "Completo"
            
        import pytz
        now = pytz.utc.localize(datetime.utcnow())
        registration_open_date = self.registration_open_date
        if registration_open_date.tzinfo is None:
            registration_open_date = pytz.utc.localize(registration_open_date)
            
        if registration_open_date > now:
            return "Pendiente"
            
        return "Cerrado"

class Registration(db.Model):
    """Model for player registrations to scheduled matches"""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    scheduled_match_id = db.Column(db.Integer, db.ForeignKey('scheduled_match.id'), nullable=False)
    registration_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('player_id', 'scheduled_match_id', name='unique_player_match_registration'),
    )
    
    def __repr__(self):
        return f'<Registration {self.player.name} for match {self.scheduled_match_id}>'
