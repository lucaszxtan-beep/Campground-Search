from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
import threading

from recreation_api import extract_coordinates, get_month_availability
from scoring import local_site_score


availability_cache = {}
availability_cache_lock = threading.Lock()


def month_start(date_obj):
    return date_obj.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def cached_month_availability(campground_id, month_date):
    cache_key = (
        str(campground_id),
        month_date.strftime("%Y-%m"),
    )

    with availability_cache_lock:
        cached = availability_cache.get(cache_key)

    if cached is not None:
        return cached

    data = get_month_availability(campground_id, month_date)

    with availability_cache_lock:
        availability_cache[cache_key] = data

    return data


def status_is_available(status):
    return str(status).strip().lower() == "available"


def site_available_for_stay(
    campground_id,
    campsite_id,
    check_in,
    nights,
):
    for offset in range(nights):
        day = check_in + timedelta(days=offset)

        month_data = cached_month_availability(
            campground_id,
            month_start(day),
        )

        campsite = (
            month_data
            .get("campsites", {})
            .get(str(campsite_id))
        )

        if not campsite:
            return False

        availability_map = campsite.get("availabilities", {})

        possible_date_keys = [
            day.strftime("%Y-%m-%dT00:00:00Z"),
            day.strftime("%Y-%m-%dT00:00:00.000Z"),
        ]

        status = None

        for date_key in possible_date_keys:
            if date_key in availability_map:
                status = availability_map[date_key]
                break

        if not status_is_available(status):
            return False

    return True


def build_site_record(campsite_id, campsite):
    latitude, longitude = extract_coordinates(campsite)

    site = {
        "campsite_id": str(campsite_id),
        "site": campsite.get("site", campsite_id),
        "loop": campsite.get("loop", "Unknown"),
        "campsite_type": campsite.get(
            "campsite_type",
            "Unknown",
        ),
        "type_of_use": campsite.get(
            "type_of_use",
            "Unknown",
        ),
        "max_num_people": campsite.get(
            "max_num_people",
            "Unknown",
        ),
        "equipment_length": campsite.get(
            "equipment_length",
            "Unknown",
        ),
        "latitude": latitude,
        "longitude": longitude,
    }

    score, reasons = local_site_score(site)

    site["local_score"] = score
    site["score_reasons"] = reasons

    return site


def get_available_site_details(
    campground_id,
    check_in,
    nights,
):
    first_month_data = cached_month_availability(
        campground_id,
        month_start(check_in),
    )

    campsites = first_month_data.get("campsites", {})
    available_sites = []

    for campsite_id, campsite in campsites.items():
        if not site_available_for_stay(
            campground_id,
            campsite_id,
            check_in,
            nights,
        ):
            continue

        available_sites.append(
            build_site_record(campsite_id, campsite)
        )

    return sorted(
        available_sites,
        key=lambda site: (
            site.get("local_score", 0),
            str(site.get("site", "")),
        ),
        reverse=True,
    )


def check_one_date(
    campground_id,
    date_obj,
    nights,
    friday_saturday_only,
):
    # Python: Monday=0, Friday=4, Saturday=5.
    if (
        friday_saturday_only
        and date_obj.weekday() not in (4, 5)
    ):
        return None

    available_sites = get_available_site_details(
        campground_id,
        date_obj,
        nights,
    )

    if not available_sites:
        return None

    return {
        "date": date_obj.strftime("%Y-%m-%d"),
        "count": len(available_sites),
        "best_site": available_sites[0],
    }


def search_possible_dates_parallel(
    campground_id,
    start_date,
    end_date,
    nights,
    friday_saturday_only,
    max_workers=4,
):
    dates = []
    current = start_date

    while current <= end_date:
        if (
            not friday_saturday_only
            or current.weekday() in (4, 5)
        ):
            dates.append(current)

        current += timedelta(days=1)

    if not dates:
        return []

    results = []
    worker_count = max(1, min(max_workers, len(dates)))

    with ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:
        futures = [
            executor.submit(
                check_one_date,
                campground_id,
                date_obj,
                nights,
                friday_saturday_only,
            )
            for date_obj in dates
        ]

        for future in as_completed(futures):
            try:
                result = future.result()

                if result:
                    results.append(result)
            except Exception:
                # One unsuccessful date should not stop all other dates.
                continue

    return sorted(
        results,
        key=lambda result: result["date"],
    )