# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Directory and File Paths
INITIAL_PDF_DIR = "data/initial_pdfs"
ADDITIONAL_PDF_DIR = "data/additional_pdfs"
ONTOLOGY_FILE = "ontology.json"
ONTO_PATH = Path(ONTOLOGY_FILE)

# Graph and Database Configuration
GRAPH_NAME = "assignment_kg"
FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", 6379))

# LLM Configuration
DEFAULT_MODEL_NAME = "openai/gpt-4o"