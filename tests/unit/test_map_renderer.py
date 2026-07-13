from map.renderer import render_map


def _sample_analysis():
    return {
        "bbox": {"min_lon": 10.91, "min_lat": 44.62, "max_lon": 10.93, "max_lat": 44.64},
        "ndvi_mean": 0.42,
        "ndvi_min": -0.1,
        "ndvi_max": 0.85,
        "heat_island_coverage_pct": 35.5,
        "acquisition_date": "2026-07-01T10:30:00+00:00",
        "cloud_coverage_pct": 3.2,
        "resolution_m": 10,
        "source": "Sentinel-2 L2A",
    }


def test_render_map_returns_full_html_document():
    html = render_map(44.6471, 10.9252, radius_m=500, analysis=_sample_analysis())
    assert "<html" in html.lower()
    assert "</html>" in html.lower()


def test_render_map_contains_leaflet_reference():
    html = render_map(44.6471, 10.9252, radius_m=500, analysis=_sample_analysis())
    assert "leaflet" in html.lower()


def test_render_map_embeds_center_coordinates():
    html = render_map(44.6471, 10.9252, radius_m=500, analysis=_sample_analysis())
    assert "44.6471" in html
    assert "10.9252" in html


def test_render_map_embeds_ndvi_summary_in_popup():
    html = render_map(44.6471, 10.9252, radius_m=500, analysis=_sample_analysis())
    assert "0.42" in html


def test_render_map_embeds_heat_island_summary_in_popup():
    html = render_map(44.6471, 10.9252, radius_m=500, analysis=_sample_analysis())
    assert "35.5" in html
