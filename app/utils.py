# app/utils.py
import typer
from typing import List, Tuple
from graphrag_sdk import Ontology

def normalise_schema(raw: dict) -> dict:
    """
    Ensure every attribute dict has 'type', 'unique', 'required' keys.
    Adds sensible defaults if they are missing.
    """
    for ent in raw.get("entities", []):
        for attr in ent.get("attributes", []):
            attr.setdefault("type", "string")
            attr.setdefault("unique", False)
            attr.setdefault("required", False)
    return raw

def merge_ontologies(a: Ontology, b: Ontology) -> Ontology:
    """
    Return a new Ontology containing the union of entities / relations
    from A and B.
    """
    def _by_label(seq):
        return {item.label: item for item in seq}

    ent_map = _by_label(a.entities)
    for ent in b.entities:
        ent_map.setdefault(ent.label, ent)

    rel_map = _by_label(a.relations)
    for rel in b.relations:
        rel_map.setdefault(rel.label, rel)

    return Ontology(list(ent_map.values()), list(rel_map.values()))

def print_table(rows: List[Tuple[str, str]], title: str = "") -> None:
    """Prints a formatted table to the console."""
    if title:
        typer.secho(f"\n{title}", fg=typer.colors.BRIGHT_BLUE, bold=True)
    if not rows:
        return
    # Find the maximum width for the first column
    w = max(len(r[0]) for r in rows) if rows else 0
    for l, r in rows:
        typer.echo(f"  {l.ljust(w)}  {r}")