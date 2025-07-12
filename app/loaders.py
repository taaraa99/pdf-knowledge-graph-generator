# app/loaders.py
import os
import typer
from typing import List, Iterator

from graphrag_sdk.document import Document

class UnstructuredPDFLoader:
    """A standalone loader that uses unstructured.io to process a directory of PDFs."""
    def __init__(self):
        try:
            from unstructured.partition.auto import partition
        except ImportError:
            raise ImportError(
                "unstructured[pdf] package not found. Please install it with `pip install 'unstructured[pdf]'`"
            )
        self._partition = partition

    def load(self, directory_path: str) -> List[Document]:
        """
        Loads all PDFs from a directory and returns a list of Document objects.
        
        Args:
            directory_path (str): The path to the directory containing PDFs.
        
        Returns:
            List[Document]: A list of Document objects, one for each PDF.
        """
        documents = []
        typer.echo(f"Loading PDFs from '{directory_path}' using Unstructured.io...")
        for f in os.listdir(directory_path):
            if f.endswith(".pdf"):
                path = os.path.join(directory_path, f)
                typer.secho(f"  -> Processing: {f}", fg=typer.colors.CYAN)
                elements = self._partition(filename=path)
                full_text = "\n\n".join([str(el) for el in elements])
                documents.append(Document(full_text, id=path))
        return documents