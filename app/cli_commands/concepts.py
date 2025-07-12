# app/cli_commands/concepts.py
import typer
import traceback

from app import config, utils

def concepts(label: str = typer.Option("Concept", "--label", "-l", help="Node label to list")):
    """List all Concept (or Metric / Dataset …) nodes currently in FalkorDB."""
    try:
        try:
            import redis.asyncio as redis
            import asyncio
        except ImportError:
            typer.secho("Install redis-py for this command.", fg=typer.colors.YELLOW)
            raise typer.Exit()

        async def _fetch():
            r = redis.Redis(host=config.FALKORDB_HOST, port=config.FALKORDB_PORT, decode_responses=True)
            res = await r.execute_command(
                "GRAPH.QUERY", config.GRAPH_NAME,
                f"MATCH (n:`{label}`) RETURN n.name, count(n) ORDER BY count(n) DESC",
                "--compact"
            )
            await r.aclose()
            return [(str(row[0]), str(row[1])) for row in res[1:] if row]

        rows = asyncio.run(_fetch())
        if not rows:
            typer.secho(f"No nodes with label '{label}' found.", fg=typer.colors.YELLOW)
        else:
            utils.print_table(rows, f"🗂️  {label.upper()} NODES")

    except Exception as e:
        typer.secho(f"🔥  Error: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)