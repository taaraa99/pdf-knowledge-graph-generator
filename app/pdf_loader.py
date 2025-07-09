from unstructured.partition.pdf import partition_pdf

def load_pdfs(file_paths):
    """
    Loads and extracts text from a list of PDF files using Unstructured-IO.
    """
    all_elements = []
    for path in file_paths:
        try:
            elements = partition_pdf(filename=path)
            all_elements.extend(elements)
        except Exception as e:
            print(f"Error processing {path}: {e}")
    return all_elements