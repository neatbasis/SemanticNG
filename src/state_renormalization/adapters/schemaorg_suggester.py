from typing import Optional, List
from state_renormalization.contracts import SchemaHit, AmbiguityAbout, AboutKind

def suggest_schemaorg_hits(text: str, *, top_n: int = 8) -> List[SchemaHit]:
    ...
