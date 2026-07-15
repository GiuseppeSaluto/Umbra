"""Landing page (auto-geolocation + manual/place search) and /search (Nominatim)."""

import asyncio

from flask import Blueprint, Response, redirect, request

from api.services.geocoding_service import resolve_place

index_bp = Blueprint("index", __name__)

DEFAULT_RADIUS_M = 500

_PAGE_TEMPLATE = r"""<!DOCTYPE html>
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
  <p id="status">{status_text}</p>

  <form id="manual-form" action="/map" method="get" style="{manual_form_style}">
    <p>{manual_form_label}</p>
    <input type="text" inputmode="decimal" pattern="-?[0-9]*\.?[0-9]+" name="lat" placeholder="Latitude (e.g. 44.6471)" required>
    <input type="text" inputmode="decimal" pattern="-?[0-9]*\.?[0-9]+" name="lon" placeholder="Longitude (e.g. 10.9252)" required>
    <input type="hidden" name="radius_m" value="{default_radius_m}">
    <button type="submit">View map</button>
  </form>

  <hr>

  <form action="/search" method="get">
    <p>Or search a place by name:</p>
    <input type="text" name="place" placeholder="e.g. Modena, Roma, Trapani" required>
    <button type="submit">Search</button>
  </form>

  {geolocation_script}
</body>
</html>"""

_GEOLOCATION_SCRIPT = r"""<script>
    navigator.geolocation.getCurrentPosition(
      function (position) {{
        window.location = "/map?lat=" + position.coords.latitude +
                           "&lon=" + position.coords.longitude +
                           "&radius_m={default_radius_m}";
      }},
      function () {{
        document.getElementById("status").textContent = "Could not detect your location.";
        document.getElementById("manual-form").style.display = "block";
      }}
    );
  </script>""".format(default_radius_m=DEFAULT_RADIUS_M)


@index_bp.route("/", methods=["GET"])
def index():
    # ?search=1 (used by the map page's "New search" link) skips auto-geolocation,
    # otherwise a returning user just gets bounced straight back to /map.
    skip_geolocation = request.args.get("search") is not None

    if skip_geolocation:
        html = _PAGE_TEMPLATE.format(
            status_text="Where do you want to look?",
            manual_form_style="display: block;",
            manual_form_label="Enter coordinates manually:",
            geolocation_script="",
            default_radius_m=DEFAULT_RADIUS_M,
        )
    else:
        html = _PAGE_TEMPLATE.format(
            status_text="Locating you...",
            manual_form_style="display: none;",
            manual_form_label="Location unavailable - enter coordinates manually:",
            geolocation_script=_GEOLOCATION_SCRIPT,
            default_radius_m=DEFAULT_RADIUS_M,
        )

    return Response(html, mimetype="text/html")


@index_bp.route("/search", methods=["GET"])
async def search():
    place = request.args.get("place", "")
    try:
        result = await asyncio.to_thread(resolve_place, place)
    except ValueError as e:
        return Response(f"Could not find that place: {e}", status=400, mimetype="text/plain")

    return redirect(f"/map?lat={result['lat']}&lon={result['lon']}&radius_m={DEFAULT_RADIUS_M}")
