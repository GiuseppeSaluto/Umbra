"""Climate shelter lookup endpoint - GET /api/shelters?comune=<name>"""

import asyncio

from flask import Blueprint, jsonify, request

from api.extensions import limiter
from api.services.shelter_service import get_shelters_for_comune

shelters_bp = Blueprint("shelters", __name__)


def _serialize_shelter(shelter: dict) -> dict:
    return {k: v for k, v in shelter.items() if k not in ("_id", "istat_code")}


@shelters_bp.route("/api/shelters", methods=["GET"])
@limiter.limit("20 per minute")
async def shelters():
    comune = request.args.get("comune", "").strip()
    if not comune:
        return jsonify({"error": "comune is required"}), 400

    try:
        result = await asyncio.to_thread(get_shelters_for_comune, comune)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify(
        {
            "comune": result["comune"]["name"],
            "province": result["comune"]["province"],
            "region": result["comune"]["region"],
            "shelter_count": len(result["shelters"]),
            "shelters": [_serialize_shelter(s) for s in result["shelters"]],
        }
    ), 200
