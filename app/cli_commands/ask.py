# app/cli_commands/ask.py
import typer
import os
import json
import traceback

from graphrag_sdk import KnowledgeGraph, Ontology
from graphrag_sdk.models.litellm import LiteModel
from graphrag_sdk.model_config import KnowledgeGraphModelConfig

from app import config

def ask(
    question: str = typer.Argument(..., help="Your natural-language question."),
    model: str = typer.Option(
        config.DEFAULT_MODEL_NAME,
        "--model",
        "-m",
        help="The model to use for answering, e.g., 'openai/gpt-4.1' or 'ollama/llama3'."
    )
):
    """Ask a question against the knowledge graph."""
    typer.echo(f"❓ Asking: '{question}'")
    try:
        if not os.path.exists(config.ONTOLOGY_FILE):
            typer.secho(f"Error: Ontology file '{config.ONTOLOGY_FILE}' not found.", fg=typer.colors.RED)
            raise typer.Exit()

        with open(config.ONTOLOGY_FILE, "r", encoding="utf-8") as file:
            ontology = Ontology.from_json(json.load(file))
        
        typer.echo(f"--- Using model: {model} ---")
        llm = LiteModel(model_name=model)
        kg = KnowledgeGraph(
            name=config.GRAPH_NAME,
            model_config=KnowledgeGraphModelConfig.with_model(llm),
            ontology=ontology,
            host=config.FALKORDB_HOST,
            port=config.FALKORDB_PORT,
        )
        typer.echo("  - Starting chat session…")
        response = kg.chat_session().send_message(question)
        typer.secho("✅ Answer:", fg=typer.colors.GREEN)
        typer.echo(response['response'])
    except Exception as e:
        typer.secho(f"🔥 A critical error occurred: {e}", fg=typer.colors.RED)
        traceback.print_exception(e)
