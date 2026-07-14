from flask import Blueprint, Response, redirect, request
from api.services.geocoding_service import resolve_place

index_bp = Blueprint("index", __name__)

DEFAULT_RADIUS_M = 500

_LANDING_PAGE_HTML = rf"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Umbra</title>
  <style>
    body {{ font-family: sans-serif; text-align: center; margin-top: 15vh; }}
    form {{ margin-top: 1.5rem; }}
    input {{ margin: 0.25rem; padding: 0.4rem; }}
    hr {{ margin: 2rem auto; width: 200px; }}
  </style>
</head>
<body>
  <h1>Umbra</h1>
  <p id="status">Locating you...</p>

  <form id="manual-form" action="/map" method="get" style="display: none;">
    <p>Location unavailable - enter coordinates manually:</p>
    <input type="text" inputmode="decimal" pattern="-?[0-9]*\.?[0-9]+" name="lat" placeholder="Latitude (e.g. 44.6471)" required>
    <input type="text" inputmode="decimal" pattern="-?[0-9]*\.?[0-9]+" name="lon" placeholder="Longitude (e.g. 10.9252)" required>
    <input type="hidden" name="radius_m" value="{DEFAULT_RADIUS_M}">
    <button type="submit">View map</button>
  </form>

  <hr>

  <form action="/search" method="get">
    <p>Or search a place by name:</p>
    <input type="text" name="place" placeholder="e.g. Modena, Roma, Trapani" required>
    <button type="submit">Search</button>
  </form>

  <script>
    navigator.geolocation.getCurrentPosition(
      function (position) {{
        window.location = "/map?lat=" + position.coords.latitude +
                           "&lon=" + position.coords.longitude +
                           "&radius_m={DEFAULT_RADIUS_M}";
      }},
      function () {{
        document.getElementById("status").textContent = "Could not detect your location.";
        document.getElementById("manual-form").style.display = "block";
      }}
    );
  </script>
</body>
</html>"""


@index_bp.route("/", methods=["GET"])
def index():
    return Response(_LANDING_PAGE_HTML, mimetype="text/html")


@index_bp.route("/search", methods=["GET"])
def search():
    place = request.args.get("place", "")
    try:
        result = resolve_place(place)
    except ValueError as e:
        return Response(f"Could not find that place: {e}", status=400, mimetype="text/plain")

    return redirect(f"/map?lat={result['lat']}&lon={result['lon']}&radius_m={DEFAULT_RADIUS_M}")
