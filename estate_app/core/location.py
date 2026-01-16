import asyncio

from geopy.geocoders import Nominatim


async def geocode_location(address: str):
    geolocator = Nominatim(user_agent="venue_app")

    def _geocode():
        return geolocator.geocode(address, addressdetails=True)

    location = await asyncio.to_thread(_geocode)

    if not location:
        return None

    return {
        "point": f"POINT({location.longitude} {location.latitude})",
        "latitude": location.latitude,
        "longitude": location.longitude,
        "display_name": location.raw.get("display_name"),
        "address": location.raw.get("address", {})
    }