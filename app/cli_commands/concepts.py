# app/cli_commands/concepts.py
import typer
import traceback

from app import config, utils

def concepts(label: str = typer.Option("Concept", "--label", "-l", help="Node label to list")):
    """List all nodes of a given label, like Concept, Paper, or Person."""
    try:
        try:
            import redis.asyncio as redis
            import asyncio
        except ImportError:
            typer.secho("Install redis-py for this command.", fg=typer.colors.YELLOW)
            raise typer.Exit()

        async def _fetch():
            r = redis.Redis(host=config.FALKORDB_HOST, port=config.FALKORDB_PORT, decode_responses=True)
            
            # CORRECTED QUERY: Use coalesce to handle different name properties (name vs title)
            # and properly group by the name to get counts.
            query = f"""
            MATCH (n:{label})
            WITH coalesce(n.title, n.name) AS name
            WHERE name IS NOT NULL
            RETURN name, count(name) AS occurrences
            ORDER BY occurrences DESC
            """
            res = await r.execute_command(
                "GRAPH.QUERY", config.GRAPH_NAME,
                query,
                "--compact"
            )
            await r.aclose()
            
            # The response has a header row, so we skip it (res[1:])
            # Each row should now correctly have two items.
            return [(str(row[0]), str(row[1])) for row in res[1:] if row and len(row) == 2]

        rows = asyncio.run(_fetch())
        if not rows:
            typer.secho(f"No nodes with label '{label}' found, or they have no 'name' or 'title' property.", fg=typer.colors.YELLOW)
        else:
            utils.print_table(rows, f"🗂️  {label.upper()} NODES")

    except Exception as e:
        typer.secho(f"🔥  Error: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)
