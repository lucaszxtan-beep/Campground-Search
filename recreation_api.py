import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
    )
}


def extract_coordinates(item):
    if not isinstance(item, dict):
        return None, None

    latitude_keys = [
        "latitude",
        "Latitude",
        "lat",
        "FacilityLatitude",
        "RecAreaLatitude",
        "facility_latitude",
    ]

    longitude_keys = [
        "longitude",
        "Longitude",
        "lon",
        "lng",
        "FacilityLongitude",
        "RecAreaLongitude",
        "facility_longitude",
    ]

    latitude = next(
        (
            item.get(key)
            for key in latitude_keys
            if item.get(key) not in (None, "")
        ),
        None,
    )

    longitude = next(
        (
            item.get(key)
            for key in longitude_keys
            if item.get(key) not in (None, "")
        ),
        None,
    )

    try:
        return float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None, None


def search_campgrounds(query):
    query = query.strip()

    if not query:
        return []

    response = requests.get(
        "https://www.recreation.gov/api/search",
        params={
            "q": query,
            "inventory_type": "camping",
            "size": 50,
        },
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()
    results = response.json().get("results", [])

    campgrounds = []
    seen_ids = set()

    for item in results:
        name = item.get("name") or item.get("title")
        entity_id = item.get("entity_id") or item.get("id")
        entity_type = str(item.get("entity_type", "")).lower()

        if not name or not entity_id:
            continue

        entity_id = str(entity_id)

        if entity_id in seen_ids:
            continue

        name_lower = name.lower()

        is_campground = (
            entity_type == "campground"
            or "campground" in name_lower
            or item.get("inventory_type") == "camping"
        )

        if not is_campground:
            continue

        latitude, longitude = extract_coordinates(item)

        campgrounds.append(
            {
                "name": name,
                "id": entity_id,
                "latitude": latitude,
                "longitude": longitude,
                "url": (
                    "https://www.recreation.gov/camping/campgrounds/"
                    f"{entity_id}"
                ),
            }
        )

        seen_ids.add(entity_id)

    return campgrounds


def get_month_availability(campground_id, month_date):
    url = (
        "https://www.recreation.gov/api/camps/availability/"
        f"campground/{campground_id}/month"
    )

    response = requests.get(
        url,
        params={
            "start_date": month_date.strftime(
                "%Y-%m-%dT00:00:00.000Z"
            )
        },
        headers=HEADERS,
        timeout=20,
    )

    if response.status_code == 404:
        raise ValueError(
            "Availability information was not found for this campground."
        )

    response.raise_for_status()
    return response.json()