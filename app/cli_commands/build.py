
# app/cli_commands/build.py
import typer
import json
import traceback
import os

from graphrag_sdk import KnowledgeGraph, Ontology
from graphrag_sdk.models.litellm import LiteModel
from graphrag_sdk.model_config import KnowledgeGraphModelConfig

from app import config, utils
from app.loaders import UnstructuredPDFLoader

def build(
    model: str = typer.Option(
        config.DEFAULT_MODEL_NAME,
        "--model",
        "-m",
        help="The model to use for processing, e.g., 'openai/gpt-4.1' or 'gemini/gemini-pro'."
    )
):
    """Build and evolve the knowledge graph from all PDF files."""
    typer.echo("🚀 Starting the knowledge-graph build process…")
    try:
        # --- MODIFIED: Use the new duck-typed loader class ---
        initial_sources = [
            UnstructuredPDFLoader(path=os.path.join(config.INITIAL_PDF_DIR, f))
            for f in os.listdir(config.INITIAL_PDF_DIR)
            if f.endswith(".pdf")
        ]

        if not initial_sources:
            typer.secho(f"No PDFs found in '{config.INITIAL_PDF_DIR}'. Aborting.", fg=typer.colors.RED)
            raise typer.Exit()

        typer.echo(f"\n--- Using model: {model} ---")
        llm = LiteModel(model_name=model)
        
        typer.echo("\n--- Creating Ontology ---")
        typer.echo("🔍 Discovering ontology from documents…")
        # The SDK's from_sources method will work with our duck-typed loader
        discovered = Ontology.from_sources(initial_sources, model=llm)

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
            model_config=KnowledgeGraphModelConfig.with_model(llm),
            ontology=ontology,
            host=config.FALKORDB_HOST,
            port=config.FALKORDB_PORT,
        )

        typer.echo(f"\nIngesting {len(initial_sources)} initial documents…")
        # The SDK's process_sources method will also work
        kg.process_sources(initial_sources)
        typer.secho("✅ Initial ingestion complete.", fg=typer.colors.GREEN)

        additional_sources = [
            UnstructuredPDFLoader(path=os.path.join(config.ADDITIONAL_PDF_DIR, f))
            for f in os.listdir(config.ADDITIONAL_PDF_DIR)
            if f.endswith(".pdf")
        ]
        all_sources = initial_sources + additional_sources

        typer.echo(f"\nEvolving graph with all {len(all_sources)} documents…")
        kg.process_sources(all_sources)
        typer.secho("✅ Graph evolution complete.", fg=typer.colors.GREEN)
        typer.secho("\n🎉 Knowledge-graph build finished successfully!", fg=typer.colors.BRIGHT_GREEN)

    except Exception as e:
        typer.secho(f"🔥 A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)

