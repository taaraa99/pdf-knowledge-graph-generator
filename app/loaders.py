
# app/loaders.py
import os
import typer
from typing import Iterator, List

# We only need Document from the SDK here
from graphrag_sdk.document import Document

# This class does NOT inherit from graphrag_sdk.Source to avoid metaclass conflicts.
# It uses duck typing to behave like a Source object.
class UnstructuredPDFLoader:
    """A custom loader that uses unstructured.io to process a PDF."""
    def __init__(self, path: str):
        """
        Initializes the loader with the path to the PDF.
        Args:
            path (str): The path to the PDF file.
        """
        # Mimic the attributes of the SDK's Source class.
        self.source_id = path
        self.instruction = None

        try:
            from unstructured.partition.auto import partition
        except ImportError:
            raise ImportError(
                "unstructured[pdf] package not found. Please install it with `pip install 'unstructured[pdf]'`"
            )
        self._partition = partition

    def load(self) -> Iterator[Document]:
        """
        Loads and partitions the PDF using unstructured's auto-partitioner,
        yielding a single Document.
        
        Returns:
            Iterator[Document]: An iterator containing one Document object with the full text.
        """
        typer.secho(f"  -> Loading PDF with Unstructured.io: {os.path.basename(self.source_id)}", fg=typer.colors.CYAN)
        elements = self._partition(filename=self.source_id)
        full_text = "\n\n".join([str(el) for el in elements])
        yield Document(full_text, id=self.source_id)

