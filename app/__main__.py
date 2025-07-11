# app/__main__.py
import os
import json
import traceback
import typer
from dotenv import load_dotenv
from pathlib import Path  

import textwrap
from typing import Dict, Any, List, Tuple
import random

try:
    from pyvis.network import Network
except ImportError:
    Network = None  # we’ll error politely later


# GraphRAG-SDK imports
from graphrag_sdk import KnowledgeGraph, Ontology, Source  # ← Source is new
from graphrag_sdk.models.litellm import LiteModel
from graphrag_sdk.model_config import KnowledgeGraphModelConfig

# ── App setup ────────────────────────────────────────────
app = typer.Typer(help="A CLI to build and query a PDF Knowledge Graph using the GraphRAG-SDK.")
load_dotenv()

# ── Configuration ────────────────────────────────────────
INITIAL_PDF_DIR   = "data/initial_pdfs"
ADDITIONAL_PDF_DIR = "data/additional_pdfs"
GRAPH_NAME        = "assignment_kg"
FALKORDB_HOST     = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT     = 6379
ONTOLOGY_FILE      = "ontology.json"
ONTO_PATH          = Path(ONTOLOGY_FILE) 

def _normalise_schema(raw: dict) -> dict:
    """
    Ensure every attribute dict has 'type', 'unique', 'required' keys.
    Adds sensible defaults if they are missing.
    """
    for ent in raw.get("entities", []):
        for attr in ent.get("attributes", []):
            attr.setdefault("type",     "string")
            attr.setdefault("unique",   False)
            attr.setdefault("required", False)
    return raw


# ── local fallback when SDK lacks Ontology.merge ────────────────
def _merge_ontologies(a: Ontology, b: Ontology) -> Ontology:
    """
    Return a new Ontology containing the union of entities / relations
    from A and B.  Very small utility until we upgrade the SDK.
    """
    def _by_label(seq):          # helper → dict keyed by label
        return {item.label: item for item in seq}

    ent_map = _by_label(a.entities)
    for ent in b.entities:
        ent_map.setdefault(ent.label, ent)

    rel_map = _by_label(a.relations)
    for rel in b.relations:
        rel_map.setdefault(rel.label, rel)

    return Ontology(list(ent_map.values()), list(rel_map.values()))

def _print_table(rows: List[Tuple[str, str]], title: str = "") -> None:
    if title:
        typer.secho(f"\n{title}", fg=typer.colors.BRIGHT_BLUE, bold=True)
    w = max(len(r[0]) for r in rows) if rows else 0
    for l, r in rows:
        typer.echo(f"  {l.ljust(w)}  {r}")

@app.command()
def build() -> None:
    """Build and evolve the knowledge graph from all PDF files."""
    typer.echo("🚀 Starting the knowledge-graph build process…")
    try:
        # ── Step 1: Create ontology ───────────────────────
        typer.echo("--- Step 1: Creating Ontology ---")
        initial_sources = [
            Source(os.path.join(INITIAL_PDF_DIR, f))
            for f in os.listdir(INITIAL_PDF_DIR)
            if f.endswith(".pdf")
        ]

        model = LiteModel(model_name="openai/gpt-4o")

        typer.echo(f"Creating ontology from {len(initial_sources)} initial PDFs, one by one…")
        successful_sources: list[Source] = []

        for i, src in enumerate(initial_sources):
            fname = os.path.basename(src.data_source)
            typer.echo(f"\n--- Processing file {i + 1}/{len(initial_sources)}: {fname} ---")
            try:
                Ontology.from_sources([src], model=model)
                typer.secho(f"✅ Successfully processed {fname}", fg=typer.colors.GREEN)
                successful_sources.append(src)
            except Exception as e:
                typer.secho(f">>>> FAILED on file: {fname} <<<<", fg=typer.colors.RED)
                traceback.print_exception(e)

        if not successful_sources:
            typer.secho("No PDFs could be processed successfully. Aborting.", fg=typer.colors.RED)
            raise typer.Exit()

        typer.echo("🔍  Discovering ontology from PDFs …")
        discovered = Ontology.from_sources(initial_sources, model=model)

        # ── 3. Option A – merge with existing file ────────
        if ONTO_PATH.exists():
            typer.echo("📄  Merging with existing ontology.json")
            raw_json  = json.loads(ONTO_PATH.read_text())
            existing  = Ontology.from_json(_normalise_schema(raw_json)) 
            ontology  = _merge_ontologies(existing, discovered) 
        else:
            typer.echo("📄  No existing ontology.json, using discovered one")
            ontology   = discovered

        ONTO_PATH.write_text(json.dumps(ontology.to_json(), indent=2))
        typer.secho("✓  ontology.json updated", fg=typer.colors.GREEN)

        # ── Step 2: Create and evolve the knowledge graph ─
        typer.echo("\n--- Step 2: Creating and Evolving Knowledge Graph ---")
        kg = KnowledgeGraph(
            name=GRAPH_NAME,
            model_config=KnowledgeGraphModelConfig.with_model(model),
            ontology=ontology,
            host=FALKORDB_HOST,
            port=FALKORDB_PORT,
        )

        typer.echo(f"\nIngesting {len(successful_sources)} initial PDFs…")
        kg.process_sources(successful_sources)
        typer.secho("✅ Initial ingestion complete.", fg=typer.colors.GREEN)

        typer.echo("\nEvolving graph with all available PDFs…")
        additional_sources = [
            Source(os.path.join(ADDITIONAL_PDF_DIR, f))
            for f in os.listdir(ADDITIONAL_PDF_DIR)
            if f.endswith(".pdf")
        ]
        all_sources = successful_sources + additional_sources

        kg.process_sources(all_sources)
        typer.secho("✅ Graph evolution complete.", fg=typer.colors.GREEN)

        typer.secho("\n🎉 Knowledge-graph build finished successfully!", fg=typer.colors.BRIGHT_GREEN)

    except Exception as e:
        typer.secho(f"🔥 A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Your natural-language question."),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Print context and Cypher as well"
    ),
):
    """Ask a question against the knowledge graph."""
    typer.echo(f"❓ Asking: '{question}'")
    try:
        if not os.path.exists(ONTOLOGY_FILE):
            typer.secho(
                f"Error: Ontology file '{ONTOLOGY_FILE}' not found. Run the 'build' command first.",
                fg=typer.colors.RED,
            )
            raise typer.Exit()

        with open(ONTOLOGY_FILE, "r", encoding="utf-8") as file:
            ontology = Ontology.from_json(json.load(file))

        model = LiteModel(model_name="openai/gpt-4o")

        kg = KnowledgeGraph(
            name=GRAPH_NAME,
            model_config=KnowledgeGraphModelConfig.with_model(model),
            ontology=ontology,
            host=FALKORDB_HOST,
            port=FALKORDB_PORT,
        )

        typer.echo("  - Starting chat session…")
        response = kg.chat_session().send_message(question)

        typer.secho("✅ Answer:", fg=typer.colors.GREEN)
        typer.echo(response['response'])

    except Exception as e:
        typer.secho(f"🔥 A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)


def _print_table(rows: List[Tuple[str, str]], title: str = "") -> None:
    if title:
        typer.secho(f"\n{title}", fg=typer.colors.BRIGHT_BLUE, bold=True)
    col1_len = max(len(r[0]) for r in rows) if rows else 0
    for left, right in rows:
        typer.echo(f"  {left.ljust(col1_len)}  {right}")

@app.command()
def schema(
    counts: bool = typer.Option(
        False,
        "--counts",
        "-c",
        help="Query FalkorDB and show live counts for each label/relation.",
    )
) -> None:
    """Show the ontology (labels, attributes, relations) and optionally instance counts."""
    try:
        # ----- load ontology -----
        if not os.path.exists(ONTOLOGY_FILE):
            typer.secho(
                f"Ontology file '{ONTOLOGY_FILE}' not found. Run the 'build' command first.",
                fg=typer.colors.RED,
            )
            raise typer.Exit()

        with open(ONTOLOGY_FILE, "r", encoding="utf-8") as fh:
            ontology = Ontology.from_json(json.load(fh))

        # convert to dict form so we can sub-script
        schema_dict = ontology.to_json()
        ent_dicts   = schema_dict["entities"]
        rel_dicts   = schema_dict["relations"]

        # ----- print entity labels -----
        node_rows = [
            (
                ent["label"],
                ", ".join(attr["name"] for attr in ent.get("attributes", [])) or "—",
            )
            for ent in ent_dicts
        ]
        _print_table(node_rows, "📦  ENTITY LABELS")

        # ----- print relation labels -----
        rel_rows = [
            (
                rel["label"],
                f'{rel["source"]["label"]} → {rel["target"]["label"]}',
            )
            for rel in rel_dicts
        ]
        _print_table(rel_rows, "🔗  RELATIONS")

        # ----- optional live counts -----
        if counts:
            try:
                import redis.asyncio as redis
            except ImportError:
                typer.secho(
                    "⚠️  Install redis-py (pip install redis) to use --counts.", fg=typer.colors.YELLOW
                )
                raise typer.Exit()

            import asyncio

            async def _count_labels() -> Tuple[dict, dict]:
                r = redis.Redis(host=FALKORDB_HOST, port=FALKORDB_PORT, decode_responses=True)
                node_ct, edge_ct = {}, {}
                for lbl, _ in node_rows:
                    q = f"MATCH (n:{lbl}) RETURN count(n)"
                    res = await r.execute_command("GRAPH.QUERY", GRAPH_NAME, q, "--compact")
                    node_ct[lbl] = int(res[1][0])  # [[count]]
                for lbl, _ in rel_rows:
                    q = f"MATCH ()-[:{lbl}]->() RETURN count(*)"
                    res = await r.execute_command("GRAPH.QUERY", GRAPH_NAME, q, "--compact")
                    edge_ct[lbl] = int(res[1][0])
                await r.close()
                return node_ct, edge_ct

            node_counts, edge_counts = asyncio.run(_count_labels())
            _print_table([(k, str(v)) for k, v in node_counts.items()], "📊  NODE COUNTS")
            _print_table([(k, str(v)) for k, v in edge_counts.items()], "📊  EDGE COUNTS")

    except Exception as e:
        typer.secho(f"🔥 A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)



@app.command()
def visualize(
    output: str = typer.Option(
        "graph.html", "--output", "-o",
        help="Name of the HTML file to generate (default: graph.html)",
    ),
    limit: int = typer.Option(
        750, "--limit", "-l",
        help="Maximum number of edges to pull from the DB.",
    ),
) -> None:
    """Generate an interactive PyVis HTML visualisation of the current graph."""
    typer.echo("Generating interactive graph visualization...")
    try:
        if Network is None:
            typer.secho("❌  Install pyvis (`pip install pyvis`) to use visualize.",
                        fg=typer.colors.RED)
            raise typer.Exit()

        try:
            import redis.asyncio as redis
        except ImportError:
            typer.secho("❌  Install redis-py (`pip install redis`) to use visualize.",
                        fg=typer.colors.RED)
            raise typer.Exit()

        # ── pull edge rows ──────────────────────────────────────────────
        async def _fetch_edges(lim: int) -> List[List[Any]]:
            r = redis.Redis(host=FALKORDB_HOST, port=FALKORDB_PORT,
                            decode_responses=True)

            # NEW: Query now includes node degrees to size nodes by importance
            query = f"""
            MATCH (a)-[r]->(b)
            RETURN id(a)                                   AS from_id,
                   id(b)                                   AS to_id,
                   labels(a)[0]                            AS from_label,
                   labels(b)[0]                            AS to_label,
                   type(r)                                 AS rel,
                   coalesce(a.title, a.name, labels(a)[0]) AS from_text,
                   coalesce(b.title, b.name, labels(b)[0]) AS to_text,
                   size((a)--())                           AS from_degree,
                   size((b)--())                           AS to_degree
            LIMIT {lim}
            """
            raw = await r.execute_command("GRAPH.QUERY", GRAPH_NAME, query, "--compact")
            await r.aclose()

            header = raw[0]
            # Ensure all rows have the expected number of columns
            return [row for row in raw[1:] if len(row) == len(header)]

        import asyncio
        rows = asyncio.run(_fetch_edges(limit))

        if not rows:
            typer.secho("Graph appears empty—nothing to visualise.",
                        fg=typer.colors.YELLOW)
            return   # <— graceful exit, no exception

        # ── build PyVis network ────────────────────────────────────────
        net = Network(height="800px", width="100%", bgcolor="#222222",
                      font_color="white", directed=True, notebook=False)

        # NEW: Consistent color mapping for node labels
        PREDEFINED_COLORS = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]
        colour_map: Dict[str, str] = {}
        next_color_idx = 0

        def colour_for(label: str) -> str:
            nonlocal next_color_idx
            if label not in colour_map:
                colour_map[label] = PREDEFINED_COLORS[next_color_idx % len(PREDEFINED_COLORS)]
                next_color_idx += 1
            return colour_map[label]

        # Keep track of nodes already added to avoid duplicates
        added_nodes = set()

        for (
            from_id, to_id, from_label, to_label,
            rel, from_text, to_text, from_degree, to_degree
        ) in rows:
            # Add source node if not already present
            if from_id not in added_nodes:
                net.add_node(
                    from_id,
                    label=from_text[:120],
                    title=f"{from_text}\nLabel: {from_label}\nDegree: {from_degree}",
                    color=colour_for(from_label),
                    shape="dot",
                    # NEW: Size nodes based on their degree
                    size=10 + int(from_degree) * 2
                )
                added_nodes.add(from_id)

            # Add target node if not already present
            if to_id not in added_nodes:
                net.add_node(
                    to_id,
                    label=to_text[:120],
                    title=f"{to_text}\nLabel: {to_label}\nDegree: {to_degree}",
                    color=colour_for(to_label),
                    shape="dot",
                    size=10 + int(to_degree) * 2
                )
                added_nodes.add(to_id)

            # Add the edge connecting them
            net.add_edge(from_id, to_id, label=rel, arrows="to")

        # NEW: Enable interactive filtering UI in the output HTML
        net.show_buttons(filter_=['nodes', 'edges', 'physics'])

        net.set_options("""
        var options = {
          "nodes": {
            "font": { "size": 14, "face": "tahoma" }
          },
          "edges": {
            "font": { "size": 12, "align": "top" },
            "smooth": { "type": "dynamic" }
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -8000,
              "springLength": 250,
              "springConstant": 0.04
            },
            "minVelocity": 0.75
          },
          "interaction": {
            "navigationButtons": true,
            "keyboard": true
          }
        }""")

        net.show(output)
        typer.secho(f"✅  Graph saved to {output}", fg=typer.colors.GREEN)
        typer.echo("Open the file in a browser to explore!")

    except Exception as e:
        typer.secho(f"🔥  A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)





@app.command()
def concepts(
    label: str = typer.Option("Concept", "--label", "-l", help="Node label to list")
):
    """List all Concept (or Metric / Dataset …) nodes currently in FalkorDB."""
    try:
        try:
            import redis.asyncio as redis, asyncio
        except ImportError:
            typer.secho("Install redis-py for this command.", fg=typer.colors.YELLOW)
            raise typer.Exit()

        async def _fetch():
            r = redis.Redis(host=FALKORDB_HOST, port=FALKORDB_PORT, decode_responses=True)
            res = await r.execute_command(
                "GRAPH.QUERY", GRAPH_NAME,
                f"MATCH (n:`{label}`) RETURN n.name, count(n) ORDER BY count(n) DESC",
                "--compact"
            )
            await r.aclose()
            # convert every item to a plain string so _print_table is happy
            return [(str(row[0]), str(row[1])) for row in res[1:] if row]

        rows = asyncio.run(_fetch())
        if not rows:
            typer.secho(f"No nodes with label '{label}' found.", fg=typer.colors.YELLOW)
        else:
            _print_table(rows, f"🗂️  {label.upper()} NODES")

    except Exception as e:
        typer.secho(f"🔥  Error: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)

# ── NEW: list relation labels ────────────────────────────
@app.command()
def relations(
    counts: bool = typer.Option(
        False, "--counts", "-c", help="Show live edge-counts per relation"
    )
) -> None:
    """
    List all relation types defined in the ontology.
    Example:
        python -m app relations           # just the names
        python -m app relations -c        # names + how many edges
    """
    try:
        if not ONTO_PATH.exists():
            typer.secho("Run `python -m app build` first – no ontology found.",
                         fg=typer.colors.RED)
            raise typer.Exit()

        # -------- load ontology & collect labels -------------
        onto_json   = json.loads(ONTO_PATH.read_text())
        rel_labels  = [rel["label"] for rel in onto_json.get("relations", [])]

        if not rel_labels:
            typer.secho("Ontology contains no relations.", fg=typer.colors.YELLOW)
            raise typer.Exit()

        # -------- optional live counts -----------------------
        counts_map: dict[str, int] = {}
        if counts:
            try:
                import redis.asyncio as redis, asyncio
            except ImportError:
                typer.secho("Install redis-py to use --counts.", fg=typer.colors.YELLOW)
                raise typer.Exit()

            async def _get_counts() -> dict[str, int]:
                r   = redis.Redis(host=FALKORDB_HOST, port=FALKORDB_PORT,
                                  decode_responses=True)
                out = {}
                for lbl in rel_labels:
                    q   = f"MATCH ()-[:`{lbl}`]->() RETURN count(*)"
                    res = await r.execute_command("GRAPH.QUERY",
                                                  GRAPH_NAME, q, "--compact")

                    # res[1] holds the first data row; drill down until scalar
                    val = res[1]
                    while isinstance(val, list):
                        val = val[0]
                    out[lbl] = int(val)

                await r.aclose()
                return out
        # -------- pretty print -------------------------------
        rows = [(lbl, str(counts_map.get(lbl, ""))) for lbl in rel_labels]
        _print_table(rows, "🔗  RELATION LABELS")

    except Exception as exc:
        typer.secho(f"🔥  Error: {exc}", fg=typer.colors.RED)
        traceback.print_exception(exc)


if __name__ == "__main__":
    app()