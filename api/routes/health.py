"""Health check endpoint."""

from flask import Blueprint, jsonify

from api.services.health_service import check_mongo_connectivity

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    mongo_ok = check_mongo_connectivity()
    payload = {
        "status": "ok" if mongo_ok else "error",
        "mongo": "connected" if mongo_ok else "unreachable",
    }
    return jsonify(payload), 200 if mongo_ok else 503
