from typing import List

from state_renormalization.contracts import SchemaHit


def suggest_schemaorg_hits(text: str, *, top_n: int = 8) -> List[SchemaHit]:
    """Placeholder adapter: schema.org suggestions are currently unavailable."""
    del text, top_n
    return []
