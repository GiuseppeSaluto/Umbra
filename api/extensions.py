"""Shared Flask extension instances.

Kept separate from api/app.py: create_app() imports the route blueprints,
which in turn need `limiter` already constructed to use as a decorator -
putting it here avoids a circular import between api.app and api.routes.*.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"])
