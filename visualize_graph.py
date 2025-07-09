# visualize_graph.py
import falkordb
import networkx as nx
import matplotlib.pyplot as plt

# Connect to the database
r = falkordb.FalkorDB(host="localhost", port=6379)
db = r.select_graph("assignment_kg")

# Query a small, connected part of the graph
query = """
MATCH (n)-[r]->(m)
WHERE n.name CONTAINS 'Transformer' OR m.name CONTAINS 'Transformer'
RETURN n, r, m
LIMIT 15
"""
result = db.query(query)

# Create a NetworkX directed graph
G = nx.DiGraph()

edge_labels = {}

# Add nodes and edges from the query result
for record in result.result_set:
    source_node = record[0]
    relationship = record[1]
    target_node = record[2]

    source_name = source_node.properties['name']
    target_name = target_node.properties['name']

    # Add nodes with their labels as attributes
    G.add_node(source_name, label=source_node.labels[0])
    G.add_node(target_name, label=target_node.labels[0])

    # Add the edge and store its label
    G.add_edge(source_name, target_name)
    edge_labels[(source_name, target_name)] = relationship.relation

# Visualize the graph if it's not empty
if not G.nodes:
    print("No data found in the graph for this query.")
else:
    plt.figure(figsize=(20, 16))
    pos = nx.spring_layout(G, k=0.8, iterations=50) # Use a layout to spread nodes

    # Draw the graph
    nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=2500,
            font_size=10, font_weight='bold', width=1.5, arrowsize=20)

    # Draw the edge labels
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', font_size=9)

    plt.title("Knowledge Graph of Transformer Technologies", size=20)
    plt.savefig("knowledge_graph.png", format="PNG")
    print("Graph visualization saved to knowledge_graph.png")