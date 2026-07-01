"""Shared helpers for graph-shaped API payloads.

These helpers do not build graph relationships. They annotate already-built
payloads so UOM, domain graph providers, and Knowledge Graph endpoints can
advertise their source and vocabulary without changing existing node/edge
shapes.
"""


def _edge_type(edge):
    rel = edge.get("relationship") or edge.get("type") or ""
    return str(rel).strip().upper()


def annotate_graph(graph, source, vocabulary, semantics="", mutate=False):
    """Return a graph payload with standard metadata and edge type aliases.

    Existing consumers rely on `relationship`; Knowledge Graph consumers use
    `type`. Keep both when possible so endpoints can converge without breaking
    current UI behavior.
    """
    payload = graph if mutate else dict(graph or {})
    nodes = list(payload.get("nodes") or [])
    edges = [dict(edge) for edge in (payload.get("edges") or [])]

    for edge in edges:
        edge_type = _edge_type(edge)
        if edge_type:
            edge.setdefault("type", edge_type)
            edge.setdefault("relationship", edge_type)

    payload["nodes"] = nodes
    payload["edges"] = edges
    payload["_source"] = source
    payload["_vocabulary"] = vocabulary
    if semantics:
        payload["_semantics"] = semantics
    return payload
