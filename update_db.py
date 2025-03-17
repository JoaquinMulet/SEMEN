from flask import Flask
from models import db
import os
from dotenv import load_dotenv
from sqlalchemy import text

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Configurar la misma base de datos que tu aplicación principal
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///football_league.db')
# SQLAlchemy no acepta postgresql:// URLs, sino postgresql+psycopg2://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar la base de datos
db.init_app(app)

with app.app_context():
    try:
        # Para SQLite, necesitas usar text() para declarar explícitamente el SQL
        db.session.execute(text("ALTER TABLE scheduled_match ADD COLUMN is_finished BOOLEAN DEFAULT 0"))
        db.session.commit()
        print("✅ Columna 'is_finished' añadida correctamente a la tabla 'scheduled_match'")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al añadir la columna: {str(e)}")
        print("Es posible que la columna ya exista o haya otro problema con la base de datos.")