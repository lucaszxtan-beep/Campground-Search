import html

import streamlit as st

from feedback_core import (
    add_feedback,
    get_feedback_summary,
)

from scoring import (
    color_from_score,
    combined_site_score,
    stars_from_score,
)


def inject_css():
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            font-size: 17px !important;
        }

        .big-title {
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .section-title {
            font-size: 24px;
            font-weight: 700;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }

        .card {
            border-radius: 18px;
            padding: 16px;
            margin: 10px 0;
            border: 2px solid #dddddd;
            background-color: #fafafa;
        }

        .important {
            background-color: #fff3cd;
            border-left: 10px solid #b7791f;
            padding: 10px;
            border-radius: 10px;
            margin: 8px 0;
        }

        .strength {
            background-color: #d8f3dc;
            border-left: 10px solid #2e7d32;
            padding: 10px;
            border-radius: 10px;
            margin: 8px 0;
        }

        .concern {
            background-color: #fde2e2;
            border-left: 10px solid #c62828;
            padding: 10px;
            border-radius: 10px;
            margin: 8px 0;
        }

        .stars {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: 1px;
        }

        .reserve-info {
            font-size: 18px;
            line-height: 1.55;
        }

        .rating-note {
            margin-top: 8px;
            color: #555555;
            font-size: 15px;
        }

        div.stButton > button,
        div.stLinkButton > a {
            font-size: 18px !important;
            border-radius: 14px;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def title():
    st.markdown(
        '<div class="big-title">🏕️ Campsite Finder</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "Find available campsites and open the official "
        "reservation page."
    )


def section_title(text):
    st.markdown(
        f'<div class="section-title">{html.escape(str(text))}</div>',
        unsafe_allow_html=True,
    )


def page_nav():
    dates_column, sites_column = st.columns(2)

    with dates_column:
        if st.button(
            "🗓 Available Dates",
            use_container_width=True,
            key="navigation-dates",
        ):
            st.session_state["page"] = "dates"
            st.rerun()

    with sites_column:
        if st.button(
            "🏕 Campsites",
            use_container_width=True,
            key="navigation-sites",
        ):
            st.session_state["page"] = "sites"
            st.rerun()


def color_block(title_text, items, css_class):
    if not items:
        return

    item_lines = "".join(
        f"• {html.escape(str(item))}<br>"
        for item in items
    )

    st.markdown(
        (
            f'<div class="{css_class}">'
            f"<b>{html.escape(title_text)}</b><br>"
            f"{item_lines}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def campground_summary(campground, review):
    score = review.get("review_score", 70)
    stars = stars_from_score(score)
    star_color = color_from_score(score)

    campground_name = html.escape(
        str(campground["name"])
    )

    st.markdown(
        f"""
        <div class="card">
            <div style="font-size:28px;font-weight:800;">
                {campground_name}
            </div>
            <div class="stars" style="color:{star_color};">
                {stars}
            </div>
            <div class="rating-note">
                Campground rating is based on available public
                campground-level information.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    color_block(
        "Important Information",
        review.get("important", []),
        "important",
    )

    color_block(
        "Strengths",
        review.get("positives", []),
        "strength",
    )

    color_block(
        "Potential Concerns",
        review.get("negatives", []),
        "concern",
    )


def official_map_button(campground):
    st.link_button(
        "Open official Recreation.gov page and map",
        campground["url"],
        use_container_width=False,
    )


def campground_feedback_widget(campground):
    campground_id = str(campground["id"])
    summary = get_feedback_summary(campground)

    st.markdown("### Visitor Feedback")

    if summary["total"] == 0:
        st.caption(
            "No visitor feedback has been submitted yet."
        )
    else:
        st.write(
            f"👍 {summary['thumbs_up']}    "
            f"👎 {summary['thumbs_down']}    "
            f"{summary['percent_positive']}% positive"
        )

    vote_key = f"feedback-vote-{campground_id}"

    already_voted = (
        st.session_state.get(vote_key) is not None
    )

    up_column, down_column = st.columns(2)

    with up_column:
        if st.button(
            "👍 Helpful campground",
            key=f"feedback-up-{campground_id}",
            use_container_width=True,
            disabled=already_voted,
        ):
            add_feedback(campground, "up")
            st.session_state[vote_key] = "up"
            st.rerun()

    with down_column:
        if st.button(
            "👎 Not recommended",
            key=f"feedback-down-{campground_id}",
            use_container_width=True,
            disabled=already_voted,
        ):
            add_feedback(campground, "down")
            st.session_state[vote_key] = "down"
            st.rerun()

    if already_voted:
        st.success(
            "Thank you. Your feedback has been recorded "
            "for this session."
        )


def reservation_card(
    site,
    campground,
    check_in,
    nights,
    review,
):
    combined_score = combined_site_score(
        site,
        review,
    )

    stars = stars_from_score(combined_score)
    star_color = color_from_score(combined_score)

    rating_reasons = site.get(
        "score_reasons",
        [
            "Recreation.gov provides limited "
            "comparison information."
        ],
    )

    reasons_text = "; ".join(
        html.escape(str(reason))
        for reason in rating_reasons
    )

    st.markdown(
        f"""
        <div class="card">
            <div style="font-size:28px;font-weight:800;">
                Site {html.escape(str(site["site"]))}
            </div>

            <div class="stars" style="color:{star_color};">
                {stars}
            </div>

            <div class="reserve-info">
                <b>Campground:</b>
                {html.escape(str(campground["name"]))}<br>

                <b>Check-in:</b>
                {html.escape(str(check_in))}<br>

                <b>Nights:</b>
                {html.escape(str(nights))}<br>

                <b>Loop:</b>
                {html.escape(str(site["loop"]))}<br>

                <b>Type:</b>
                {html.escape(str(site["campsite_type"]))}<br>

                <b>Maximum occupancy:</b>
                {html.escape(str(site["max_num_people"]))}<br>

                <b>Equipment length:</b>
                {html.escape(str(site["equipment_length"]))}<br>

                <b>Rating factors:</b>
                {reasons_text}
            </div>

            <div class="rating-note">
                The campsite rating combines the listed site
                characteristics with campground-level public
                review information. Sites with identical listed
                information receive the same score.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.link_button(
        "Reserve or view on Recreation.gov",
        campground["url"],
    )


def date_card(
    date_item,
    campground,
    nights,
    review,
    unique_suffix="",
):
    best_site = date_item.get("best_site") or {}
    best_site_name = best_site.get("site", "Unknown")

    if best_site:
        date_score = combined_site_score(
            best_site,
            review,
        )
    else:
        date_score = review.get(
            "review_score",
            70,
        )

    stars = stars_from_score(date_score)
    star_color = color_from_score(date_score)

    st.markdown(
        f"""
        <div class="card">
            <div style="font-size:26px;font-weight:800;">
                {html.escape(str(date_item["date"]))}
            </div>

            <div class="stars" style="color:{star_color};">
                {stars}
            </div>

            <div class="reserve-info">
                <b>Available sites:</b>
                {html.escape(str(date_item["count"]))}<br>

                <b>Highest-rated available site:</b>
                {html.escape(str(best_site_name))}
            </div>

            <div class="rating-note">
                The date uses the rating of its highest-rated
                available campsite. The number of open sites
                does not artificially increase the rating.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    button_key = (
        f"show-sites-{campground['id']}-"
        f"{date_item['date']}-{unique_suffix}"
    )

    if st.button(
        f"Show sites for {date_item['date']}",
        key=button_key,
        use_container_width=True,
    ):
        st.session_state["selected_date"] = (
            date_item["date"]
        )

        st.session_state["selected_campground"] = (
            campground
        )

        st.session_state["selected_review"] = review
        st.session_state["selected_nights"] = int(nights)
        st.session_state["page"] = "sites"

        st.rerun()