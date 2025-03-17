from flask import Flask, render_template
from models import db, Player, Match, PlayerMatch, User
from routes import routes
from flask_login import LoginManager
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configure the SQLite database (o PostgreSQL en Railway)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///football_league.db')
    
    # SQLAlchemy no acepta postgresql:// URLs, sino postgresql+psycopg2://
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    
    # Código a añadir en app.py cerca de la configuración de la base de datos
    volume_path = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    if volume_path and os.path.exists(os.path.join(volume_path, 'instance', 'football_league.db')):
        db_path = os.path.join(volume_path, 'instance', 'football_league.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        print(f"Usando base de datos en volumen: {db_path}")

    # Initialize the database
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        from flask import current_app
        with current_app.app_context():
            return db.session.get(User, int(user_id))
    
    # Register blueprints
    app.register_blueprint(routes)
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        
        # Si la variable de entorno INIT_DB está establecida, inicializar la base de datos
        # (útil para Railway)
        if os.getenv('INIT_DB') == 'true':
            try:
                from init_db import initialize_database_tables
                initialize_database_tables(app)
                print("Base de datos inicializada en Railway")
            except Exception as e:
                print(f"Error al inicializar la base de datos: {str(e)}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)