"""Folium map generation - HTML output served by Flask on /map.

Three independently toggleable layers (folium.LayerControl): blending NDVI (10m)
and LST (1km) into a single view would imply a precision the data doesn't have
(see docs/SPEC.md section 7). Green areas and heat islands render as their own
detected polygons, not just the current search circle.
"""

from datetime import datetime

import folium
from folium import Element
from folium.plugins import Fullscreen, MiniMap

HEAT_ISLAND_COLOR = "#cf5836"
GREEN_AREA_COLOR = "#059488"
SEARCH_ACCENT_COLOR = "#3560a8"

# Mirrors api.services.area_service.GREEN_AREA_NDVI_THRESHOLD - kept separate
# since this one only drives the popup's plain-language label.
_GREEN_AREA_NDVI_THRESHOLD = 0.3

_MAP_STYLE_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  body, .leaflet-container, .leaflet-popup-content, .leaflet-control {
    font-family: 'Quicksand', system-ui, sans-serif !important;
  }
  .leaflet-control-layers, .leaflet-bar, .leaflet-popup-content-wrapper {
    border-radius: 14px !important;
    box-shadow: 0 8px 24px rgba(33, 48, 43, 0.14) !important;
    border: 1px solid #dbeae4 !important;
  }
  .leaflet-popup-tip { box-shadow: none !important; }
  .leaflet-bar a { border-radius: 10px !important; color: #21302b !important; }
  .leaflet-control-layers-toggle { border-radius: 10px !important; }
</style>
"""

_NEW_SEARCH_LINK_HTML = """
<a href="/?search=1" style="position: fixed; top: 14px; left: 60px; z-index: 9999;
   background: #ffffff; padding: 8px 18px; border-radius: 999px;
   box-shadow: 0 8px 24px rgba(33, 48, 43, 0.14); border: 1px solid #dbeae4;
   text-decoration: none; color: #21302b; font-family: 'Quicksand', system-ui, sans-serif;
   font-weight: 600; font-size: 14px;">
  &larr; New search
</a>
"""


def _green_area_style(ndvi_mean: float) -> dict:
    """More opaque fill for higher NDVI - a visual cue, not a precise scale."""
    opacity = min(0.15 + ndvi_mean * 0.5, 0.7)
    return {"fillColor": GREEN_AREA_COLOR, "color": GREEN_AREA_COLOR, "fillOpacity": opacity, "weight": 1}


def _heat_island_style(coverage_pct: float) -> dict:
    opacity = min(0.15 + (coverage_pct / 100) * 0.6, 0.75)
    return {"fillColor": HEAT_ISLAND_COLOR, "color": HEAT_ISLAND_COLOR, "fillOpacity": opacity, "weight": 1}


def _describe_green_coverage(ndvi_mean: float) -> str:
    if ndvi_mean >= _GREEN_AREA_NDVI_THRESHOLD:
        return "🌳 Green area"
    if ndvi_mean >= 0:
        return "🌱 Some vegetation"
    return "🧱 Mostly paved or built-up"


def _describe_heat_risk(heat_pct: float | None) -> str:
    if heat_pct is None:
        return "🌡️ Heat data not available here"
    if heat_pct <= 0:
        return "✅ No heat island detected here"
    if heat_pct >= 100:
        return "🔥 This whole area is a heat island"
    return f"🔥 Heat island covers {heat_pct:.1f}% of this area"


def _build_search_area_layer(
    lat: float, lon: float, radius_m: float, analysis: dict
) -> tuple[folium.FeatureGroup, folium.CircleMarker, folium.Circle]:
    layer = folium.FeatureGroup(name="Search area", show=True)

    acquisition_date = datetime.fromisoformat(analysis["acquisition_date"]).strftime("%d %b %Y")
    popup_html = (
        '<div style="font-size: 14px; font-weight: 700; color: #21302b; line-height: 1.6;">'
        f"{_describe_green_coverage(analysis['ndvi_mean'])}<br>"
        f"{_describe_heat_risk(analysis['heat_island_coverage_pct'])}"
        "</div>"
        '<div style="font-size: 11px; color: #5c6b64; border-top: 1px solid #dbeae4; '
        'margin-top: 6px; padding-top: 6px;">'
        f"NDVI {analysis['ndvi_mean']:.2f} &middot; satellite pass on {acquisition_date}<br>"
        "Data: Sentinel-2 &amp; Sentinel-3 satellites"
        "</div>"
    )

    marker = folium.CircleMarker(
        location=[lat, lon],
        radius=9,
        tooltip="Your search location",
        popup=folium.Popup(popup_html, max_width=300),
        color="#ffffff",
        weight=3,
        fill=True,
        fill_color=SEARCH_ACCENT_COLOR,
        fill_opacity=1,
    )
    marker.add_to(layer)

    circle = folium.Circle(
        location=[lat, lon],
        radius=radius_m,
        color=SEARCH_ACCENT_COLOR,
        weight=2,
        fill=True,
        fill_opacity=0.08,
    )
    circle.add_to(layer)

    return layer, marker, circle


def _build_green_areas_layer(green_areas: list[dict]) -> folium.FeatureGroup:
    layer = folium.FeatureGroup(name="Detected green areas", show=True)
    for doc in green_areas:
        ndvi_mean = doc.get("ndvi_mean")
        location = doc.get("location")
        if ndvi_mean is None or location is None:
            continue
        folium.GeoJson(
            location,
            style_function=lambda _feature, style=_green_area_style(ndvi_mean): style,
            tooltip=f"NDVI mean: {ndvi_mean:.2f}",
        ).add_to(layer)
    return layer


def _build_heat_islands_layer(heat_islands: list[dict]) -> folium.FeatureGroup:
    layer = folium.FeatureGroup(name="Detected heat islands", show=True)
    for doc in heat_islands:
        coverage_pct = doc.get("heat_island_coverage_pct")
        location = doc.get("location")
        if coverage_pct is None or location is None:
            continue
        folium.GeoJson(
            location,
            style_function=lambda _feature, style=_heat_island_style(coverage_pct): style,
            tooltip=f"Heat island coverage: {coverage_pct:.1f}%",
        ).add_to(layer)
    return layer


def render_map(
    lat: float,
    lon: float,
    radius_m: float,
    analysis: dict,
    nearby_green_areas: list[dict] | None = None,
    nearby_heat_islands: list[dict] | None = None,
) -> str:
    """Render a full HTML document: a Folium/Leaflet map centered on (lat, lon)"""
    fmap = folium.Map(location=[lat, lon], zoom_start=15, tiles="CartoDB Voyager")

    search_layer, search_marker, search_circle = _build_search_area_layer(lat, lon, radius_m, analysis)
    search_layer.add_to(fmap)
    _build_green_areas_layer(nearby_green_areas or []).add_to(fmap)
    _build_heat_islands_layer(nearby_heat_islands or []).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    Fullscreen().add_to(fmap)
    MiniMap(toggle_display=True).add_to(fmap)

    fmap.get_root().header.add_child(Element(_MAP_STYLE_HTML))  # type: ignore[attr-defined]
    fmap.get_root().html.add_child(Element(_NEW_SEARCH_LINK_HTML))  # type: ignore[attr-defined]
    popup_toggle_js = f"""setTimeout(function() {{
        var marker = {search_marker.get_name()};
        var circle = {search_circle.get_name()};
        function toggle() {{
            if (marker.isPopupOpen()) {{ marker.closePopup(); }} else {{ marker.openPopup(); }}
        }}
        marker.off('click');
        marker.on('click', toggle);
        circle.on('click', toggle);
        marker.openPopup();
    }}, 0);"""
    fmap.get_root().script.add_child(Element(popup_toggle_js))  # type: ignore[attr-defined]

    return fmap.get_root().render()
