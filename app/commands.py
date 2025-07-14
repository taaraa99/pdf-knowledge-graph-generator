# app/commands.py
import typer

# Import the plain command functions from their new modules
from .cli_commands.build import build
from .cli_commands.ask import ask
from .cli_commands.schema import schema
from .cli_commands.visualize import visualize
from .cli_commands.concepts import concepts
from .cli_commands.relations import relations

# Create the main Typer application instance
app = typer.Typer(
    help="A CLI to build and query a PDF Knowledge Graph using the GraphRAG-SDK.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="markdown"
)

# Register each imported function as a command on the app instance
app.command()(build)
app.command()(ask)
app.command()(schema)
app.command()(visualize)
app.command()(concepts)
app.command()(relations)
