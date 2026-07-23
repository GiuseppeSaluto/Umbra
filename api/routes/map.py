"""Map endpoint - serves a Folium HTML map for a geographic area."""

import asyncio

from flask import Blueprint, Response, request

from api.extensions import limiter
from api.routes._params import parse_float
from api.services.map_service import get_area_map_html

map_bp = Blueprint("map", __name__)


@map_bp.route("/map", methods=["GET"])
@limiter.limit("20 per minute")
async def map_view():
    try:
        lat = parse_float(request.args["lat"])
        lon = parse_float(request.args["lon"])
        radius_m = parse_float(request.args.get("radius_m", "500"))
    except (KeyError, ValueError):
        return Response(
            "lat and lon are required and must be numeric; radius_m must be numeric",
            status=400,
            mimetype="text/plain",
        )

    try:
        html = await asyncio.to_thread(get_area_map_html, lat, lon, radius_m)
    except ValueError as e:
        return Response(str(e), status=400, mimetype="text/plain")

    return Response(html, mimetype="text/html")
