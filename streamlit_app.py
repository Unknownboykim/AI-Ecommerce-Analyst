"""
streamlit_app.py
----------------
Web version of the analyst. Choose a question from the sidebar menu or
search by terms, see the results table and chart, and optionally ask the
AI for a written analysis.

Usage:
    streamlit run streamlit_app.py
"""

import streamlit as st

from analyst import llm
from analyst.config import DB_PATH
from analyst.database import run_sql
from analyst.queries import GROUPS, Query, get_query, queries_in_group
from analyst.search import search

st.set_page_config(page_title="Ecommerce AI Analyst", layout="wide")


@st.cache_resource(show_spinner="Building the database for the first time...")
def ensure_database() -> None:
    """Build the database on first launch (for example on Streamlit Cloud)."""
    if not DB_PATH.exists():
        from build_database import build
        build()


@st.cache_data(show_spinner=False)
def load_result(key: str):
    return run_sql(get_query(key).sql)


@st.cache_data(show_spinner="Writing analysis...")
def load_analysis(key: str) -> str:
    q = get_query(key)
    return llm.analyze(q.question, load_result(key))


def sidebar() -> Query:
    st.sidebar.title("Ecommerce AI Analyst")

    terms = st.sidebar.text_input("Search by terms", placeholder="discount, low stock, revenue...")
    if terms.strip():
        matches = search(terms, limit=8)
        if matches:
            return st.sidebar.radio(
                f"{len(matches)} matching questions",
                matches,
                format_func=lambda q: q.title,
            )
        st.sidebar.info("No question matches those terms. Browse the menu below instead.")

    group = st.sidebar.selectbox("Topic", GROUPS)
    return st.sidebar.radio("Question", queries_in_group(group), format_func=lambda q: q.title)


def main() -> None:
    ensure_database()
    query = sidebar()

    st.caption(query.group)
    st.header(query.question)

    df = load_result(query.key)

    col_table, col_chart = st.columns([3, 2]) if query.chart and not df.empty else (st.container(), None)
    with col_table:
        st.dataframe(df, width="stretch", hide_index=True)
        st.caption(f"{len(df)} rows")
    if col_chart is not None:
        x, y = query.chart
        with col_chart:
            st.bar_chart(df, x=x, y=y, horizontal=True)

    with st.expander("Show the SQL behind this answer"):
        st.code(query.sql.strip(), language="sql")

    st.subheader("AI analysis")
    if not llm.is_configured():
        st.info("Set OPENAI_API_KEY in your .env file (or Streamlit secrets) to turn on AI analysis.")
        return

    if st.button("Analyze these results", type="primary"):
        st.session_state[f"analyze_{query.key}"] = True

    if st.session_state.get(f"analyze_{query.key}"):
        try:
            st.write(load_analysis(query.key))
        except RuntimeError as e:
            st.error(str(e))


main()
