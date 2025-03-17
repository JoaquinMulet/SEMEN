# Sistema de Gestión de Liga de Fútbol

Este sistema permite gestionar una liga de fútbol, incluyendo jugadores, partidos, sedes, y un sistema de rankings basado en ELO.

## Estructura del Proyecto

- `app.py` - Aplicación principal Flask
- `models.py` - Modelos de datos (Player, Match, etc.)
- `routes.py` - Rutas y controladores de la aplicación
- `elo.py` - Funciones para cálculos de puntuación ELO
- `team_formation.py` - Algoritmos para formar equipos equilibrados
- `init_db.py` - Script para inicializar la base de datos con datos de prueba
- `/templates` - Plantillas HTML
- `/static` - Archivos estáticos (CSS, JS, imágenes)

## Configuración Inicial (Local)

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Inicializar la base de datos

Para crear la estructura de la base de datos y cargar datos iniciales de prueba, ejecuta:

```bash
python init_db.py
```

Este script:
- Crea todas las tablas necesarias
- Agrega 25 jugadores iniciales
- Crea dos partidos de ejemplo
- Agrega datos de sedes y partidos programados
- Configura un usuario administrador (usuario: `admin`, contraseña: `admin123`)

### 3. Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en http://localhost:5000

## Despliegue en Railway

Railway es una plataforma que facilita el despliegue de aplicaciones web. A continuación se detallan los pasos para desplegar esta aplicación en Railway:

### 1. Preparar el proyecto para Railway

1. Asegúrate de tener un archivo `Procfile` en la raíz del proyecto con el siguiente contenido:

```
web: gunicorn "app:create_app()"
```

2. Crea un archivo `.env` para las variables de entorno (no lo subas al repositorio):

```
SECRET_KEY=tu_clave_secreta_aqui
DATABASE_URL=sqlite:///football_league.db
```

3. Modifica `app.py` para que utilice variables de entorno (si no lo hace ya):

```python
# Añade esto cerca del inicio de app.py
import os
from dotenv import load_dotenv

load_dotenv()
```

```python
# En la función create_app(), modifica la configuración:
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///football_league.db')
```

### 2. Desplegar en Railway

1. Crea una cuenta en [Railway](https://railway.app/) si aún no tienes una.

2. Instala la CLI de Railway (opcional, pero útil):

```bash
npm i -g @railway/cli
```

3. Inicia sesión:

```bash
railway login
```

4. Inicia un nuevo proyecto:

```bash
railway init
```

5. Sube el proyecto:

```bash
railway up
```

6. Configura las variables de entorno en el panel de Railway:
   - SECRET_KEY
   - DATABASE_URL (Railway proporcionará automáticamente esta variable para PostgreSQL)

7. Inicializa la base de datos:
   - En el panel de Railway, ve a la pestaña "Settings"
   - Ve a la sección "Environment Variables"
   - Agrega una variable temporal INIT_DB=true
   - Modifica `app.py` para que detecte esta variable y ejecute la inicialización:

```python
# En la función create_app(), después de db.create_all():
if os.getenv('INIT_DB') == 'true':
    # Importa la función
    from init_db import initialize_database_tables
    # Inicializa tablas y datos
    initialize_database_tables(app)
    print("Base de datos inicializada en Railway")
```

8. Una vez inicializada la base de datos, elimina o desactiva la variable INIT_DB.

### 3. Configurar dominio personalizado (opcional)

1. En el panel de Railway, ve a la pestaña "Settings"
2. Busca la sección "Domains"
3. Haz clic en "Generate Domain" o configura tu dominio personalizado

## Acceso al Sistema

- **URL Local**: http://localhost:5000
- **URL Railway**: Proporcionado por Railway después del despliegue
- **Usuario Administrador**: admin
- **Contraseña**: admin123 (cambiar después del primer inicio de sesión)

## Características Principales

- Gestión de jugadores con sistema de puntuación ELO
- Registro de partidos con equipos y resultados
- Programación de partidos futuros en sedes específicas
- Sistema de inscripción para jugadores
- Algoritmo para formar equipos equilibrados
- Análisis de desempeño de jugadores
- Sección de históricos para ver partidos pasados o finalizados
- Posibilidad de formar equipos a partir de asistentes a partidos históricos

## Modelo ELO

El sistema utiliza un modelo de puntuación ELO adaptado para equipos, donde:

- Cada jugador comienza con un ELO inicial de 1000
- El ELO se ajusta después de cada partido basado en:
  - Resultado del partido (victoria/derrota/empate)
  - Diferencia de ELO entre equipos
  - Diferencia de goles/puntos

## Gestión de Partidos

El sistema organiza los partidos en dos categorías:

### Próximos Partidos
- Partidos programados que aún no han ocurrido
- Permite inscripción de jugadores cuando está habilitada
- Muestra estado actual (Pendiente, Inscripciones Abiertas, Completo, etc.)

### Partidos Históricos
- Partidos pasados o marcados como finalizados
- Muestra resumen de asistencia y estado final
- Permite formar equipos con los jugadores que asistieron
- Útil para revisar estadísticas pasadas

## Desarrollo

Para modificar o extender la aplicación:

1. El archivo `elo.py` contiene todas las funciones relacionadas con cálculos de ELO
2. `team_formation.py` contiene algoritmos para formar equipos equilibrados
3. Las rutas en `routes.py` están organizadas por funcionalidad
4. Los modelos en `models.py` definen la estructura de la base de datos

## Notas

- La aplicación utiliza SQLite como base de datos por defecto (PostgreSQL en Railway)
- Para entornos de producción, se recomienda cambiar la SECRET_KEY en app.py
- Cambiar la contraseña del administrador después del primer inicio de sesión