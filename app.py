from flask import Flask, render_template
from models import db, Player, Match, PlayerMatch, User
from routes import routes
from flask_login import LoginManager
import os
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Obtener la ruta del volumen de Railway
    volume_path = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    logger.info(f"Railway volume path: {volume_path}")
    
    # Configurar la base de datos
    if volume_path and os.path.exists(volume_path):
        # Buscar la base de datos en diferentes ubicaciones posibles en el volumen
        possible_locations = [
            os.path.join(volume_path, 'football_league.db'),  # Directorio raíz del volumen
            os.path.join(volume_path, 'db', 'football_league.db'),  # Subdirectorio db
            os.path.join(volume_path, 'instance', 'football_league.db')  # Subdirectorio instance
        ]
        
        db_path = None
        for location in possible_locations:
            if os.path.exists(location):
                db_path = location
                logger.info(f"Base de datos existente encontrada en: {db_path}")
                break
        
        # Si no se encuentra la base de datos, usar una ubicación predeterminada
        if not db_path:
            db_path = os.path.join(volume_path, 'football_league.db')
            logger.info(f"No se encontró base de datos existente, se usará: {db_path}")
        
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        logger.info(f"Usando base de datos en volumen: {db_path}")
    else:
        # Si no hay volumen, verificar DATABASE_URL para postgresql o usar SQLite local
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # SQLAlchemy no acepta postgresql:// URLs, sino postgresql+psycopg2://
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url
            logger.info(f"Usando base de datos remota: {database_url}")
        else:
            # Usar SQLite local si no hay configuración
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/football_league.db'
            logger.info("Usando base de datos SQLite local")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    
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
    
    # Si encontramos una base de datos existente en el volumen, no intentamos crear tablas
    with app.app_context():
        try:
            # Solo crear tablas si la variable de entorno está definida o no estamos en un volumen
            if os.getenv('FORCE_DB_CREATE') == 'true' or not volume_path:
                logger.info("Verificando y creando tablas de base de datos si es necesario")
                db.create_all()
                logger.info("Verificación/creación de tablas completada")
            else:
                logger.info("Usando base de datos existente, omitiendo creación de tablas")
            
            # Solo inicializar la base de datos si se solicita explícitamente
            if os.getenv('INIT_DB') == 'true':
                try:
                    from init_db import initialize_database_tables
                    initialize_database_tables(app)
                    logger.info("Base de datos inicializada en Railway")
                except Exception as e:
                    logger.error(f"Error al inicializar la base de datos: {str(e)}")
        except Exception as e:
            logger.error(f"Error con la base de datos: {str(e)}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)