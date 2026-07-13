"""Folium map generation - HTML output served by Flask on /map."""

import folium


def render_map(lat: float, lon: float, radius_m: float, analysis: dict) -> str:
    """Render a full HTML document: a Folium/Leaflet map centered on (lat, lon),
    with a marker summarizing the NDVI/heat island analysis and a circle showing
    the requested search radius.
    """
    fmap = folium.Map(location=[lat, lon], zoom_start=15)

    popup_html = (
        f"NDVI mean: {analysis['ndvi_mean']:.2f}<br>"
        f"Heat island coverage: {analysis['heat_island_coverage_pct']:.1f}%<br>"
        f"Acquisition date: {analysis['acquisition_date']}<br>"
        f"Source: {analysis['source']}"
    )

    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=300),
    ).add_to(fmap)

    folium.Circle(
        location=[lat, lon],
        radius=radius_m,
        color="#d9534f",
        fill=True,
        fill_opacity=0.1,
    ).add_to(fmap)

    return fmap.get_root().render()
