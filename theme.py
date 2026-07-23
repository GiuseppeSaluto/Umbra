"""Shared brand color palette - single source of truth for the landing page
(Jinja2, injected via api.app's context processor) and the Folium map
(map/renderer.py, plain Python string formatting).

green/heat validated as a colorblind-safe pair against the bg surface
(CVD separation 12.4, normal-vision floor 17.6, both >=3:1 contrast).
"""

COLORS = {
    "bg": "#f4f9f7",
    "card": "#ffffff",
    "ink": "#21302b",
    "ink_secondary": "#5c6b64",
    "border": "#dbeae4",
    "green": "#059488",
    "blue": "#3560a8",
    "heat": "#cf5836",
}
