import httpx
from .settings import settings
from shapely.geometry import Point


async def geocode_address(address: str) -> Point:
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": address,
        "apiKey": settings.GEOAPIFY_API_KEY,
        "limit": 1,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    features = data.get("features")
    if not features:
        raise ValueError(f"Could not geocode address: {address}")

    geometry = features[0].get("geometry")
    if not geometry:
        raise ValueError(f"No geometry returned for address: {address}")

    lon = geometry["coordinates"][0]
    lat = geometry["coordinates"][1]
    return Point(lon, lat)