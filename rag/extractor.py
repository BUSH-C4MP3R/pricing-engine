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