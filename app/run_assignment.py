# run_assignment.py
from dotenv import load_dotenv
from database_manager import DatabaseManager
from graph_builder import GraphBuilder
from ingestion_pipeline import IngestionPipeline

# Load API key from .env file
load_dotenv()

# --- Configuration ---
INITIAL_PDF_DIR = "data/initial_pdfs"
ADDITIONAL_PDF_DIR = "data/additional_pdfs"
GRAPH_NAME = "assignment_kg"

def main():
    """Main function to run the knowledge graph generation pipeline."""
    try:
        # --- Initialization ---
        db_manager = DatabaseManager()
        graph_builder = GraphBuilder()
        pipeline = IngestionPipeline(graph_builder, db_manager)
        db_instance = db_manager.select_graph(GRAPH_NAME)

        # --- Pipeline Execution ---
        # Stage 1: Ingest the first 5 PDF files
        pipeline.process_directory(db_instance, INITIAL_PDF_DIR)

        # Stage 2: Evolve the graph with the additional 5 PDF files
        pipeline.process_directory(db_instance, ADDITIONAL_PDF_DIR)

        print("\n--- Assignment complete! ---")

    except Exception as e:
        print(f"\n--- A critical error occurred: {e} ---")

if __name__ == "__main__":
    main()