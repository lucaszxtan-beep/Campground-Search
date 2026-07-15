import re
import threading
import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
    )
}

REVIEW_TIME_LIMIT_SECONDS = 5

review_cache = {}
review_cache_lock = threading.Lock()


POSITIVE_WORDS = [
    "beautiful",
    "quiet",
    "clean",
    "spacious",
    "scenic",
    "great",
    "excellent",
    "friendly",
    "private",
    "peaceful",
    "nice",
    "amazing",
    "family",
    "shade",
    "lake",
    "river",
    "hiking",
    "views",
    "well maintained",
    "large",
    "good",
    "wonderful",
    "favorite",
    "recommend",
    "loved",
]

NEGATIVE_WORDS = [
    "noisy",
    "crowded",
    "dirty",
    "small",
    "tight",
    "bugs",
    "mosquito",
    "dusty",
    "rough",
    "poor",
    "bad",
    "limited",
    "traffic",
    "generator",
    "close together",
    "no privacy",
    "steep",
    "problem",
    "broken",
]


SOURCE_DOMAINS = [
    "recreation.gov",
    "campendium.com",
    "thedyrt.com",
    "tripadvisor.com",
    "yelp.com",
    "reddit.com",
    "rvlife.com",
    "campgroundreviews.com",
]


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def remaining_time(start_time):
    return REVIEW_TIME_LIMIT_SECONDS - (
        time.monotonic() - start_time
    )


def safe_get(url, start_time):
    remaining = remaining_time(start_time)

    if remaining <= 0:
        raise TimeoutError(
            "The review search reached its time limit."
        )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=max(0.5, min(remaining, 1.8)),
    )

    response.raise_for_status()
    return response


def extract_duckduckgo_url(href):
    if not href:
        return None

    if href.startswith("/l/?"):
        parsed = urlparse(href)
        query = parse_qs(parsed.query)

        if "uddg" in query:
            return unquote(query["uddg"][0])

    if href.startswith("http"):
        return href

    return None


def fetch_page_text(url, start_time):
    try:
        response = safe_get(url, start_time)
    except Exception:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(
        ["script", "style", "noscript", "svg"]
    ):
        tag.decompose()

    return clean_text(
        soup.get_text(" ")
    )[:7000]


def get_search_result_links(
    query,
    start_time,
    max_links=5,
):
    search_url = (
        "https://duckduckgo.com/html/?q="
        f"{quote_plus(query)}"
    )

    try:
        response = safe_get(search_url, start_time)
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    selectors = [
        ".result__a",
        "a[href]",
    ]

    for selector in selectors:
        for anchor in soup.select(selector):
            href = extract_duckduckgo_url(
                anchor.get("href")
            )

            if not href:
                continue

            lower_url = href.lower()

            if any(
                blocked in lower_url
                for blocked in [
                    "facebook.com",
                    "instagram.com",
                    "pinterest.com",
                    "login",
                    "signin",
                ]
            ):
                continue

            if not any(
                domain in lower_url
                for domain in SOURCE_DOMAINS
            ):
                continue

            if href not in links:
                links.append(href)

            if len(links) >= max_links:
                return links

    return links


def collect_review_text(campground):
    start_time = time.monotonic()
    campground_name = campground["name"]

    text_parts = []

    official_text = fetch_page_text(
        campground["url"],
        start_time,
    )

    if official_text:
        text_parts.append(official_text)

    queries = [
        f'"{campground_name}" campground reviews',
        f'"{campground_name}" camping reviews',
        f'"{campground_name}" Reddit campground',
        f'"{campground_name}" The Dyrt',
        f'"{campground_name}" Campendium',
    ]

    visited_urls = set()

    for query in queries:
        if remaining_time(start_time) <= 0:
            break

        result_links = get_search_result_links(
            query,
            start_time,
            max_links=4,
        )

        for link in result_links:
            if remaining_time(start_time) <= 0:
                break

            if link in visited_urls:
                continue

            visited_urls.add(link)
            page_text = fetch_page_text(
                link,
                start_time,
            )

            if not page_text:
                continue

            lower_text = page_text.lower()

            if any(
                term in lower_text
                for term in [
                    "campground",
                    "camping",
                    "campsite",
                ]
            ):
                text_parts.append(page_text[:4500])

    return "\n".join(text_parts)


def count_words(text, words):
    lower_text = text.lower()

    return sum(
        lower_text.count(word)
        for word in words
    )


def extract_comment_summary(text):
    lower_text = text.lower()

    positive_patterns = [
        (
            "Scenic surroundings",
            ["beautiful", "scenic", "views", "view"],
        ),
        (
            "Quiet atmosphere",
            ["quiet", "peaceful"],
        ),
        (
            "Family-friendly environment",
            ["family", "kids", "children"],
        ),
        (
            "Clean or well-maintained facilities",
            ["clean", "well maintained"],
        ),
        (
            "Shade or forested surroundings",
            ["shade", "forested", "trees"],
        ),
        (
            "Access to hiking or water",
            ["hiking", "trail", "lake", "river"],
        ),
    ]

    negative_patterns = [
        (
            "May become crowded",
            ["crowded", "busy"],
        ),
        (
            "Some sites may offer limited privacy",
            ["close together", "no privacy"],
        ),
        (
            "Noise may be present",
            ["noisy", "generator", "traffic"],
        ),
        (
            "Insects or mosquitoes may be present",
            ["bugs", "mosquito"],
        ),
        (
            "Some sites may be small or difficult to access",
            ["small", "tight"],
        ),
        (
            "Cell service or facilities may be limited",
            ["limited", "no cell", "cell signal"],
        ),
    ]

    strengths = []
    concerns = []

    for label, keywords in positive_patterns:
        if any(
            keyword in lower_text
            for keyword in keywords
        ):
            strengths.append(label)

    for label, keywords in negative_patterns:
        if any(
            keyword in lower_text
            for keyword in keywords
        ):
            concerns.append(label)

    return strengths[:4], concerns[:4]


def score_reviews_from_text(text):
    if not text or len(text) < 300:
        return {
            "review_score": 70,
            "confidence": "unavailable",
            "positives": [],
            "negatives": [],
            "important": [
                "Limited public review information was found."
            ],
        }

    positive_count = count_words(
        text,
        POSITIVE_WORDS,
    )

    negative_count = count_words(
        text,
        NEGATIVE_WORDS,
    )

    raw_score = (
        70
        + positive_count * 2.0
        - negative_count * 3.0
    )

    review_score = int(
        max(30, min(95, raw_score))
    )

    strengths, concerns = (
        extract_comment_summary(text)
    )

    if len(text) > 12000:
        confidence = "high"
    elif len(text) > 4500:
        confidence = "moderate"
    else:
        confidence = "limited"

    return {
        "review_score": review_score,
        "confidence": confidence,
        "positives": strengths,
        "negatives": concerns,
        "important": [
            f"Public review-data confidence: {confidence}."
        ],
    }


def get_campground_review_summary(campground):
    campground_id = str(campground["id"])

    with review_cache_lock:
        cached = review_cache.get(campground_id)

    if cached is not None:
        return cached

    review_text = collect_review_text(campground)
    summary = score_reviews_from_text(review_text)

    with review_cache_lock:
        review_cache[campground_id] = summary

    return summary