# app/database_manager.py
import falkordb

class DatabaseManager:
    """Handles all interactions with the FalkorDB database."""
    def __init__(self, host="localhost", port=6379):
        try:
            self.r = falkordb.FalkorDB(host=host, port=port)
            print("Successfully connected to FalkorDB.")
        except Exception as e:
            print(f"Error connecting to FalkorDB: {e}")
            raise

    def select_graph(self, graph_name):
        return self.r.select_graph(graph_name)

    def update_graph(self, db_instance, graph_data):
        """Updates the graph with new entities and relationships."""
        if not graph_data or "entities" not in graph_data or "relationships" not in graph_data:
            return 0
        
        # Use MERGE to create nodes without duplicates
        for entity in graph_data["entities"]:
            db_instance.query("""
                MERGE (n:%s {name: $name})
                ON CREATE SET n.description = $description
            """ % entity['type'].replace(" ", "_"), {
                'name': entity['name'],
                'description': entity.get('description', '')
            })

        # Use MERGE to create relationships without duplicates
        for rel in graph_data["relationships"]:
            db_instance.query("""
                MATCH (a {name: $source})
                MATCH (b {name: $target})
                MERGE (a)-[r:%s]->(b)
            """ % rel['type'].replace(" ", "_"), {
                'source': rel['source'],
                'target': rel['target']
            })
        
        update_count = len(graph_data['entities']) + len(graph_data['relationships'])
        print(f"  - Graph updated with {len(graph_data['entities'])} entities and {len(graph_data['relationships'])} relationships.")
        return update_count