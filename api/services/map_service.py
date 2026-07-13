"""Map service - combines area analysis with Folium rendering."""

from api.services.area_service import get_area_analysis
from map.renderer import render_map


def get_area_map_html(lat: float, lon: float, radius_m: float) -> str:
    analysis = get_area_analysis(lat, lon, radius_m)
    return render_map(lat, lon, radius_m, analysis)
