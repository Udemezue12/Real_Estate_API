from geoalchemy2.shape import to_shape

def convert_location(geom):
    if not geom:
        return None
    point = to_shape(geom)
    return {
        "latitude": point.y,
        "longitude": point.x
    }