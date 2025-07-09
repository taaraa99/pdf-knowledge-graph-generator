# app/ingestion_pipeline.py
import os
from unstructured.partition.pdf import partition_pdf

class IngestionPipeline:
    """Orchestrates the process of reading files and building the graph."""
    def __init__(self, graph_builder, db_manager):
        self.graph_builder = graph_builder
        self.db_manager = db_manager
        self.chunk_size = 12000
        self.chunk_overlap = 500

    def process_directory(self, db_instance, directory_path):
        """Processes all PDF files in a given directory."""
        print(f"\n--- Processing directory: {directory_path} ---")
        for filename in os.listdir(directory_path):
            if filename.endswith(".pdf"):
                path = os.path.join(directory_path, filename)
                print(f"Processing file: {filename}")
                try:
                    elements = partition_pdf(filename=path, strategy="hi_res")
                    full_text = "\n".join([el.text for el in elements])

                    if not full_text.strip():
                        print("  - No text found in file.")
                        continue
                    
                    print(f"  - Splitting text into chunks...")
                    for i in range(0, len(full_text), self.chunk_size - self.chunk_overlap):
                        chunk = full_text[i:i + self.chunk_size]
                        print(f"    - Processing chunk {i//(self.chunk_size - self.chunk_overlap) + 1}...")
                        
                        graph_data = self.graph_builder.extract_graph_from_chunk(chunk)
                        if graph_data:
                            self.db_manager.update_graph(db_instance, graph_data)

                except Exception as e:
                    print(f"    Could not process file {filename}. Error: {e}")