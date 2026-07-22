"""Turn place names into coordinates via Nominatim (OpenStreetMap).

Keyless, but its usage policy asks for an identifying User-Agent and no more than
one request per second, so callers that hit it in bulk should throttle.
"""

from django.conf import settings
from django.core.cache import cache

from .http import session


class GeocodingError(Exception):
    pass


def _cache_key(country, query):
    raw = f"geocode_{country}_{query.strip().lower()}"
    return raw.replace(" ", "_").replace(",", "").replace("'", "")


def geocode(query, *, country="us"):
    """Return (lat, lon) for a free-form place name, or raise GeocodingError."""
    key = _cache_key(country, query)
    hit = cache.get(key)
    if hit is not None:
        return hit

    params = {"q": query, "format": "jsonv2", "limit": 1}
    if country:
        params["countrycodes"] = country

    resp = session().get(
        f"{settings.NOMINATIM_BASE_URL}/search",
        params=params,
        headers={"User-Agent": settings.GEOCODER_USER_AGENT},
        timeout=settings.HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise GeocodingError(f"could not locate '{query}'")

    coords = (float(results[0]["lat"]), float(results[0]["lon"]))
    cache.set(key, coords, timeout=None)
    return coords
