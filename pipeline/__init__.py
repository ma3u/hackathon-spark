"""graph-protokoll — Audio-Sitzungsmitschnitt -> Protokoll-Knowledge-Graph + GraphRAG.

Pipeline:  Audio -> ASR (asr) -> Diarisierung (diarize) -> Alignment (align)
           -> Extraktion (extract) -> Graph (graph_build) -> Export/GraphRAG.
"""

from .graphrag import GraphRAG
from .graph_build import build_graph
from .extract import extract_rule_based, Protocol
from .factcheck import factcheck_rule_based, FactCheck

__all__ = ["GraphRAG", "build_graph", "extract_rule_based", "Protocol",
           "factcheck_rule_based", "FactCheck"]
