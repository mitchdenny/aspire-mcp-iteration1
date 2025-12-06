"""Weather Sync Service - Fetches weather data from Open-Meteo API and stores in PostgreSQL."""

import asyncio
import contextlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fastapi
import fastapi.responses
import httpx
import opentelemetry.instrumentation.fastapi as otel_fastapi
import opentelemetry.instrumentation.httpx as otel_httpx
import psycopg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from psycopg.rows import dict_row

import telemetry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Open-Meteo API - Free, no API key required
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"

# Global scheduler
scheduler = AsyncIOScheduler()

# Database connection string
db_connection_string: str | None = None


def get_db_connection_string() -> str | None:
    """Get the database connection string from environment."""
    global db_connection_string
    if db_connection_string is None:
        # Prefer the URI format which is compatible with psycopg
        db_connection_string = os.environ.get("WEATHERDB_URI")
        
        if not db_connection_string:
            # Build connection string from individual components
            host = os.environ.get("WEATHERDB_HOST")
            port = os.environ.get("WEATHERDB_PORT", "5432")
            user = os.environ.get("WEATHERDB_USERNAME", "postgres")
            password = os.environ.get("WEATHERDB_PASSWORD", "")
            database = os.environ.get("WEATHERDB_DATABASE", "weatherdb")
            
            if host:
                db_connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        if db_connection_string:
            logger.info("Found database connection string")
        else:
            logger.warning("No database connection string found in environment")
    return db_connection_string


async def get_db_connection():
    """Get an async database connection."""
    conn_str = get_db_connection_string()
    if not conn_str:
        raise ValueError("No database connection string available")
    return await psycopg.AsyncConnection.connect(conn_str, row_factory=dict_row)


async def initialize_database():
    """Initialize the database schema if it doesn't exist."""
    logger.info("Initializing database schema...")
    
    # Read the init.sql file
    init_sql_path = Path(__file__).parent.parent / "db" / "init.sql"
    if not init_sql_path.exists():
        logger.warning(f"init.sql not found at {init_sql_path}")
        return
    
    init_sql = init_sql_path.read_text()
    
    try:
        async with await get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(init_sql)
            await conn.commit()
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def weather_code_to_description(code: int) -> tuple[str, str]:
    """Convert Open-Meteo weather code to description and icon."""
    weather_codes = {
        0: ("Clear sky", "☀️"),
        1: ("Mainly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫️"),
        48: ("Depositing rime fog", "🌫️"),
        51: ("Light drizzle", "🌧️"),
        53: ("Moderate drizzle", "🌧️"),
        55: ("Dense drizzle", "🌧️"),
        56: ("Light freezing drizzle", "🌨️"),
        57: ("Dense freezing drizzle", "🌨️"),
        61: ("Slight rain", "🌧️"),
        63: ("Moderate rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),
        66: ("Light freezing rain", "🌨️"),
        67: ("Heavy freezing rain", "🌨️"),
        71: ("Slight snow fall", "❄️"),
        73: ("Moderate snow fall", "❄️"),
        75: ("Heavy snow fall", "❄️"),
        77: ("Snow grains", "❄️"),
        80: ("Slight rain showers", "🌦️"),
        81: ("Moderate rain showers", "🌦️"),
        82: ("Violent rain showers", "🌦️"),
        85: ("Slight snow showers", "🌨️"),
        86: ("Heavy snow showers", "🌨️"),
        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with slight hail", "⛈️"),
        99: ("Thunderstorm with heavy hail", "⛈️"),
    }
    return weather_codes.get(code, ("Unknown", "❓"))


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32


async def fetch_weather_for_city(
    client: httpx.AsyncClient, city: dict[str, Any]
) -> dict[str, Any] | None:
    """Fetch weather data for a single city from Open-Meteo API."""
    try:
        params = {
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "weather_code",
                "pressure_msl",
                "wind_speed_10m",
                "wind_direction_10m",
                "cloud_cover",
            ],
            "timezone": city.get("timezone", "auto"),
        }

        response = await client.get(OPEN_METEO_API, params=params)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        weather_code = current.get("weather_code", 0)
        description, icon = weather_code_to_description(weather_code)

        temp_c = current.get("temperature_2m", 0)
        feels_like_c = current.get("apparent_temperature", temp_c)

        return {
            "city_id": city["id"],
            "temperature_c": temp_c,
            "temperature_f": celsius_to_fahrenheit(temp_c),
            "feels_like_c": feels_like_c,
            "feels_like_f": celsius_to_fahrenheit(feels_like_c),
            "humidity": current.get("relative_humidity_2m"),
            "pressure": current.get("pressure_msl"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "description": description,
            "icon": icon,
            "visibility": None,  # Not available in Open-Meteo free tier
            "clouds": current.get("cloud_cover"),
            "recorded_at": datetime.now(timezone.utc),
        }
    except Exception as e:
        logger.error(f"Error fetching weather for {city['name']}: {e}")
        return None


async def sync_weather_data():
    """Sync weather data for all cities in the database."""
    logger.info("Starting weather data sync...")

    try:
        async with await get_db_connection() as conn:
            # Get all cities
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, name, country, latitude, longitude, timezone FROM cities"
                )
                cities = await cur.fetchall()

            if not cities:
                logger.warning("No cities found in database")
                return

            logger.info(f"Syncing weather for {len(cities)} cities")

            # Fetch weather data for all cities concurrently
            async with httpx.AsyncClient(timeout=30.0) as client:
                tasks = [fetch_weather_for_city(client, city) for city in cities]
                results = await asyncio.gather(*tasks)

            # Filter out None results
            weather_data = [r for r in results if r is not None]

            if weather_data:
                # Insert weather data
                async with conn.cursor() as cur:
                    insert_query = """
                        INSERT INTO weather_data (
                            city_id, temperature_c, temperature_f, feels_like_c, feels_like_f,
                            humidity, pressure, wind_speed, wind_direction, description,
                            icon, visibility, clouds, recorded_at
                        ) VALUES (
                            %(city_id)s, %(temperature_c)s, %(temperature_f)s, %(feels_like_c)s,
                            %(feels_like_f)s, %(humidity)s, %(pressure)s, %(wind_speed)s,
                            %(wind_direction)s, %(description)s, %(icon)s, %(visibility)s,
                            %(clouds)s, %(recorded_at)s
                        )
                    """
                    await cur.executemany(insert_query, weather_data)

                await conn.commit()
                logger.info(
                    f"Successfully synced weather data for {len(weather_data)} cities"
                )
            else:
                logger.warning("No weather data was fetched")

    except Exception as e:
        logger.error(f"Error during weather sync: {e}")
        raise


async def cleanup_old_data():
    """Remove weather data older than 7 days to prevent database bloat."""
    logger.info("Cleaning up old weather data...")
    try:
        async with await get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM weather_data 
                    WHERE recorded_at < NOW() - INTERVAL '7 days'
                """
                )
                deleted = cur.rowcount
            await conn.commit()
            logger.info(f"Deleted {deleted} old weather records")
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")


@contextlib.asynccontextmanager
async def lifespan(app):
    """Application lifespan handler."""
    telemetry.configure_opentelemetry()
    otel_httpx.HTTPXClientInstrumentor().instrument()

    # Wait a bit for database to be ready
    await asyncio.sleep(5)

    # Initialize database schema
    max_retries = 10
    for attempt in range(max_retries):
        try:
            await initialize_database()
            break
        except Exception as e:
            logger.warning(f"Database init attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                logger.error("Failed to initialize database after all retries")

    # Run initial sync
    try:
        await sync_weather_data()
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")

    # Schedule periodic sync every 15 minutes
    scheduler.add_job(sync_weather_data, "interval", minutes=15, id="weather_sync")
    # Schedule cleanup every day
    scheduler.add_job(cleanup_old_data, "interval", hours=24, id="cleanup")
    scheduler.start()

    logger.info("Weather sync service started")
    yield

    scheduler.shutdown()
    logger.info("Weather sync service stopped")


app = fastapi.FastAPI(lifespan=lifespan, title="Weather Sync Service")
otel_fastapi.FastAPIInstrumentor.instrument_app(app, exclude_spans=["send"])


@app.get("/health", response_class=fastapi.responses.PlainTextResponse)
async def health_check():
    """Health check endpoint."""
    return "Healthy"


@app.post("/sync")
async def trigger_sync():
    """Manually trigger a weather sync."""
    try:
        await sync_weather_data()
        return {"status": "success", "message": "Weather data synced successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/status")
async def get_status():
    """Get the sync service status."""
    try:
        async with await get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) as count FROM cities")
                cities = (await cur.fetchone())["count"]

                await cur.execute("SELECT COUNT(*) as count FROM weather_data")
                weather_records = (await cur.fetchone())["count"]

                await cur.execute(
                    "SELECT MAX(recorded_at) as last_sync FROM weather_data"
                )
                last_sync = (await cur.fetchone())["last_sync"]

        return {
            "status": "running",
            "cities_count": cities,
            "weather_records": weather_records,
            "last_sync": last_sync.isoformat() if last_sync else None,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
