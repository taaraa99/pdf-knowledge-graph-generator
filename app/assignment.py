import os
import json
import falkordb
from dotenv import load_dotenv
from litellm import completion
from unstructured.partition.pdf import partition_pdf

# Load API keys from .env file
load_dotenv()

# --- Configuration ---
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6379
INITIAL_PDF_DIR = "data/initial_pdfs"
ADDITIONAL_PDF_DIR = "data/additional_pdfs"

def extract_graph_from_text(text_chunk):
    """Sends text to an LLM and asks it to extract entities and relationships."""
    print("  - Calling LLM to extract graph from text chunk...")
    
    system_prompt = """
    You are an expert at creating knowledge graphs. From the text provided, extract entities and their relationships.
    An entity should have a 'name', a 'type' (e.g., PERSON, ORGANIZATION, TECHNOLOGY), and a 'description'.
    A relationship should have a 'source' entity name, a 'target' entity name, and a 'type' (e.g., DIRECTED, WORKED_ON, INFLUENCED).
    Respond with ONLY a valid JSON object containing two keys: "entities" and "relationships". Do not include any other text or explanations.
    Example: {"entities": [{"name": "Neo", "type": "PERSON", "description": "The protagonist"}], "relationships": []}
    """
    
    try:
        response = completion(
            model="openai/gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_chunk}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"    ERROR: Could not get valid JSON from LLM. Error: {e}")
        return None

def update_falkordb_graph(db, graph_data):
    """Updates the FalkorDB graph with entities and relationships."""
    if not graph_data or "entities" not in graph_data or "relationships" not in graph_data:
        return

    # Use MERGE to create nodes without duplicates
    for entity in graph_data["entities"]:
        db.query("""
            MERGE (n:%s {name: $name})
            ON CREATE SET n.description = $description
        """ % entity['type'].replace(" ", "_"), {  # Sanitize entity type for Cypher
            'name': entity['name'],
            'description': entity.get('description', '')
        })

    # Use MERGE to create relationships without duplicates
    for rel in graph_data["relationships"]:
        db.query("""
            MATCH (a {name: $source})
            MATCH (b {name: $target})
            MERGE (a)-[r:%s]->(b)
        """ % rel['type'].replace(" ", "_"), {  # Sanitize relationship type for Cypher
            'source': rel['source'],
            'target': rel['target']
        })
    print(f"  - Graph updated with {len(graph_data['entities'])} entities and {len(graph_data['relationships'])} relationships.")


def process_files(db, directories):
    """Processes all files in a list of directories, now with chunking."""
    chunk_size = 12000  # characters (approx. 3k tokens, safely below limits)
    chunk_overlap = 500   # characters to maintain context between chunks

    for directory in directories:
        print(f"\n--- Processing directory: {directory} ---")
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                path = os.path.join(directory, filename)
                print(f"Processing file: {filename}")
                try:
                    elements = partition_pdf(filename=path, strategy="fast")
                    full_text = "\n".join([el.text for el in elements])

                    if not full_text.strip():
                        print("  - No text found in file.")
                        continue

                    # Loop through the text in chunks
                    print(f"  - Splitting text into chunks...")
                    for i in range(0, len(full_text), chunk_size - chunk_overlap):
                        chunk = full_text[i:i + chunk_size]
                        print(f"    - Processing chunk {i//(chunk_size - chunk_overlap) + 1}...")
                        
                        graph_data = extract_graph_from_text(chunk)
                        if graph_data:
                            update_falkordb_graph(db, graph_data)
                    
                except Exception as e:
                    print(f"    Could not process file {filename}. Error: {e}")


if __name__ == "__main__":
    # --- Database Connection ---
    print("Connecting to FalkorDB...")
    r = falkordb.FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    db = r.select_graph("assignment_kg")
    print("Connection successful.")

    # Stage 1: Ingest the first 5 PDF files
    process_files(db, [INITIAL_PDF_DIR])

    # Stage 2: Evolve the graph with the additional 5 PDF files
    process_files(db, [ADDITIONAL_PDF_DIR])

    print("\n--- Assignment complete! ---")