"""Landing page (auto-geolocation + manual/place search) and /search (Nominatim)."""

import asyncio

from flask import Blueprint, Response, redirect, render_template, request

from api.services.geocoding_service import resolve_place

index_bp = Blueprint("index", __name__)

DEFAULT_RADIUS_M = 500


@index_bp.route("/", methods=["GET"])
def index():
    # ?search=1 (used by the map page's "New search" link) skips auto-geolocation,
    # otherwise a returning user just gets bounced straight back to /map.
    skip_geolocation = request.args.get("search") is not None
    return render_template(
        "index.html",
        skip_geolocation=skip_geolocation,
        default_radius_m=DEFAULT_RADIUS_M,
    )


@index_bp.route("/search", methods=["GET"])
async def search():
    place = request.args.get("place", "")
    try:
        result = await asyncio.to_thread(resolve_place, place)
    except ValueError as e:
        return Response(f"Could not find that place: {e}", status=400, mimetype="text/plain")

    return redirect(f"/map?lat={result['lat']}&lon={result['lon']}&radius_m={DEFAULT_RADIUS_M}")
