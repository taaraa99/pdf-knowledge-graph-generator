# app/cli_commands/visualize.py
import typer
import random
import traceback
from typing import List, Dict, Any

try:
    from pyvis.network import Network
except ImportError:
    Network = None

from app import config

def visualize(
    output: str = typer.Option(
        "graph.html", "--output", "-o", help="Name of the HTML file to generate."
    ),
    limit: int = typer.Option(
        750, "--limit", "-l", help="Maximum number of edges to pull from the DB."
    ),
):
    """Generate an interactive PyVis HTML visualisation of the current graph."""
    typer.echo("Generating interactive graph visualization...")
    try:
        if Network is None:
            typer.secho("❌ Install pyvis (`pip install pyvis`) to use visualize.", fg=typer.colors.RED)
            raise typer.Exit()

        try:
            import redis.asyncio as redis
            import asyncio
        except ImportError:
            typer.secho("❌ Install redis-py (`pip install redis`) to use visualize.", fg=typer.colors.RED)
            raise typer.Exit()

        async def _fetch_edges(lim: int) -> List[List[Any]]:
            r = redis.Redis(host=config.FALKORDB_HOST, port=config.FALKORDB_PORT, decode_responses=True)
            query = f"""
            MATCH (a)-[r]->(b)
            RETURN id(a) AS from_id, id(b) AS to_id, labels(a)[0] AS from_label,
                   labels(b)[0] AS to_label, type(r) AS rel,
                   coalesce(a.title, a.name, labels(a)[0]) AS from_text,
                   coalesce(b.title, b.name, labels(b)[0]) AS to_text,
                   size((a)--()) AS from_degree, size((b)--()) AS to_degree
            LIMIT {lim}
            """
            raw = await r.execute_command("GRAPH.QUERY", config.GRAPH_NAME, query, "--compact")
            await r.aclose()
            if not raw or len(raw) < 2:
                return []
            header = raw[0]
            return [row for row in raw[1:] if len(row) == len(header)]

        rows = asyncio.run(_fetch_edges(limit))

        if not rows:
            typer.secho("Graph appears empty—nothing to visualise.", fg=typer.colors.YELLOW)
            return

        net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", directed=True)
        
        PREDEFINED_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
        colour_map: Dict[str, str] = {}
        next_color_idx = 0

        def colour_for(label: str) -> str:
            nonlocal next_color_idx
            if label not in colour_map:
                colour_map[label] = PREDEFINED_COLORS[next_color_idx % len(PREDEFINED_COLORS)]
                next_color_idx += 1
            return colour_map[label]

        added_nodes = set()
        for from_id, to_id, from_label, to_label, rel, from_text, to_text, from_degree, to_degree in rows:
            if from_id not in added_nodes:
                net.add_node(from_id, label=from_text[:120], title=f"{from_text}\nLabel: {from_label}\nDegree: {from_degree}", color=colour_for(from_label), shape="dot", size=10 + int(from_degree) * 2)
                added_nodes.add(from_id)
            if to_id not in added_nodes:
                net.add_node(to_id, label=to_text[:120], title=f"{to_text}\nLabel: {to_label}\nDegree: {to_degree}", color=colour_for(to_label), shape="dot", size=10 + int(to_degree) * 2)
                added_nodes.add(to_id)
            net.add_edge(from_id, to_id, label=rel, arrows="to")

        net.show_buttons(filter_=['nodes', 'edges', 'physics'])
        net.set_options("""
        var options = {
          "nodes": { "font": { "size": 14, "face": "tahoma" } },
          "edges": { "font": { "size": 12, "align": "top" }, "smooth": { "type": "dynamic" } },
          "physics": { "barnesHut": { "gravitationalConstant": -8000, "springLength": 250, "springConstant": 0.04 }, "minVelocity": 0.75 },
          "interaction": { "navigationButtons": true, "keyboard": true }
        }""")
        net.show(output)
        typer.secho(f"✅  Graph saved to {output}", fg=typer.colors.GREEN)
        typer.echo("Open the file in a browser to explore!")

    except Exception as e:
        typer.secho(f"🔥  A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)