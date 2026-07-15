from utils import safe_int


def local_site_score(site):
    """
    Score a campsite only from the factual fields supplied by Recreation.gov.

    Returns:
        tuple[float, list[str]]: numerical score and readable reasons.
    """
    score = 0.0
    reasons = []

    max_people = safe_int(site.get("max_num_people"))
    equipment_length = safe_int(site.get("equipment_length"))
    campsite_type = str(site.get("campsite_type", "")).lower()
    loop = str(site.get("loop", "")).strip()

    if max_people > 0:
        capacity_points = min(max_people * 2, 20)
        score += capacity_points
        reasons.append(f"Capacity for up to {max_people} people")

    if equipment_length > 0:
        equipment_points = min(equipment_length / 4, 20)
        score += equipment_points
        reasons.append(
            f"Equipment length listed as {equipment_length}"
        )

    if "standard" in campsite_type:
        score += 15
        reasons.append("Standard campsite")

    if "tent" in campsite_type:
        score += 10
        reasons.append("Tent-compatible")

    if "rv" in campsite_type:
        score += 10
        reasons.append("RV-compatible")

    if "electric" in campsite_type:
        score += 10
        reasons.append("Electric-site information listed")

    if "group" in campsite_type:
        score += 5
        reasons.append("Group campsite")

    if loop and loop.lower() != "unknown":
        score += 5
        reasons.append(f"Located in loop {loop}")

    if not reasons:
        reasons.append(
            "Recreation.gov provides limited comparison details for this site"
        )

    return min(100.0, round(score, 1)), reasons


def combine_site_and_review_score(site_score, review_score):
    """
    Combine factual campsite information with campground-level review data.

    Site information contributes 65%.
    Campground review information contributes 35%.
    """
    normalized_site_score = min(100.0, max(0.0, float(site_score)))
    normalized_review_score = min(100.0, max(0.0, float(review_score)))

    return round(
        normalized_site_score * 0.65
        + normalized_review_score * 0.35,
        1,
    )


def combined_site_score(site, review_summary):
    return combine_site_and_review_score(
        site.get("local_score", 0),
        review_summary.get("review_score", 70),
    )


def star_count_from_score(score):
    """
    Fixed star ranges prevent two equal star ratings from having
    different colors.
    """
    score = float(score)

    if score >= 85:
        return 5

    if score >= 70:
        return 4

    if score >= 50:
        return 3

    if score >= 30:
        return 2

    return 1


def stars_from_score(score):
    star_count = star_count_from_score(score)
    return "★" * star_count + "☆" * (5 - star_count)


def color_from_score(score):
    """
    Star colors are based only on star count:

    4–5 stars: green
    3 stars: yellow
    1–2 stars: red
    """
    star_count = star_count_from_score(score)

    if star_count >= 4:
        return "#2e7d32"

    if star_count == 3:
        return "#b7791f"

    return "#c62828"