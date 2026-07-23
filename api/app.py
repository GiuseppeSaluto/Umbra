import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from api.extensions import limiter
from api.routes.area import area_bp
from api.routes.health import health_bp
from api.routes.index import index_bp
from api.routes.map import map_bp
from db.mongo import get_client as get_mongo_client
from theme import COLORS

logger = logging.getLogger(__name__)


def create_app(testing: bool = False, rate_limiting: bool | None = None) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing

    if not testing:
        load_dotenv(Path.home() / ".secrets" / "umbra")
        load_dotenv(Path(".env"))
        app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "")

        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        mongo = get_mongo_client(mongo_uri)
        app.extensions = getattr(app, "extensions", {})
        app.extensions["mongo"] = mongo

    # Swappable later via RATELIMIT_STORAGE_URI.
    app.config["RATELIMIT_STORAGE_URI"] = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    app.config["RATELIMIT_ENABLED"] = (not testing) if rate_limiting is None else rate_limiting
    limiter.init_app(app)

    cors_origins = os.getenv("CORS_ORIGINS", "*")
    CORS(app, resources={r"/api/*": {"origins": cors_origins if cors_origins == "*" else cors_origins.split(",")}})

    app.register_blueprint(health_bp)
    app.register_blueprint(area_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(index_bp)

    @app.context_processor
    def inject_theme() -> dict:
        return {"colors": COLORS}

    return app
