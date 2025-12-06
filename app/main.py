import contextlib
import datetime
import json
import logging
import os
import random

import fastapi
import fastapi.responses
import fastapi.staticfiles
import opentelemetry.instrumentation.fastapi as otel_fastapi
import opentelemetry.instrumentation.redis as otel_redis
import opentelemetry.instrumentation.psycopg as otel_psycopg
import psycopg
from psycopg.rows import dict_row
import redis
import telemetry


@contextlib.asynccontextmanager
async def lifespan(app):
    telemetry.configure_opentelemetry()
    yield


app = fastapi.FastAPI(lifespan=lifespan)
otel_fastapi.FastAPIInstrumentor.instrument_app(app, exclude_spans=["send"])

# Create a global to store the Redis client.
redis_client = None
otel_redis.RedisInstrumentor().instrument()
otel_psycopg.PsycopgInstrumentor().instrument()

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
        return None
    try:
        return await psycopg.AsyncConnection.connect(conn_str, row_factory=dict_row)
    except Exception as e:
        logger.warning(f"Failed to connect to database: {e}")
        return None


def get_redis_client():
    """Get the Redis client instance."""
    global redis_client
    if redis_client is None:
        if cache_uri := os.environ.get("CACHE_URI"):
            try:
                redis_client = redis.from_url(
                    cache_uri,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    decode_responses=True,
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                redis_client = None
        else:
            logger.info(
                "No CACHE_URI environment variable found, Redis caching disabled"
            )
    return redis_client


logger = logging.getLogger(__name__)


if not os.path.exists("static"):
    @app.get("/", response_class=fastapi.responses.HTMLResponse)
    async def root():
        """Root endpoint."""
        return "API service is running. Navigate to <a href='/api/weatherforecast'>/api/weatherforecast</a> to see sample data."


@app.get("/api/cities")
async def get_cities(redis_client=fastapi.Depends(get_redis_client)):
    """Get all cities with their latest weather data."""
    cache_key = "cities_weather"
    cache_ttl = 60  # 1 minute cache duration

    # Try to get data from cache
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.info("Returning cached cities weather data")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    # Get data from database
    conn = await get_db_connection()
    if conn:
        try:
            async with conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            city_id as id,
                            city_name as name,
                            country,
                            country_code,
                            latitude,
                            longitude,
                            population,
                            timezone,
                            temperature_c,
                            temperature_f,
                            feels_like_c,
                            feels_like_f,
                            humidity,
                            pressure,
                            wind_speed,
                            wind_direction,
                            description,
                            icon,
                            clouds,
                            recorded_at
                        FROM latest_weather
                        ORDER BY city_name
                    """)
                    rows = await cur.fetchall()

            cities = []
            for row in rows:
                city = dict(row)
                # Convert Decimal types to float and datetime to ISO string
                for key, value in city.items():
                    if hasattr(value, 'quantize'):  # Decimal
                        city[key] = float(value)
                    elif hasattr(value, 'isoformat'):  # datetime
                        city[key] = value.isoformat()
                cities.append(city)

            # Cache the data
            if redis_client and cities:
                try:
                    redis_client.setex(cache_key, cache_ttl, json.dumps(cities))
                except Exception as e:
                    logger.warning(f"Redis cache write error: {e}")

            return cities
        except Exception as e:
            logger.error(f"Database error: {e}")

    # Return empty list if no database connection
    return []


@app.get("/api/cities/{city_id}")
async def get_city_weather(city_id: int, redis_client=fastapi.Depends(get_redis_client)):
    """Get weather data for a specific city."""
    cache_key = f"city_weather_{city_id}"
    cache_ttl = 60

    # Try to get data from cache
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    conn = await get_db_connection()
    if conn:
        try:
            async with conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            city_id as id,
                            city_name as name,
                            country,
                            country_code,
                            latitude,
                            longitude,
                            population,
                            timezone,
                            temperature_c,
                            temperature_f,
                            feels_like_c,
                            feels_like_f,
                            humidity,
                            pressure,
                            wind_speed,
                            wind_direction,
                            description,
                            icon,
                            clouds,
                            recorded_at
                        FROM latest_weather
                        WHERE city_id = %s
                    """, (city_id,))
                    row = await cur.fetchone()

            if row:
                city = dict(row)
                for key, value in city.items():
                    if hasattr(value, 'quantize'):
                        city[key] = float(value)
                    elif hasattr(value, 'isoformat'):
                        city[key] = value.isoformat()

                # Cache the data
                if redis_client:
                    try:
                        redis_client.setex(cache_key, cache_ttl, json.dumps(city))
                    except Exception as e:
                        logger.warning(f"Redis cache write error: {e}")

                return city

            raise fastapi.HTTPException(status_code=404, detail="City not found")
        except fastapi.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise fastapi.HTTPException(status_code=500, detail="Database error")

    raise fastapi.HTTPException(status_code=503, detail="Database unavailable")


@app.get("/api/weatherforecast")
async def weather_forecast(redis_client=fastapi.Depends(get_redis_client)):
    """Weather forecast endpoint - returns latest weather for all cities."""
    cache_key = "weatherforecast"
    cache_ttl = 60  # 1 minute cache duration

    # Try to get data from cache.
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.info("Returning cached weather forecast data")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    # Try to get real weather data from database
    conn = await get_db_connection()
    if conn:
        try:
            async with conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT 
                            city_name as name,
                            temperature_c as "temperatureC",
                            temperature_f as "temperatureF",
                            description as summary,
                            recorded_at as date
                        FROM latest_weather
                        WHERE temperature_c IS NOT NULL
                        ORDER BY city_name
                        LIMIT 10
                    """)
                    rows = await cur.fetchall()

            if rows:
                forecast = []
                for row in rows:
                    item = dict(row)
                    for key, value in item.items():
                        if hasattr(value, 'quantize'):
                            item[key] = float(value) if key != "temperatureC" and key != "temperatureF" else int(float(value))
                        elif hasattr(value, 'isoformat'):
                            item[key] = value.isoformat()
                    forecast.append(item)

                # Cache the data
                if redis_client:
                    try:
                        redis_client.setex(cache_key, cache_ttl, json.dumps(forecast))
                    except Exception as e:
                        logger.warning(f"Redis cache write error: {e}")

                return forecast
        except Exception as e:
            logger.error(f"Database error fetching weather: {e}")

    # Fallback to generated data if database unavailable
    summaries = [
        "Freezing",
        "Bracing",
        "Chilly",
        "Cool",
        "Mild",
        "Warm",
        "Balmy",
        "Hot",
        "Sweltering",
        "Scorching",
    ]

    forecast = []
    for index in range(1, 6):  # Range 1 to 5 (inclusive)
        temp_c = random.randint(-20, 55)
        forecast_date = datetime.datetime.now() + datetime.timedelta(days=index)
        forecast_item = {
            "date": forecast_date.isoformat(),
            "temperatureC": temp_c,
            "temperatureF": int(temp_c * 9 / 5) + 32,
            "summary": random.choice(summaries),
        }
        forecast.append(forecast_item)

    # Cache the data
    if redis_client:
        try:
            redis_client.setex(cache_key, cache_ttl, json.dumps(forecast))
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    return forecast


@app.get("/health", response_class=fastapi.responses.PlainTextResponse)
async def health_check(redis_client=fastapi.Depends(get_redis_client)):
    """Health check endpoint."""
    if redis_client:
        redis_client.ping()
    return "Healthy"


# Serve static files directly from root, if the "static" directory exists
if os.path.exists("static"):
    app.mount(
        "/",
        fastapi.staticfiles.StaticFiles(directory="static", html=True),
        name="static"
    )
