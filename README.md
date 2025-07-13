# PDF Knowledge Graph Generator

## Project Overview

This project is a command-line interface (CLI) application that builds, evolves, and queries a knowledge graph from a collection of PDF documents. It leverages the **GraphRAG-SDK** to extract structured information from unstructured text, stores it in a **FalkorDB** graph database, and allows users to interact with the generated knowledge through natural language questions, schema exploration, and interactive visualizations.

The entire solution is containerized with **Docker**, ensuring a reproducible and easy-to-deploy environment that meets the assignment's requirements for a production-grade service.

## Features

* **Flexible Model Selection**: Choose your LLM provider (OpenAI, Google, Azure, Ollama) directly from the command line.
* **Knowledge Graph Construction**: Ingests an initial set of PDFs to build a baseline knowledge graph.
* **Graph Evolution**: Seamlessly evolves the graph by processing additional documents, enriching the existing knowledge base.
* **Natural Language Q&A**: Ask questions in plain English and receive answers synthesized from the graph's context.
* **Interactive Visualization**: Generates a dynamic, interactive HTML file to visually explore the nodes and relationships in the graph.
* **Schema Inspection**: Provides commands to view the graph's ontology (entity types, relationships) and live instance counts.
* **Containerized Deployment**: Fully containerized with Docker and Docker Compose for easy setup and consistent execution.
* **Tested**: Includes a `pytest` suite to ensure the reliability and correctness of the application's logic.

## Technology Choices

This project was built with a selection of modern, robust tools chosen specifically for their suitability to the task.

| Tool / Library      | Purpose                               | Why it was chosen                                                                                                                                                                                          |
| ------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Python 3.11** | Core Programming Language             | A modern, stable version of Python with excellent support for data science, ML, and asynchronous programming.                                                                                              |
| **Typer** | Command-Line Interface (CLI)          | Provides a simple, elegant way to build powerful and user-friendly CLIs with automatic help generation and type validation. It makes the application easy to use and extend.                               |
| **GraphRAG-SDK** | Knowledge Graph Framework             | The core engine for this project. It abstracts away the complexity of LLM-based entity and relationship extraction, providing a high-level API to build knowledge graphs from source documents.                |
| **Unstructured.io** | PDF Processing                        | A powerful library for parsing complex file types. The assignment explicitly required its integration. It was used via a custom `UnstructuredPDFLoader` to perform deep layout analysis on the PDFs, identifying semantic elements like titles, paragraphs, and lists. This provides cleaner, more contextually-aware text to the LLM, resulting in a higher quality knowledge graph compared to simple text extraction methods. |
| **LiteLLM** | LLM Abstraction Layer                 | Allows the application to connect to various LLM providers (OpenAI, Google, Azure, Ollama) through a unified interface, making it easy to switch models without changing the core code.                                |
| **FalkorDB** | Graph Database                        | A high-performance, Redis-based graph database designed for real-time queries. Its compatibility with the Cypher query language and Python client make it an excellent choice for storing the knowledge graph. |
| **PyVis** | Graph Visualization                   | Creates beautiful, interactive HTML visualizations of the graph directly from Python, enabling easy exploration of the complex relationships discovered in the data.                                         |
| **Docker & Compose**| Containerization                      | The industry standard for creating portable, scalable, and isolated application environments. Docker ensures that the application and its dependencies run the same way everywhere, fulfilling a key assignment requirement. |
| **Pytest** | Testing Framework                     | A powerful and easy-to-use testing framework for Python. Using `pytest` demonstrates a commitment to code quality and robustness, another key requirement of the assignment.                               |

## Folder Structure

The project is organized into a clean and logical directory structure.

```
.
├── app/
│   ├── __main__.py
│   ├── commands.py
│   ├── config.py
│   ├── loaders.py
│   ├── utils.py
│   └── cli_commands/
│       ├── __init__.py
│       └── (command files...)
├── data/
│   ├── initial_pdfs/
│   └── additional_pdfs/
├── tests/
│   └── test_main.py
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── ontology.json
└── requirements.txt
```

## Data Pipeline

The application follows a clear, multi-stage pipeline to transform raw PDFs into a queryable knowledge graph.

1.  **PDF Pre-processing with a Custom Loader (`build` command)**:
    * The pipeline begins by using a custom `UnstructuredPDFLoader` class. This was created to explicitly integrate the `unstructured-io` library as required by the assignment, extending the framework's capabilities.
    * For each PDF, this loader calls the `unstructured.partition` function. This function performs deep document analysis, going beyond simple text extraction to identify document elements like titles, paragraphs, and lists.
    * This step produces a list of clean `Document` objects, which are then fed into the GraphRAG-SDK for ontology creation and ingestion.
2.  **Ontology Creation (`build` command)**:
    * The extracted text from the initial 5 PDFs is passed to the `GraphRAG-SDK`.
    * Using an LLM, the SDK analyzes this text to discover a suitable ontology (the schema of entities and relationships).
    * If an `ontology.json` file already exists, it merges the newly discovered schema with the existing one. Otherwise, it saves the new ontology.
3.  **Initial Graph Ingestion (`build` command)**:
    * Using the generated ontology, the application creates a `KnowledgeGraph` instance connected to FalkorDB.
    * It then re-processes the text from the initial 5 PDFs, this time extracting specific entities and relationships based on the ontology and ingesting them into the database.
4.  **Graph Evolution (`build` command)**:
    * The application then processes the text from all 10 PDFs (from both `initial_pdfs` and `additional_pdfs`), again using the custom `UnstructuredPDFLoader`.
    * The `KnowledgeGraph` instance intelligently updates the graph, adding new entities and relationships and strengthening connections based on the new information.
5.  **Querying and Interaction (`ask`, etc.)**:
    * Once the graph is built, users can use the other CLI commands to interact with it.
    * The `ask` command sends a natural language question to the `KnowledgeGraph`, which retrieves relevant context from the database, synthesizes an answer with an LLM, and returns it to the user.
    <!-- * The `visualize` command queries the graph directly using Cypher, fetches a sample of nodes and edges, and builds an interactive HTML file with PyVis. -->

## Setup and Usage

### Step 1: Configure Credentials for Your LLM

Before running the application, you must configure your credentials for the desired LLM provider.

1.  Copy the `.env.example` file to a new file named `.env`.
2.  Open the `.env` file and fill in the required API keys and settings for the provider you intend to use.

#### **OpenAI**
* **Required Variable:** `OPENAI_API_KEY`
* **Example Model String:** `openai/gpt-4o`

#### **Gemini**
* **Required Variable:** `Gemini_API_KEY`
* **Example Model String:** `gemini/gemini-2.0-flash`

#### **Azure OpenAI**
* **Required Variables:** `AZURE_API_KEY`, `AZURE_API_BASE`, `AZURE_API_VERSION`
* **Example Model String:** `azure/your-deployment-name`

#### **Ollama**
* **Required Variables:** None for local instances. `OLLAMA_API_BASE` for remote servers.
* **Note:** Ollama models are best suited for the Q&A step after the graph has been built with a more powerful model.
* **Example Model String:** `ollama/llama3`

### Step 2: Choose a Running Method

#### Option A: Running Locally with a Virtual Environment

1.  **Clone the Repository:**
    ```bash
    git clone git@github.com:taaraa99/pdf-knowledge-graph-generator.git
    cd pdf-knowledge-graph-generator
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Start FalkorDB (using Docker):**
    ```bash
    docker run -d -p 6379:6379 -v falkordb_data:/data falkordb/falkordb:latest
    ```

5.  **Add PDFs:** Place your PDF files in the `data/initial_pdfs` and `data/additional_pdfs` directories.

6.  **Run Commands:** See the **CLI Command Reference** section below for a full list of commands and examples.

#### Option B: Running with Docker (Recommended)

1.  **Add PDFs:** Place your PDF files in the `data/initial_pdfs` and `data/additional_pdfs` directories.

2.  **Build and Start Services:**
    ```bash
    docker-compose up --build -d
    ```

3.  **Run Commands:** Use `docker-compose exec app` before each command. See the **CLI Command Reference** section for examples.
    * **Build:** `docker-compose exec app python -m app build --model "openai/gpt-4o"`
    * **Ask:** `docker-compose exec app python -m app ask "Your question here" --model "gemini/gemini-2.0-flash"`
    <!-- * **Visualize:** `docker-compose exec app python -m app visualize` -->

4.  **Stop Services:**
    When you are finished, stop and remove the containers.
    ```bash
    docker-compose down -v
    ```

## CLI Command Reference

All commands are run from your terminal. Use `python -m app <command>` for local execution or `docker-compose exec app python -m app <command>` for Docker execution.

### `build`
This is the main command to construct and evolve the knowledge graph. It performs the entire data pipeline: loading PDFs with `unstructured-io`, discovering the ontology, ingesting the initial documents, and then evolving the graph with additional documents.

* **Usage:**
    ```bash
    python -m app build
    ```
* **Options:**
    * `--model <model_string>`: Specify which LLM to use for processing.
        ```bash
        python -m app build --model "openai/gpt-4o"
        ```

### `ask`
Allows you to ask a natural language question about the content of your documents. The application uses the knowledge graph to find relevant context and generates a synthesized answer.

* **Usage:**
    ```bash
    python -m app ask "What is the relationship between BERT and Transformers?"
    ```
* **Options:**
    * `--model <model_string>`: Specify which LLM to use for answering the question. This is useful for testing smaller, faster models like Ollama for the Q&A step.
        ```bash
        python -m app ask "Summarize the paper on Word2Vec" --model "ollama/llama3"
        ```

<!-- ### `visualize`
Generates an interactive HTML file that allows you to visually explore the nodes and relationships in your graph. This is excellent for understanding the overall structure of the extracted knowledge.

* **Usage:**
    ```bash
    python -m app visualize
    ```
    This creates `graph.html` in your project root.
* **Options:**
    * `--output <filename>`: Specify a different name for the output file.
    * `--limit <number>`: Control the maximum number of graph edges to include in the visualization. -->

### `schema`
Displays the high-level structure (ontology) of your graph. It lists all the entity types (e.g., `Person`, `Paper`, `Concept`) and the relationship types that connect them. This is useful for seeing what kind of information you can query.

* **Usage:**
    ```bash
    python -m app schema
    ```
* **Options:**
    * `--counts` or `-c`: Queries the database to show the live number of nodes and edges for each type.

### `relations`
Provides a focused list of all the relationship types (e.g., `AUTHORED_BY`, `CITES`, `TOPIC_OF`) that have been defined in your ontology.

* **Usage:**
    ```bash
    python -m app relations
    ```
<!-- * **Options:**
    * `--counts` or `-c`: Shows how many instances of each relationship exist in the graph. -->

<!-- ### `concepts`
Lists all the individual nodes of a specific type that have been extracted into the graph. This is useful for finding specific entities to ask questions about.

* **Usage:**
    ```bash
    # List all 'Concept' nodes
    python -m app concepts

    # List all 'Person' nodes
    python -m app concepts --label Person
    ``` -->

## Testing

The project includes a test suite using `pytest`. The tests use mocking to isolate the application from external services, ensuring fast and reliable execution.

To run the tests, make sure you have set up the local environment and installed the dependencies, then run:
```bash
pytest
