"""Area analysis endpoint - NDVI/LST summary for a geographic area."""

from flask import Blueprint, jsonify, request

from api.services.area_service import get_area_analysis_cached

area_bp = Blueprint("area", __name__)


@area_bp.route("/api/area", methods=["GET"])
def area():
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
        radius_m = float(request.args.get("radius_m", 500))
    except (KeyError, ValueError):
        return jsonify({
            "error": "lat and lon are required and must be numeric; radius_m must be numeric"
        }), 400

    try:
        result = get_area_analysis_cached(lat, lon, radius_m)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(result), 200
