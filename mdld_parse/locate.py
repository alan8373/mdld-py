"""locate: find the source origin entry for a quad."""
from __future__ import annotations
from .utils import quad_to_key_for_origin


def locate(quad, origin=None):
    """Return the origin entry for *quad* in *origin*, or None if not found."""
    if quad is None or origin is None:
        return None
    quad_index = origin.get('quad_index') if isinstance(origin, dict) else getattr(origin, 'quad_index', None)
    if quad_index is None:
        return None
    key = quad_to_key_for_origin(quad)
    if key is None:
        return None
    return quad_index.get(key)
