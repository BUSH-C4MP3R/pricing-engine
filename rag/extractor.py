"""
Use a local Ollama LLM to extract structured pricing inputs from context.
The LLM returns JSON ONLY — it performs no pricing math.
"""

import json
from openai import OpenAI

# Point the OpenAI SDK at the local Ollama server
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # placeholder — Ollama doesn't check this
)

EXTRACTION_PROMPT = """
You are a data extraction assistant. From the context below, extract these
fields for the product and return them as STRICT JSON only (no prose):

- product (string)
- current_price (float)
- inflation (float, as decimal e.g. 0.03)
- cost_change (float, as decimal)
- last_price_change (float, as decimal)
- volume_change (float, as decimal)

Do NOT calculate prices. Only extract values found in the context.
If a value is not present, use 0.0.

Context:
{context}
"""


def extract_product_data(context: str) -> dict:
    """Send retrieved context to the local LLM and parse structured JSON back."""
    response = client.chat.completions.create(
        model="llama3.1",
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(context=context)}
        ],
        response_format={"type": "json_object"},
        temperature=0,  # deterministic extraction
    )
    return json.loads(response.choices[0].message.content)


MACRO_EXTRACTION_PROMPT = """
You are a data extraction assistant. From the context below (an inflation/cost
report), extract the estimated rate for each of these exact product categories:

{categories}

Return STRICT JSON only (no prose), shaped exactly like:
{{
  "<category>": {{"low": <percent>, "high": <percent>}},
  ...
}}

Rules:
- Use ONLY the category strings listed above as keys, copied exactly.
- Report rates as plain percentage numbers, e.g. "4%" -> 4 (NOT 0.04, NOT 4%).
- If a category has a range (e.g. "3.5-4.5%"), set low=3.5 and high=4.5.
- If a category has a single rate rather than a range, set low and high to the
  same number.
- Do NOT average, convert, or calculate anything — copy the numbers as written.
- The context may use similar-but-not-identical category names — match each
  listed category to the closest relevant data in the context. Known synonyms:
  "Instruments" means the same bucket as "Units".
- If you cannot find data for a category, omit it entirely — do not guess.

Context:
{context}
"""


def extract_macro_data(context: str, categories: list[str]) -> dict:
    """Send retrieved macro-doc context to the local LLM and parse a
    per-category {category: {"low": pct, "high": pct}} JSON dict back.
    Percent-to-decimal conversion and midpoint math happen in Python
    (pipeline._clean_macro), not in the LLM — small local models were
    getting that arithmetic wrong (e.g. "3.5-4.5%" -> 0.375 instead of 0.04)."""
    prompt = MACRO_EXTRACTION_PROMPT.format(
        categories="\n".join(f"- {c}" for c in categories), context=context
    )
    response = client.chat.completions.create(
        model="llama3.1",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)