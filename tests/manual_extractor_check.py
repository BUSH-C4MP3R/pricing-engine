"""Manual check for LLM extraction. Requires Ollama running."""

from rag.extractor import extract_product_data

sample_context = """
The current list price for Biologics-A is $100.00 per unit.
Inflation is 3% (0.03). Input costs rose 2% (0.02).
Last price change was 10% (0.10) and volume fell 30% (-0.30).
"""

result = extract_product_data(sample_context)
print("LLM extracted:")
print(result)
