from datetime import datetime

import streamlit as st

from campsite_core import (
    get_available_site_details,
    search_possible_dates_parallel,
)

from recreation_api import search_campgrounds

from reviews_core import (
    get_campground_review_summary,
)

from scoring import combined_site_score

from ui_components import (
    campground_feedback_widget,
    campground_summary,
    date_card,
    inject_css,
    official_map_button,
    page_nav,
    reservation_card,
    section_title,
    title,
)

from utils import APP_VERSION, to_datetime


st.set_page_config(
    page_title="Campsite Finder",
    page_icon="🏕️",
    layout="wide",
)

inject_css()


@st.cache_data(
    show_spinner=False,
    ttl=3600,
)
def cached_search_campgrounds(query):
    return search_campgrounds(query)


@st.cache_data(
    show_spinner=False,
    ttl=1800,
)
def cached_review(campground):
    return get_campground_review_summary(
        campground
    )


@st.cache_data(
    show_spinner=False,
    ttl=300,
)
def cached_sites(
    campground_id,
    check_in,
    nights,
):
    return get_available_site_details(
        campground_id,
        check_in,
        nights,
    )


@st.cache_data(
    show_spinner=False,
    ttl=300,
)
def cached_flexible_dates(
    campground_id,
    start_date,
    end_date,
    nights,
    friday_saturday_only,
):
    return search_possible_dates_parallel(
        campground_id,
        start_date,
        end_date,
        nights,
        friday_saturday_only,
        max_workers=4,
    )


def reset_search_state():
    st.session_state["availability_ready"] = False
    st.session_state["page"] = "dates"

    for key in [
        "selected_date",
        "selected_campground",
        "selected_review",
        "selected_nights",
    ]:
        st.session_state.pop(key, None)


if "page" not in st.session_state:
    st.session_state["page"] = "dates"

if "availability_ready" not in st.session_state:
    st.session_state["availability_ready"] = False


title()
st.caption(APP_VERSION)
page_nav()


with st.sidebar:
    st.header("Search")

    park_query = st.text_input(
        "Park or campground",
        key="park-query",
    )

    start_date = st.date_input(
        "Start date",
        key="start-date",
    )

    end_date = st.date_input(
        "End date",
        key="end-date",
    )

    nights = st.number_input(
        "Nights",
        min_value=1,
        max_value=14,
        value=2,
        step=1,
        key="nights",
    )

    flexible = st.checkbox(
        "Flexible date-range search",
        value=True,
        key="flexible-search",
    )

    friday_saturday_only = st.checkbox(
        "Friday/Saturday check-ins only",
        value=False,
        key="weekend-filter",
    )

    find_clicked = st.button(
        "Find campgrounds",
        use_container_width=True,
        key="find-campgrounds",
    )


if find_clicked:
    if not park_query.strip():
        st.warning(
            "Enter a park or campground name."
        )
    else:
        try:
            with st.spinner(
                "Finding campgrounds..."
            ):
                results = (
                    cached_search_campgrounds(
                        park_query.strip()
                    )
                )

            st.session_state["campgrounds"] = (
                results
            )

            reset_search_state()

        except Exception as error:
            st.error(
                f"Campground search failed: {error}"
            )


if "campgrounds" not in st.session_state:
    st.info(
        "Enter a park or campground name in "
        "the sidebar to begin."
    )
    st.stop()


campgrounds = st.session_state["campgrounds"]

if not campgrounds:
    st.warning(
        "No campground results were found. "
        "Try a more specific campground name."
    )
    st.stop()


campground_labels = [
    f"{campground['name']} | ID {campground['id']}"
    for campground in campgrounds
]


selected_labels = st.multiselect(
    "Select campground(s)",
    campground_labels,
    default=[campground_labels[0]],
    key="selected-campgrounds",
)


selected_campgrounds = [
    campgrounds[campground_labels.index(label)]
    for label in selected_labels
]


if not selected_campgrounds:
    st.warning(
        "Select at least one campground."
    )
    st.stop()


if st.button(
    "Search Availability",
    use_container_width=True,
    key="search-availability",
):
    st.session_state[
        "availability_ready"
    ] = True

    st.session_state["page"] = "dates"

    for key in [
        "selected_date",
        "selected_campground",
        "selected_review",
        "selected_nights",
    ]:
        st.session_state.pop(key, None)


if not st.session_state[
    "availability_ready"
]:
    st.info(
        "Select one or more campgrounds, "
        "then choose Search Availability."
    )
    st.stop()


start_datetime = to_datetime(start_date)
end_datetime = to_datetime(end_date)


if end_datetime < start_datetime:
    st.error(
        "The end date must be on or after "
        "the start date."
    )
    st.stop()


if st.session_state["page"] == "dates":
    section_title("Available Dates")

    for campground_index, campground in enumerate(
        selected_campgrounds
    ):
        try:
            with st.spinner(
                f"Loading information for "
                f"{campground['name']}..."
            ):
                review = cached_review(
                    campground
                )

            campground_summary(
                campground,
                review,
            )

            official_map_button(campground)

            campground_feedback_widget(
                campground
            )

            if flexible:
                with st.spinner(
                    "Searching available dates..."
                ):
                    dates = cached_flexible_dates(
                        campground["id"],
                        start_datetime,
                        end_datetime,
                        int(nights),
                        friday_saturday_only,
                    )

                if not dates:
                    st.warning(
                        "No available dates were found "
                        "for this campground."
                    )
                    continue

                date_columns = st.columns(3)

                for date_index, date_item in enumerate(
                    dates
                ):
                    column = date_columns[
                        date_index % 3
                    ]

                    with column:
                        date_card(
                            date_item,
                            campground,
                            int(nights),
                            review,
                            unique_suffix=(
                                f"{campground_index}-"
                                f"{date_index}"
                            ),
                        )

            else:
                with st.spinner(
                    "Searching available sites..."
                ):
                    sites = cached_sites(
                        campground["id"],
                        start_datetime,
                        int(nights),
                    )

                if not sites:
                    st.warning(
                        "No available sites were found "
                        "for the selected date."
                    )
                    continue

                section_title("Available Sites")

                sorted_sites = sorted(
                    sites,
                    key=lambda site: (
                        combined_site_score(
                            site,
                            review,
                        ),
                        str(site.get("site", "")),
                    ),
                    reverse=True,
                )

                for site in sorted_sites[:6]:
                    reservation_card(
                        site,
                        campground,
                        start_date,
                        int(nights),
                        review,
                    )

        except Exception as error:
            st.error(
                f"Unable to load "
                f"{campground['name']}: {error}"
            )


elif st.session_state["page"] == "sites":
    selected_date = st.session_state.get(
        "selected_date"
    )

    selected_campground = (
        st.session_state.get(
            "selected_campground"
        )
    )

    selected_review = (
        st.session_state.get(
            "selected_review"
        )
    )

    selected_nights = int(
        st.session_state.get(
            "selected_nights",
            nights,
        )
    )

    if (
        not selected_date
        or not selected_campground
        or not selected_review
    ):
        st.info(
            "Choose a date from the Available "
            "Dates page first."
        )

        if st.button(
            "Return to Available Dates",
            key="empty-sites-back",
        ):
            st.session_state["page"] = "dates"
            st.rerun()

        st.stop()


    section_title(
        f"Sites for {selected_date}"
    )

    st.write(
        selected_campground["name"]
    )

    official_map_button(
        selected_campground
    )


    if st.button(
        "← Back to Available Dates",
        key="back-to-dates",
    ):
        st.session_state["page"] = "dates"
        st.rerun()


    selected_datetime = datetime.strptime(
        selected_date,
        "%Y-%m-%d",
    )


    try:
        with st.spinner(
            "Loading available campsites..."
        ):
            sites = cached_sites(
                selected_campground["id"],
                selected_datetime,
                selected_nights,
            )

    except Exception as error:
        st.error(
            f"Unable to load campsites: {error}"
        )
        st.stop()


    if not sites:
        st.warning(
            "No campsites are currently available "
            "for this date and stay length."
        )
        st.stop()


    sorted_sites = sorted(
        sites,
        key=lambda site: (
            combined_site_score(
                site,
                selected_review,
            ),
            str(site.get("site", "")),
        ),
        reverse=True,
    )


    st.caption(
        f"Showing the highest-rated "
        f"{min(6, len(sorted_sites))} of "
        f"{len(sorted_sites)} available sites."
    )


    for site in sorted_sites[:6]:
        reservation_card(
            site,
            selected_campground,
            selected_date,
            selected_nights,
            selected_review,
        )