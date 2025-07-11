# PDF Knowledge Graph Generator

## Project Overview

This project is a command-line interface (CLI) application that builds, evolves, and queries a knowledge graph from a collection of PDF documents. It leverages the **GraphRAG-SDK** to extract structured information from unstructured text, stores it in a **FalkorDB** graph database, and allows users to interact with the generated knowledge through natural language questions, schema exploration, and interactive visualizations.

The entire solution is containerized with **Docker**, ensuring a reproducible and easy-to-deploy environment that meets the assignment's requirements for a production-grade service.

## Features

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
| **Unstructured.io** | PDF Processing                        | A powerful library for parsing complex file types like PDFs. It's used under the hood by the GraphRAG-SDK's `Source` class to extract clean text from the documents.                                          |
| **LiteLLM** | LLM Abstraction Layer                 | Allows the application to connect to various LLM providers (like OpenAI's GPT-4o) through a unified interface, making it easy to switch models without changing the core code.                                |
| **FalkorDB** | Graph Database                        | A high-performance, Redis-based graph database designed for real-time queries. Its compatibility with the Cypher query language and Python client make it an excellent choice for storing the knowledge graph. |
| **PyVis** | Graph Visualization                   | Creates beautiful, interactive HTML visualizations of the graph directly from Python, enabling easy exploration of the complex relationships discovered in the data.                                         |
| **Docker & Compose**| Containerization                      | The industry standard for creating portable, scalable, and isolated application environments. Docker ensures that the application and its dependencies run the same way everywhere, fulfilling a key assignment requirement. |
| **Pytest** | Testing Framework                     | A powerful and easy-to-use testing framework for Python. Using `pytest` demonstrates a commitment to code quality and robustness, another key requirement of the assignment.                               |

## Folder Structure

The project is organized into a clean and logical directory structure.

```
.
├── app/
│   └── __main__.py         # The main application script containing all CLI commands.
├── data/
│   ├── initial_pdfs/       # Folder for the first 5 PDFs to be ingested.
│   └── additional_pdfs/    # Folder for the next 5 PDFs to evolve the graph.
├── tests/
│   └── test_main.py        # Pytest test suite for the application.
├── .env                    # Stores secret API keys (ignored by Git).
├── .gitignore              # Specifies files and folders to be ignored by Git.
├── docker-compose.yml      # Defines and configures the multi-container Docker application.
├── Dockerfile              # Instructions for building the application's Docker image.
├── ontology.json           # Stores the discovered graph schema (auto-generated).
└── requirements.txt        # Lists all Python dependencies for the project.
```

## Data Pipeline

The application follows a clear, multi-stage pipeline to transform raw PDFs into a queryable knowledge graph.

1.  **Ontology Creation (`build` command)**:
    * The application first processes the 5 PDFs in the `data/initial_pdfs` directory.
    * Using the `GraphRAG-SDK` and an LLM, it discovers a suitable ontology (the schema of entities and relationships) from the text.
    * If an `ontology.json` file already exists, it merges the newly discovered schema with the existing one. Otherwise, it saves the new ontology.
2.  **Initial Graph Ingestion (`build` command)**:
    * Using the generated ontology, it creates an instance of the `KnowledgeGraph` connected to FalkorDB.
    * It then processes the same 5 initial PDFs again, this time extracting entities and relationships and ingesting them into the database.
3.  **Graph Evolution (`build` command)**:
    * The application then processes *all 10* PDFs (from both `initial_pdfs` and `additional_pdfs`).
    * The `KnowledgeGraph` instance intelligently updates the graph, adding new entities and relationships and strengthening connections based on the new information.
4.  **Querying and Interaction (`ask`, `visualize`, etc.)**:
    * Once the graph is built, users can use the other CLI commands to interact with it.
    * The `ask` command sends a natural language question to the `KnowledgeGraph`, which retrieves relevant context from the database, synthesizes an answer with an LLM, and returns it to the user.
    * The `visualize` command queries the graph directly using Cypher, fetches a sample of nodes and edges, and builds an interactive HTML file with PyVis.

## Setup and Usage

You can run the application in two ways.

### Option 1: Running Locally with a Virtual Environment

This method is ideal for development and for running the application without Docker.

#### 1. Prerequisites

* Python 3.10+
* An OpenAI API Key

#### 2. Setup Steps

1.  **Clone the Repository:**
    ```bash
    git clone git@github.com:taaraa99/pdf-knowledge-graph-generator.git
    cd pdf-knowledge-graph-generator
    ```

2.  **Create and Activate the Virtual Environment:**
    A virtual environment ensures that the project's dependencies are isolated from your global Python installation.
    ```bash
    # Create the virtual environment folder named 'venv'
    python -m venv venv

    # Activate it (the command differs by operating system)
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
    You will see `(venv)` at the beginning of your terminal prompt once it's active.

3.  **Install Dependencies into the Virtual Environment:**
    This command reads the `requirements.txt` file and installs all the necessary Python packages inside your active virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create the Environment Variable File:**
    The application requires your OpenAI API key. The easiest way to manage this is by creating a `.env` file in the project root.
    Create the file named `.env` and add your key like this:
    ```
    OPENAI_API_KEY="your-secret-api-key-here"
    ```
    The application uses the `python-dotenv` library to automatically load this file.

5.  **Start FalkorDB (using Docker):**
    Even for local development, it's easiest to run the database in Docker.
    ```bash
    docker run -d -p 6379:6379 -v falkordb_data:/data falkordb/falkordb:latest
    ```

6.  **Add your PDFs:**
    * Place your initial 5 PDF files into the `data/initial_pdfs` directory.
    * Place the additional 5 PDF files into the `data/additional_pdfs` directory.

#### 3. Running the Application Commands

**Important:** Ensure your virtual environment is active (you should see `(venv)` in your terminal prompt) before running these commands.

* **Build the graph:**
    ```bash
    python -m app build
    ```
* **Ask a question:**
    ```bash
    python -m app ask "Who authored Efficient Estimation of Word Representations in Vector Space?"
    ```
* **Generate a visualization:**
    ```bash
    python -m app visualize
    ```
    This creates `graph.html` in your project root.

### Option 2: Running with Docker (Recommended)

This is the recommended method as it handles all dependencies and networking automatically.

#### 1. Prerequisites

* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)
* An OpenAI API Key

#### 2. Setup

1.  **Add your API Key:**
    Create a `.env` file in the project root and add your key:
    ```
    OPENAI_API_KEY="your-key-here"
    ```
2.  **Add your PDFs:**
    * Place your initial 5 PDFs in `data/initial_pdfs`.
    * Place the additional 5 PDFs in `data/additional_pdfs`.

#### 3. Available Commands (Docker)

1.  **Build and Start Services:**
    This command builds the application image and starts both the `app` and `falkordb` containers.
    ```bash
    docker-compose up --build -d
    ```
2.  **Build the Knowledge Graph:**
    Use `docker-compose exec` to run commands inside the `app` container.
    ```bash
    docker-compose exec app python -m app build
    ```
3.  **Ask a Question:**
    ```bash
    docker-compose exec app python -m app ask "Who authored Efficient Estimation of Word Representations in Vector Space?"
    ```
4.  **Visualize the Graph:**
    ```bash
    docker-compose exec app python -m app visualize
    ```
    This creates `graph.html` in your project's root directory.
5.  **Stop the Services:**
    When you are finished, stop and remove the containers.
    ```bash
    docker-compose down
    ```
    To also remove the database volume (deleting all graph data), add the `-v` flag:
    ```bash
    docker-compose down -v
    ```

## Exploring the Graph

After you have run the `build` command, you can use the following commands to explore the structure and content of your knowledge graph. This is useful for understanding what kind of information has been extracted and for formulating better questions.

### `schema`

The `schema` command displays the high-level structure (ontology) of your graph. It lists all the entity types (e.g., `Person`, `Paper`, `Concept`) and the relationship types that connect them.

* **Usage (Local):**
    ```bash
    python -m app schema
    ```
* **Usage (Docker):**
    ```bash
    docker-compose exec app python -m app schema
    ```
* **Get live counts:**
    You can add the `--counts` or `-c` flag to query the database and see how many nodes and edges of each type currently exist.
    ```bash
    python -m app schema --counts
    ```

### `relations`

This command lists all the relationship types (e.g., `AUTHORED_BY`, `CITES`, `TOPIC_OF`) defined in the ontology.

* **Usage (Local):**
    ```bash
    python -m app relations
    ```
* **Usage (Docker):**
    ```bash
    docker-compose exec app python -m app relations
    ```
* **Get live counts:**
    Like the `schema` command, you can add the `--counts` or `-c` flag to see how many of each relationship exist in the graph.
    ```bash
    python -m app relations -c
    ```

### `concepts`

This command lists all the nodes of a specific type that exist in the graph. By default, it lists all `Concept` nodes, but you can specify a different label.

* **Usage (Local):**
    ```bash
    # List all 'Concept' nodes
    python -m app concepts

    # List all 'Person' nodes
    python -m app concepts --label Person
    ```
* **Usage (Docker):**
    ```bash
    # List all 'Concept' nodes
    docker-compose exec app python -m app concepts
    ```

## Testing

The project includes a test suite using `pytest`. The tests use mocking to isolate the application from external services, ensuring fast and reliable execution.

To run the tests, make sure you have set up the local environment and installed the dependencies, then run:
```bash
pytest
