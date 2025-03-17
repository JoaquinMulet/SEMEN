#!/usr/bin/env python
"""
Script para inicializar la base de datos con datos de prueba.
Ejecutar una sola vez después de crear la base de datos.
"""
from datetime import datetime, timedelta
from models import db, Player, Match, PlayerMatch, User, Venue, ScheduledMatch
import pytz

def initialize_database():
    """
    Inicializa la base de datos completa, incluida la creación de tablas
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        print("Creando tablas de la base de datos...")
        db.create_all()
        
        # Inicializar tablas con datos
        initialize_database_tables(app)

def initialize_database_tables(app):
    """
    Inicializa las tablas de la base de datos con datos de prueba
    Esta función puede ser llamada desde app.py para Railway
    """
    with app.app_context():
        # Verificar si ya hay datos
        if Player.query.count() > 0:
            print("La base de datos ya contiene datos. No se realizarán cambios.")
            return
            
        print("Insertando datos iniciales...")
        
        # Lista de jugadores iniciales
        players = [
            "Iñas", "Pete", "Rolo", "Peluca", "Aslan", "Esteban", "Agus", 
            "Claudio", "Gonza", "Manuel", "Martín", "Tato", "Simón", "Che", 
            "Buti", "Mulet", "Sergio", "Olayo", "Feli", "James", "Zuri", 
            "Niko", "Lukas", "Palli", "Pulga"
        ]
        
        # Añadir jugadores
        for name in players:
            player = Player(name=name)
            db.session.add(player)
        
        # Crear partidos de ejemplo
        match1 = Match(date=datetime.strptime("07-04-2024", "%d-%m-%Y"), winning_team=1)
        match2 = Match(date=datetime.strptime("14-04-2024", "%d-%m-%Y"), winning_team=1)
        db.session.add(match1)
        db.session.add(match2)
        
        db.session.commit()
        
        # Añadir jugadores a los partidos
        match1_team1 = ["Iñas", "Pete", "Rolo", "Peluca", "Aslan"]
        match1_team2 = ["Esteban", "Agus", "Claudio", "Gonza", "Manuel"]
        match2_team1 = ["Martín", "Tato", "Simón", "Che", "Buti"]
        match2_team2 = ["Mulet", "Sergio", "Olayo", "Feli", "James"]
        
        # Asignar jugadores al primer partido
        for name in match1_team1:
            player = Player.query.filter_by(name=name).first()
            if player:
                db.session.add(PlayerMatch(player_id=player.id, match_id=match1.id, team=1))
        
        for name in match1_team2:
            player = Player.query.filter_by(name=name).first()
            if player:
                db.session.add(PlayerMatch(player_id=player.id, match_id=match1.id, team=2))
        
        # Asignar jugadores al segundo partido
        for name in match2_team1:
            player = Player.query.filter_by(name=name).first()
            if player:
                db.session.add(PlayerMatch(player_id=player.id, match_id=match2.id, team=1))
        
        for name in match2_team2:
            player = Player.query.filter_by(name=name).first()
            if player:
                db.session.add(PlayerMatch(player_id=player.id, match_id=match2.id, team=2))
        
        # Crear usuario administrador
        if User.query.filter_by(username='admin').first() is None:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')  # Contraseña por defecto, debería cambiarse
            db.session.add(admin)
        
        # Crear sedes
        venues = [
            {"name": "Cancha Tobalaba", "address": "Av. Tobalaba 123", "description": "Cancha techada con pasto sintético"},
            {"name": "Cancha Peñalolén", "address": "Los Presidentes 555", "description": "Cancha al aire libre con pasto sintético"},
            {"name": "Cancha Las Condes", "address": "Apoquindo 3000", "description": "Cancha techada con pasto sintético"}
        ]
        
        for venue_data in venues:
            venue = Venue(**venue_data)
            db.session.add(venue)
        
        db.session.commit()
        
        # Crear partidos programados (algunos pasados, algunos futuros)
        now_utc = pytz.utc.localize(datetime.utcnow())
        
        # Partido pasado (finalizado)
        past_match = ScheduledMatch(
            match_date=now_utc - timedelta(days=7),
            venue_id=1,
            players_per_team=5,
            registration_open_date=now_utc - timedelta(days=14),
            is_active=True,
            is_finished=True
        )
        db.session.add(past_match)
        
        # Partido pasado (por finalizar)
        past_match2 = ScheduledMatch(
            match_date=now_utc - timedelta(days=3),
            venue_id=2,
            players_per_team=6,
            registration_open_date=now_utc - timedelta(days=10),
            is_active=True,
            is_finished=False
        )
        db.session.add(past_match2)
        
        # Partido futuro (inscripciones abiertas)
        future_match = ScheduledMatch(
            match_date=now_utc + timedelta(days=7),
            venue_id=3,
            players_per_team=5,
            registration_open_date=now_utc - timedelta(days=2),
            is_active=True,
            is_finished=False
        )
        db.session.add(future_match)
        
        # Partido futuro (inscripciones próximamente)
        future_match2 = ScheduledMatch(
            match_date=now_utc + timedelta(days=14),
            venue_id=1,
            players_per_team=6,
            registration_open_date=now_utc + timedelta(days=2),
            is_active=True,
            is_finished=False
        )
        db.session.add(future_match2)
        
        db.session.commit()
        print("Base de datos inicializada con datos de prueba")

if __name__ == "__main__":
    initialize_database()