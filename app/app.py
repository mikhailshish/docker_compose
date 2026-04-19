import os
import time

from flask import Flask, jsonify, render_template_string
import psycopg
import redis


APP_NAME = os.getenv("APP_NAME", "MyApp")

POSTGRES_DB = os.getenv("POSTGRES_DB", "appdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "app_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_me_123")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

VISITS_CACHE_KEY = "visits_total"
VISITS_CACHE_TTL = 10

app = Flask(__name__)
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def get_db_connection():
    return psycopg.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        autocommit=True,
    )


def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visits_counter (
                    id INTEGER PRIMARY KEY,
                    total BIGINT NOT NULL
                );
            """)
            cur.execute("""
                INSERT INTO visits_counter (id, total)
                VALUES (1, 0)
                ON CONFLICT (id) DO NOTHING;
            """)


def init_db_with_retry(retries=30, delay=2):
    for attempt in range(1, retries + 1):
        try:
            init_db()
            print("Database initialized successfully.", flush=True)
            return
        except Exception as exc:
            print(
                f"Database is not ready yet "
                f"(attempt {attempt}/{retries}): {exc}",
                flush=True
            )
            time.sleep(delay)

    raise RuntimeError("Could not initialize database after multiple retries.")


def check_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception:
        return False


def check_redis():
    try:
        return bool(redis_client.ping())
    except Exception:
        return False


@app.get("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{{ app_name }}</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background: #f5f7fb;
                color: #1f2937;
            }
            .card {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                padding: 32px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            }
            h1 {
                margin-top: 0;
            }
            code {
                background: #eef2ff;
                padding: 2px 6px;
                border-radius: 6px;
            }
            ul {
                line-height: 1.8;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>{{ app_name }}</h1>
            <p>
                Flask application is running behind Nginx with PostgreSQL and Redis.
            </p>
            <p>Available endpoints:</p>
            <ul>
                <li><code>GET /</code> — this HTML page</li>
                <li><code>GET /visits</code> — visit counter with Redis cache for 10 seconds</li>
                <li><code>GET /health</code> — health status of app dependencies</li>
            </ul>
        </div>
    </body>
    </html>
    """, app_name=APP_NAME)


@app.get("/visits")
def visits():
    try:
        cached_total = redis_client.get(VISITS_CACHE_KEY)
    except Exception:
        cached_total = None

    if cached_total is not None:
        return jsonify({
            "total": int(cached_total),
            "cached": True
        })

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE visits_counter
                SET total = total + 1
                WHERE id = 1
                RETURNING total;
            """)
            total = cur.fetchone()[0]

    try:
        redis_client.setex(VISITS_CACHE_KEY, VISITS_CACHE_TTL, total)
    except Exception:
        pass

    return jsonify({
        "total": total,
        "cached": False
    })


@app.get("/health")
def health():
    db_ok = check_db()
    redis_ok = check_redis()

    payload = {
        "status": "ok" if db_ok and redis_ok else "error",
        "db": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
    }

    return jsonify(payload), (200 if db_ok and redis_ok else 503)


init_db_with_retry()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
