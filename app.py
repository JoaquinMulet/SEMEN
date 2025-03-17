from flask import Flask, render_template
from models import db, Player, Match, PlayerMatch, User
from routes import routes
from flask_login import LoginManager
import os
from dotenv import load_dotenv
import logging
import sqlite3

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
    
    # Para diagnóstico: mostrar directorio actual y contenido
    current_dir = os.getcwd()
    logger.info(f"Directorio actual: {current_dir}")
    
    # Comprobar si existe la carpeta instance y su contenido
    instance_dir = os.path.join(current_dir, 'instance')
    if os.path.exists(instance_dir):
        logger.info(f"Carpeta instance encontrada: {instance_dir}")
        instance_files = os.listdir(instance_dir)
        logger.info(f"Contenido de instance: {instance_files}")
    
    # Configurar la base de datos
    if volume_path and os.path.exists(volume_path):
        # Estamos en Railway con un volumen
        logger.info("Entorno detectado: Railway con volumen")
        
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
                
                # Verificar si la base de datos es válida
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    logger.info(f"Tablas encontradas en la BD: {tables}")
                    conn.close()
                except Exception as e:
                    logger.error(f"Error al acceder a la BD en {db_path}: {str(e)}")
                    db_path = None  # Resetear path si no podemos acceder
                
                if db_path:  # Si aún tenemos un path válido después de la verificación
                    break
        
        # Si no se encuentra la base de datos, usar una ubicación predeterminada
        if not db_path:
            db_path = os.path.join(volume_path, 'football_league.db')
            logger.info(f"No se encontró base de datos existente, se usará: {db_path}")
        
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        logger.info(f"Usando base de datos en volumen: {db_path}")
    else:
        # Estamos en entorno local o en Railway sin volumen
        logger.info("Entorno detectado: Local o Railway sin volumen")
        
        # Si no hay volumen, verificar DATABASE_URL para postgresql o usar SQLite local
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # SQLAlchemy no acepta postgresql:// URLs, sino postgresql+psycopg2://
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url
            logger.info(f"Usando base de datos remota: {database_url}")
        else:
            # Usar SQLite local en la carpeta instance
            instance_folder = os.path.join(current_dir, 'instance')
            if not os.path.exists(instance_folder):
                os.makedirs(instance_folder)
                logger.info(f"Creada carpeta instance: {instance_folder}")
            
            db_path = os.path.join(instance_folder, 'football_league.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
            logger.info(f"Usando base de datos SQLite local: {db_path}")
            
            # Verificar si la base de datos local existe
            if os.path.exists(db_path):
                logger.info(f"Base de datos local encontrada en: {db_path}")
                
                # Verificar si la base de datos es válida
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    logger.info(f"Tablas encontradas en la BD local: {tables}")
                    conn.close()
                except Exception as e:
                    logger.error(f"Error al acceder a la BD local en {db_path}: {str(e)}")
            else:
                logger.info(f"No se encontró base de datos local en: {db_path}")
    
    # Configurar SQLAlchemy para mostrar consultas SQL
    app.config['SQLALCHEMY_ECHO'] = True
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
    
    # Diagnóstico de conexión a la base de datos
    with app.app_context():
        try:
            # Intentamos hacer una consulta sencilla a cada tabla
            logger.info("Diagnóstico: Verificando tablas en la base de datos...")
            
            # Verificar tabla User
            try:
                users = User.query.limit(1).all()
                logger.info(f"Diagnóstico: Conexión a tabla User exitosa. Encontrados: {len(users)} registros (limitado a 1)")
            except Exception as e:
                logger.error(f"Diagnóstico: Error al acceder a tabla User: {str(e)}")
            
            # Verificar tabla Player
            try:
                players = Player.query.limit(1).all()
                logger.info(f"Diagnóstico: Conexión a tabla Player exitosa. Encontrados: {len(players)} registros (limitado a 1)")
            except Exception as e:
                logger.error(f"Diagnóstico: Error al acceder a tabla Player: {str(e)}")
            
            # Verificar tabla Match
            try:
                matches = Match.query.limit(1).all()
                logger.info(f"Diagnóstico: Conexión a tabla Match exitosa. Encontrados: {len(matches)} registros (limitado a 1)")
            except Exception as e:
                logger.error(f"Diagnóstico: Error al acceder a tabla Match: {str(e)}")
            
            # Si la variable de entorno FORCE_DB_CREATE está definida, crear las tablas
            if os.getenv('FORCE_DB_CREATE') == 'true':
                logger.info("Forzando creación de tablas debido a FORCE_DB_CREATE=true")
                db.create_all()
                logger.info("Creación de tablas completada")
            
            # Solo inicializar la base de datos si se solicita explícitamente
            if os.getenv('INIT_DB') == 'true':
                try:
                    from init_db import initialize_database_tables
                    initialize_database_tables(app)
                    logger.info("Base de datos inicializada")
                except Exception as e:
                    logger.error(f"Error al inicializar la base de datos: {str(e)}")
        except Exception as e:
            logger.error(f"Error general con la base de datos: {str(e)}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)