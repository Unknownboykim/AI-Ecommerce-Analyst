"""
llm.py
------
Turns a query result into a short written analysis using OpenAI.

The model never sees the database and never writes SQL. It only receives
the business question and the rows that the pre-written query returned,
and is told to answer from that data alone.
"""

import pandas as pd

from analyst.config import LLM_MAX_ROWS, LLM_MAX_TOKENS, OPENAI_API_KEY, OPENAI_MODEL

SYSTEM_PROMPT = """You are a concise ecommerce data analyst writing for a business stakeholder.
Rules:
- Use ONLY the data provided. Do not invent numbers.
- Reference specific values (names, amounts, percentages) from the data.
- Start with a one sentence direct answer, then 2 to 4 short bullet points of supporting detail.
- End with one practical recommendation.
- If the data is empty or not enough to answer, say so plainly.
- Plain text only. Do not use em dashes or emojis."""


def is_configured() -> bool:
    """True when an API key is available."""
    return bool(OPENAI_API_KEY)


def format_table(df: pd.DataFrame, max_rows: int = LLM_MAX_ROWS) -> str:
    """Render a DataFrame as a plain text table for the prompt."""
    if df.empty:
        return "(no rows returned)"
    table = df.head(max_rows).to_string(index=False)
    if len(df) > max_rows:
        table += f"\n... {len(df) - max_rows} more rows not shown"
    return table


def build_prompt(question: str, df: pd.DataFrame) -> str:
    return f"QUESTION:\n{question}\n\nDATA ({len(df)} rows):\n{format_table(df)}"


def analyze(question: str, df: pd.DataFrame) -> str:
    """
    Send the question and the result rows to the model and return its answer.
    Raises RuntimeError if the key is missing or the API call fails.
    """
    if not is_configured():
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file to enable AI analysis.")

    # Imported here so the rest of the app works without the openai package
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(question, df)},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}") from e

    return clean_text(response.choices[0].message.content or "")


def clean_text(text: str) -> str:
    """Replace em and en dashes in model output with plain hyphens."""
    return text.replace("\u2014", " - ").replace("\u2013", "-").strip()
