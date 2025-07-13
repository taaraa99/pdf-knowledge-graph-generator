# app/cli_commands/schema.py
import typer
import os
import json
import traceback
from typing import Tuple

from graphrag_sdk import Ontology
from app import config, utils

def schema(counts: bool = typer.Option(False, "--counts", "-c", help="Show live counts.")):
    """Show the ontology (labels, attributes, relations)."""
    try:
        if not os.path.exists(config.ONTOLOGY_FILE):
            typer.secho(f"Ontology file '{config.ONTOLOGY_FILE}' not found.", fg=typer.colors.RED)
            raise typer.Exit()

        with open(config.ONTOLOGY_FILE, "r", encoding="utf-8") as fh:
            ontology = Ontology.from_json(json.load(fh))

        schema_dict = ontology.to_json()
        ent_dicts   = schema_dict.get("entities", [])
        rel_dicts   = schema_dict.get("relations", [])

        node_rows = [(ent["label"], ", ".join(attr["name"] for attr in ent.get("attributes", [])) or "—") for ent in ent_dicts]
        utils.print_table(node_rows, "📦  ENTITY LABELS")

        rel_rows = [(rel["label"], f'{rel["source"]["label"]} → {rel["target"]["label"]}') for rel in rel_dicts]
        utils.print_table(rel_rows, "🔗  RELATIONS")

        if counts:
            try:
                import redis.asyncio as redis
                import asyncio
            except ImportError:
                typer.secho("⚠️  Install redis-py (pip install redis) to use --counts.", fg=typer.colors.YELLOW)
                raise typer.Exit()
            
            async def _count_labels() -> Tuple[dict, dict]:
                r = redis.Redis(host=config.FALKORDB_HOST, port=config.FALKORDB_PORT, decode_responses=True)
                node_ct, edge_ct = {}, {}
                
                # --- FIXED: Correctly parse nested list response ---
                for lbl, _ in node_rows:
                    q = f"MATCH (n:{lbl}) RETURN count(n)"
                    res = await r.execute_command("GRAPH.QUERY", config.GRAPH_NAME, q, "--compact")
                    val = res[1]
                    while isinstance(val, list):
                        val = val[0]
                    node_ct[lbl] = int(val)

                for lbl, _ in rel_rows:
                    q = f"MATCH ()-[:{lbl}]->() RETURN count(*)"
                    res = await r.execute_command("GRAPH.QUERY", config.GRAPH_NAME, q, "--compact")
                    val = res[1]
                    while isinstance(val, list):
                        val = val[0]
                    edge_ct[lbl] = int(val)
                
                await r.close()
                return node_ct, edge_ct

            node_counts, edge_counts = asyncio.run(_count_labels())
            utils.print_table([(k, str(v)) for k, v in node_counts.items()], "📊  NODE COUNTS")
            utils.print_table([(k, str(v)) for k, v in edge_counts.items()], "📊  EDGE COUNTS")

    except Exception as e:
        typer.secho(f"🔥 A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)
