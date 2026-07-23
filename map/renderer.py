"""Folium map generation - HTML output served by Flask on /map.

Three independently toggleable layers (folium.LayerControl): blending NDVI (10m)
and LST (1km) into a single view would imply a precision the data doesn't have
(see docs/SPEC.md section 7). Green areas and heat islands render as their own
detected polygons, not just the current search area.
"""

from datetime import datetime

import folium
from folium import Element
from folium.plugins import Fullscreen, MiniMap

from processing.geo import bbox_from_point
from theme import COLORS

# Mirrors api.services.area_service.GREEN_AREA_NDVI_THRESHOLD - kept separate
# since this one only drives the popup's plain-language label.
_GREEN_AREA_NDVI_THRESHOLD = 0.3

_MAP_STYLE_HTML = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  body, .leaflet-container, .leaflet-popup-content, .leaflet-control {{
    font-family: 'Quicksand', system-ui, sans-serif !important;
  }}
  .leaflet-control-layers, .leaflet-bar, .leaflet-popup-content-wrapper {{
    border-radius: 14px !important;
    box-shadow: 0 8px 24px rgba(33, 48, 43, 0.14) !important;
    border: 1px solid {COLORS["border"]} !important;
  }}
  .leaflet-popup-tip {{ box-shadow: none !important; }}
  .leaflet-bar a {{ border-radius: 10px !important; color: {COLORS["ink"]} !important; }}
  .leaflet-control-layers-toggle {{ border-radius: 10px !important; }}
</style>
"""

_NEW_SEARCH_LINK_HTML = f"""
<a href="/?search=1" style="position: fixed; top: 14px; left: 60px; z-index: 9999;
   background: {COLORS["card"]}; padding: 8px 18px; border-radius: 999px;
   box-shadow: 0 8px 24px rgba(33, 48, 43, 0.14); border: 1px solid {COLORS["border"]};
   text-decoration: none; color: {COLORS["ink"]}; font-family: 'Quicksand', system-ui, sans-serif;
   font-weight: 600; font-size: 14px;">
  &larr; New search
</a>
"""

_LEGEND_HTML = f"""
<div style="position: fixed; bottom: 24px; left: 14px; z-index: 9999;
   background: {COLORS["card"]}; padding: 10px 14px; border-radius: 14px;
   box-shadow: 0 8px 24px rgba(33, 48, 43, 0.14); border: 1px solid {COLORS["border"]};
   font-family: 'Quicksand', system-ui, sans-serif; font-size: 12px; color: {COLORS["ink"]};">
  <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
    <span style="width: 10px; height: 10px; border-radius: 50%; display: inline-block;
       background: {COLORS["green"]};"></span>
    Vegetation / green area
  </div>
  <div style="display: flex; align-items: center; gap: 6px;">
    <span style="width: 10px; height: 10px; border-radius: 50%; display: inline-block;
       background: {COLORS["heat"]};"></span>
    Heat island
  </div>
</div>
"""

_HEAT_HATCH_SVG = f"""
<svg width="0" height="0" style="position: absolute;">
  <defs>
    <pattern id="heat-hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
      <rect width="8" height="8" fill="transparent"></rect>
      <line x1="0" y1="0" x2="0" y2="8" stroke="{COLORS["heat"]}" stroke-width="4"></line>
    </pattern>
  </defs>
</svg>
"""


def _green_area_style(ndvi_mean: float) -> dict:
    opacity = min(0.15 + ndvi_mean * 0.5, 0.7)
    return {"fillColor": COLORS["green"], "color": COLORS["green"], "fillOpacity": opacity, "weight": 1}


def _heat_island_style(coverage_pct: float) -> dict:
    opacity = min(0.35 + (coverage_pct / 100) * 0.5, 0.85)
    return {"fillColor": "url(#heat-hatch)", "color": COLORS["heat"], "fillOpacity": opacity, "weight": 1.5}


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
) -> tuple[folium.FeatureGroup, folium.CircleMarker, folium.Rectangle]:
    layer = folium.FeatureGroup(name="Search area", show=True)

    acquisition_date = datetime.fromisoformat(analysis["acquisition_date"]).strftime("%d %b %Y")
    green_word = f'<span style="color: {COLORS["green"]}; font-weight: 600;">Vegetation</span>'
    heat_word = f'<span style="color: {COLORS["heat"]}; font-weight: 600;">heat</span>'
    popup_html = (
        f'<div style="font-size: 14px; font-weight: 700; color: {COLORS["ink"]}; line-height: 1.6;">'
        f"{_describe_green_coverage(analysis['ndvi_mean'])}<br>"
        f"{_describe_heat_risk(analysis['heat_island_coverage_pct'])}"
        "</div>"
        '<details style="margin-top: 6px;">'
        f'<summary style="font-size: 12px; color: {COLORS["green"]}; font-weight: 600; cursor: pointer;">'
        "Show details</summary>"
        f'<div style="font-size: 12px; color: {COLORS["ink"]}; line-height: 1.6; margin-top: 6px;">'
        f"{green_word} index range: {analysis['ndvi_min']:.2f} to {analysis['ndvi_max']:.2f} "
        "(higher = greener)<br>"
        f"Cloud cover during satellite pass: {analysis['cloud_coverage_pct']:.0f}%<br>"
        f"{green_word} is measured at {analysis['resolution_m_ndvi']}m resolution; "
        f"{heat_word} is measured at {analysis['resolution_m_lst']}m resolution, so "
        f"{heat_word} readings cover a much wider, blurrier area."
        "</div>"
        "</details>"
        f'<div style="font-size: 11px; color: {COLORS["ink_secondary"]}; '
        f'border-top: 1px solid {COLORS["border"]}; margin-top: 6px; padding-top: 6px;">'
        f"NDVI {analysis['ndvi_mean']:.2f} &middot; satellite pass on {acquisition_date}<br>"
        "Data: Sentinel-2 &amp; Sentinel-3 satellites"
        "</div>"
    )

    marker = folium.CircleMarker(
        location=[lat, lon],
        radius=9,
        tooltip="Your search location",
        popup=folium.Popup(popup_html, max_width=320),
        color=COLORS["card"],
        weight=3,
        fill=True,
        fill_color=COLORS["blue"],
        fill_opacity=1,
    )
    marker.add_to(layer)

    bbox = bbox_from_point(lat, lon, radius_m)
    square = folium.Rectangle(
        bounds=[[bbox["min_lat"], bbox["min_lon"]], [bbox["max_lat"], bbox["max_lon"]]],
        color=COLORS["blue"],
        weight=2,
        fill=True,
        fill_opacity=0.08,
    )
    square.add_to(layer)

    return layer, marker, square


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

    search_layer, search_marker, search_square = _build_search_area_layer(lat, lon, radius_m, analysis)
    search_layer.add_to(fmap)
    _build_green_areas_layer(nearby_green_areas or []).add_to(fmap)
    _build_heat_islands_layer(nearby_heat_islands or []).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    Fullscreen().add_to(fmap)
    MiniMap(toggle_display=True).add_to(fmap)

    fmap.get_root().header.add_child(Element(_MAP_STYLE_HTML))  # type: ignore[attr-defined]
    fmap.get_root().html.add_child(Element(_NEW_SEARCH_LINK_HTML))  # type: ignore[attr-defined]
    fmap.get_root().html.add_child(Element(_LEGEND_HTML))  # type: ignore[attr-defined]
    fmap.get_root().html.add_child(Element(_HEAT_HATCH_SVG))  # type: ignore[attr-defined]
    popup_toggle_js = f"""setTimeout(function() {{
        var marker = {search_marker.get_name()};
        var square = {search_square.get_name()};
        function toggle() {{
            if (marker.isPopupOpen()) {{ marker.closePopup(); }} else {{ marker.openPopup(); }}
        }}
        marker.off('click');
        marker.on('click', toggle);
        square.on('click', toggle);
        marker.openPopup();
    }}, 0);"""
    fmap.get_root().script.add_child(Element(popup_toggle_js))  # type: ignore[attr-defined]

    return fmap.get_root().render()
