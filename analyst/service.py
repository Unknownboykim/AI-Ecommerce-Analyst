"""
service.py
----------
The one function both front ends call: run a catalog query and, if asked,
add the AI write-up.

    menu pick or search  ->  Query  ->  run_sql()  ->  DataFrame  ->  llm.analyze()
"""

from dataclasses import dataclass

import pandas as pd

from analyst import llm
from analyst.database import run_sql
from analyst.queries import Query, get_query


@dataclass
class Answer:
    query: Query
    data: pd.DataFrame
    analysis: str | None = None   # None when AI was not requested or not available
    note: str | None = None       # explains why analysis is missing, if it is


def answer(query: Query | str, with_analysis: bool = True) -> Answer:
    """Run one catalog query by object or key, optionally with AI analysis."""
    if isinstance(query, str):
        query = get_query(query)

    df = run_sql(query.sql)
    result = Answer(query=query, data=df)

    if not with_analysis:
        return result
    if not llm.is_configured():
        result.note = "AI analysis is off. Set OPENAI_API_KEY in .env to turn it on."
        return result

    try:
        result.analysis = llm.analyze(query.question, df)
    except RuntimeError as e:
        result.note = str(e)
    return result
