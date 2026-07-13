import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from db.mongo import get_client
from api.routes.health import health_bp
from api.routes.area import area_bp
from api.routes.map import map_bp


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing

    if not testing:
        load_dotenv(Path.home() / ".secrets" / "umbra")
        load_dotenv(Path(".env"))
        app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "")

        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        mongo = get_client(mongo_uri)
        app.extensions = getattr(app, "extensions", {})
        app.extensions["mongo"] = mongo

    app.register_blueprint(health_bp)
    app.register_blueprint(area_bp)
    app.register_blueprint(map_bp)

    return app
