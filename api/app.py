import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from db.mongo import get_client as get_mongo_client
from db.valkey_cache import get_client as get_valkey_client
from api.routes.health import health_bp
from api.routes.area import area_bp
from api.routes.map import map_bp
from api.routes.index import index_bp

logger = logging.getLogger(__name__)


def create_app(testing: bool = False) -> Flask:
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

        # Valkey is an optional cache (docs/SPEC.md section 5) - the app must
        # still run without it, just without the fast-path cache.
        valkey_url = os.getenv("VALKEY_URL", "redis://localhost:6379/0")
        try:
            app.extensions["valkey"] = get_valkey_client(valkey_url)
        except Exception:
            logger.warning("Valkey unavailable at %s - caching disabled", valkey_url, exc_info=True)

    app.register_blueprint(health_bp)
    app.register_blueprint(area_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(index_bp)

    return app
