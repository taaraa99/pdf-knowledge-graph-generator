# # # app/loaders.py
# # import os
# # import typer
# # from typing import List, Iterator

# # from graphrag_sdk.document import Document

# # class UnstructuredPDFLoader:
# #     """A standalone loader that uses unstructured.io to process a directory of PDFs."""
# #     def __init__(self):
# #         try:
# #             from unstructured.partition.auto import partition
# #         except ImportError:
# #             raise ImportError(
# #                 "unstructured[pdf] package not found. Please install it with `pip install 'unstructured[pdf]'`"
# #             )
# #         self._partition = partition

# #     def load(self, directory_path: str) -> List[Document]:
# #         """
# #         Loads all PDFs from a directory and returns a list of Document objects.
        
# #         Args:
# #             directory_path (str): The path to the directory containing PDFs.
        
# #         Returns:
# #             List[Document]: A list of Document objects, one for each PDF.
# #         """
# #         documents = []
# #         typer.echo(f"Loading PDFs from '{directory_path}' using Unstructured.io...")
# #         for f in os.listdir(directory_path):
# #             if f.endswith(".pdf"):
# #                 path = os.path.join(directory_path, f)
# #                 typer.secho(f"  -> Processing: {f}", fg=typer.colors.CYAN)
# #                 elements = self._partition(filename=path)
# #                 full_text = "\n\n".join([str(el) for el in elements])
# #                 documents.append(Document(full_text, id=path))
# #         return documents


# # app/loaders.py
# import os
# import typer
# from typing import Iterator

# from graphrag_sdk import Source
# from graphrag_sdk.document import Document

# # This class fulfills the assignment requirement by subclassing and overriding.
# class UnstructuredSource(Source):
#     """A custom Source that uses the unstructured.io library to process PDFs."""

#     # No __init__ override is needed. The parent's __init__ handles everything.
#     # The `source_id` will be set automatically by the parent class.

#     def load(self) -> Iterator[Document]:
#         """
#         Overrides the default loader. Loads and partitions the PDF using 
#         unstructured's auto-partitioner, yielding a single Document.
        
#         Returns:
#             Iterator[Document]: An iterator containing one Document object with the full text.
#         """
#         try:
#             from unstructured.partition.auto import partition
#         except ImportError:
#             raise ImportError(
#                 "unstructured[pdf] package not found. Please install it with `pip install 'unstructured[pdf]'`"
#             )
        
#         typer.secho(f"  -> Loading PDF with Unstructured.io: {os.path.basename(self.source_id)}", fg=typer.colors.CYAN)
#         elements = partition(filename=self.source_id)
#         full_text = "\n\n".join([str(el) for el in elements])
#         yield Document(full_text, id=self.source_id)


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
        self.instruction = None # <-- FIXED: Add the missing 'instruction' attribute.

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

