"""Folium map generation - HTML output served by Flask on /map.

Three independently toggleable layers (folium.LayerControl), matching the
green/heat/refuge separation discussed for Umbra: overlaying NDVI (10m) and LST
(1km) detail in a single blended view would imply a precision the data doesn't
have (see docs/SPEC.md section 8 and processing/sentinel.py). Green areas and
heat islands are rendered as their own real detected polygons, not just the
current search circle - giving a visible purpose to the green_areas/heat_islands
collections that api/services/area_service.py already populates.
"""

import folium
from folium import Element
from folium.plugins import Fullscreen, MiniMap

GREEN_AREA_COLOR = "#27ae60"
HEAT_ISLAND_COLOR = "#c0392b"

_NEW_SEARCH_LINK_HTML = """
<a href="/" style="position: fixed; top: 10px; left: 60px; z-index: 9999;
   background: white; padding: 6px 14px; border-radius: 4px;
   box-shadow: 0 1px 4px rgba(0,0,0,0.4); text-decoration: none;
   color: #333; font-family: sans-serif; font-size: 14px;">
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


def _build_search_area_layer(lat: float, lon: float, radius_m: float, analysis: dict) -> folium.FeatureGroup:
    layer = folium.FeatureGroup(name="Search area", show=True)

    heat_pct = analysis["heat_island_coverage_pct"]
    heat_line = (
        f"Heat island coverage: {heat_pct:.1f}%"
        if heat_pct is not None
        else "Heat island coverage: not available (no Sentinel-3 data for this area)"
    )
    popup_html = (
        f"NDVI mean: {analysis['ndvi_mean']:.2f}<br>"
        f"{heat_line}<br>"
        f"Acquisition date: {analysis['acquisition_date']}<br>"
        f"Source: {analysis['source']}"
    )

    folium.Marker(
        location=[lat, lon],
        tooltip="Your search location",
        popup=folium.Popup(popup_html, max_width=300, show=True),
        icon=folium.Icon(color="blue", icon="search", prefix="fa"),
    ).add_to(layer)

    folium.Circle(
        location=[lat, lon],
        radius=radius_m,
        color="#3388ff",
        fill=True,
        fill_opacity=0.1,
    ).add_to(layer)

    return layer


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
    """Render a full HTML document: a Folium/Leaflet map centered on (lat, lon),
    with independently toggleable layers for the current search, detected green
    areas, and detected heat islands.
    """
    fmap = folium.Map(location=[lat, lon], zoom_start=15)

    _build_search_area_layer(lat, lon, radius_m, analysis).add_to(fmap)
    _build_green_areas_layer(nearby_green_areas or []).add_to(fmap)
    _build_heat_islands_layer(nearby_heat_islands or []).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    Fullscreen().add_to(fmap)
    MiniMap(toggle_display=True).add_to(fmap)
    fmap.get_root().html.add_child(Element(_NEW_SEARCH_LINK_HTML))

    return fmap.get_root().render()
