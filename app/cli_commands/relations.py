# app/cli_commands/relations.py
import typer
import os
import json
import traceback

from app import config, utils

def relations(counts: bool = typer.Option(False, "--counts", "-c", help="Show live edge-counts per relation")):
    """List all relation types defined in the ontology."""
    try:
        if not os.path.exists(config.ONTOLOGY_FILE):
            typer.secho("Run `python -m app build` first – no ontology found.", fg=typer.colors.RED)
            raise typer.Exit()

        onto_json = json.loads(config.ONTO_PATH.read_text())
        rel_labels = [rel["label"] for rel in onto_json.get("relations", [])]

        if not rel_labels:
            typer.secho("Ontology contains no relations.", fg=typer.colors.YELLOW)
            raise typer.Exit()

        counts_map = {}
        if counts:
            try:
                import redis.asyncio as redis
                import asyncio
            except ImportError:
                typer.secho("Install redis-py to use --counts.", fg=typer.colors.YELLOW)
                raise typer.Exit()

            async def _get_counts() -> dict[str, int]:
                r = redis.Redis(host=config.FALKORDB_HOST, port=config.FALKORDB_PORT, decode_responses=True)
                out = {}
                for lbl in rel_labels:
                    q = f"MATCH ()-[:`{lbl}`]->() RETURN count(*)"
                    res = await r.execute_command("GRAPH.QUERY", config.GRAPH_NAME, q, "--compact")
                    val = res[1]
                    while isinstance(val, list):
                        val = val[0]
                    out[lbl] = int(val)
                await r.aclose()
                return out
            
            counts_map = asyncio.run(_get_counts())

        rows = [(lbl, str(counts_map.get(lbl, ""))) for lbl in rel_labels]
        utils.print_table(rows, "🔗  RELATION LABELS")

    except Exception as exc:
        typer.secho(f"🔥  Error: {exc}", fg=typer.colors.RED)
        traceback.print_exception(exc)