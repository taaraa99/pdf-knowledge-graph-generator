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
        "graph.html", "--output", "-o", help="Name of the output HTML file."
    ),
    limit: int = typer.Option(
        1000, "--limit", "-l", help="Maximum number of nodes to pull from the DB."
    ),
):
    """Generate an interactive PyVis HTML visualisation of the current graph."""
    typer.echo("Generating interactive graph visualization...")
    try:
        if Network is None:
            typer.secho("❌ Install pyvis (`pip install pyvis`) to use this command.", fg=typer.colors.RED)
            raise typer.Exit()

        try:
            import redis.asyncio as redis
            import asyncio
        except ImportError:
            typer.secho("❌ Install redis-py (`pip install redis`) to use this command.", fg=typer.colors.RED)
            raise typer.Exit()

        def _parse_compact_response(raw_response: list) -> list:
            """
            Parses the complex, nested list structure from a --compact FalkorDB query.
            The expected format is [ header, [data_rows], metadata ].
            """
            if not raw_response or len(raw_response) < 2:
                return []
            
            header = [h[1] for h in raw_response[0]]
            data_section = raw_response[1]

            if not isinstance(data_section, list):
                return []

            data_rows = []
            for nested_row in data_section:
                if not isinstance(nested_row, list):
                    continue
                
                flat_row = [item[1] if isinstance(item, list) and len(item) > 1 else item for item in nested_row]
                
                if len(flat_row) == len(header):
                    data_rows.append(flat_row)
            return data_rows

        async def _fetch_graph_data(lim: int) -> tuple[list, list]:
            """Fetches all nodes and edges from the graph separately."""
            r = redis.Redis(host=config.FALKORDB_HOST, port=config.FALKORDB_PORT, decode_responses=True)
            
            nodes_query = f"""
            MATCH (n)
            RETURN id(n) AS node_id, labels(n)[0] AS label,
                   coalesce(n.title, n.name, 'Node ' + id(n)) AS display_text,
                   size((n)--()) AS degree
            LIMIT {lim}
            """
            nodes_raw = await r.execute_command("GRAPH.QUERY", config.GRAPH_NAME, nodes_query, "--compact")
            
            edges_query = f"""
            MATCH (a)-[r]->(b)
            RETURN id(a) AS from_id, id(b) AS to_id, type(r) AS rel_type
            LIMIT {lim}
            """
            edges_raw = await r.execute_command("GRAPH.QUERY", config.GRAPH_NAME, edges_query, "--compact")

            await r.aclose()
            
            return _parse_compact_response(nodes_raw), _parse_compact_response(edges_raw)

        nodes, edges = asyncio.run(_fetch_graph_data(limit))

        if not nodes:
            typer.secho("Graph appears empty—nothing to visualise.", fg=typer.colors.YELLOW)
            return

        net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", directed=True, notebook=False)
        
        PREDEFINED_COLORS = ["#5E81AC", "#81A1C1", "#88C0D0", "#8FBCBB", "#A3BE8C", "#B48EAD", "#BF616A", "#D08770", "#EBCB8B", "#D8DEE9"]
        colour_map: Dict[str, str] = {}
        next_color_idx = 0

        def colour_for(label: str) -> str:
            nonlocal next_color_idx
            if not label: return "#4C566A"
            if label not in colour_map:
                colour_map[label] = PREDEFINED_COLORS[next_color_idx % len(PREDEFINED_COLORS)]
                next_color_idx += 1
            return colour_map.get(label, "#4C566A")

        for node_id, label, display_text, degree in nodes:
            net.add_node(node_id, label=str(display_text)[:120], title=f"{display_text}\nLabel: {label}\nDegree: {degree}", color=colour_for(label), shape="dot", size=10 + int(degree) * 2)

        for from_id, to_id, rel_type in edges:
            net.add_edge(from_id, to_id, label=str(rel_type), arrows="to")

        net.show_buttons(filter_=['nodes', 'edges', 'physics'])
        net.set_options("""
        var options = {
          "nodes": { "font": { "size": 14, "face": "tahoma" } },
          "edges": { "font": { "size": 12, "align": "top" }, "smooth": { "type": "dynamic" } },
          "physics": { "barnesHut": { "gravitationalConstant": -8000, "springLength": 250, "springConstant": 0.04 }, "minVelocity": 0.75 },
          "interaction": { "navigationButtons": true, "keyboard": true }
        }""")
        
        # --- FINAL FIX: Use write_html() for more reliable file generation in Docker ---
        net.write_html(output)
        
        typer.secho(f"✅  Graph saved to {output}", fg=typer.colors.GREEN)
        typer.echo("Open the file in a browser to explore!")

    except Exception as e:
        typer.secho(f"🔥  A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)
