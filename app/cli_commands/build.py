# app/cli_commands/build.py
import typer
import json
import traceback

from graphrag_sdk import KnowledgeGraph, Ontology
from graphrag_sdk.models.litellm import LiteModel
from graphrag_sdk.model_config import KnowledgeGraphModelConfig

from app import config, utils
from app.loaders import UnstructuredPDFLoader

def build():
    """Build and evolve the knowledge graph from all PDF files."""
    typer.echo("🚀 Starting the knowledge-graph build process…")
    try:
        pdf_loader = UnstructuredPDFLoader()
        initial_docs = pdf_loader.load(config.INITIAL_PDF_DIR)
        if not initial_docs:
            typer.secho(f"No PDFs found in '{config.INITIAL_PDF_DIR}'. Aborting.", fg=typer.colors.RED)
            raise typer.Exit()

        typer.echo("\n--- Creating Ontology ---")
        model = LiteModel(model_name=config.MODEL_NAME)
        typer.echo("🔍 Discovering ontology from documents…")
        discovered = Ontology.from_documents(initial_docs, model=model)

        if config.ONTO_PATH.exists():
            typer.echo("📄  Merging with existing ontology.json")
            raw_json = json.loads(config.ONTO_PATH.read_text())
            existing = Ontology.from_json(utils.normalise_schema(raw_json))
            ontology = utils.merge_ontologies(existing, discovered)
        else:
            typer.echo("📄  No existing ontology.json, using discovered one")
            ontology = discovered

        config.ONTO_PATH.write_text(json.dumps(ontology.to_json(), indent=2))
        typer.secho("✓  ontology.json updated", fg=typer.colors.GREEN)

        typer.echo("\n--- Creating and Evolving Knowledge Graph ---")
        kg = KnowledgeGraph(
            name=config.GRAPH_NAME,
            model_config=KnowledgeGraphModelConfig.with_model(model),
            ontology=ontology,
            host=config.FALKORDB_HOST,
            port=config.FALKORDB_PORT,
        )

        typer.echo(f"\nIngesting {len(initial_docs)} initial documents…")
        kg.process_documents(initial_docs)
        typer.secho("✅ Initial ingestion complete.", fg=typer.colors.GREEN)

        additional_docs = pdf_loader.load(config.ADDITIONAL_PDF_DIR)
        all_docs = initial_docs + additional_docs
        typer.echo(f"\nEvolving graph with all {len(all_docs)} documents…")
        kg.process_documents(all_docs)
        typer.secho("✅ Graph evolution complete.", fg=typer.colors.GREEN)
        typer.secho("\n🎉 Knowledge-graph build finished successfully!", fg=typer.colors.BRIGHT_GREEN)

    except Exception as e:
        typer.secho(f"🔥 A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)