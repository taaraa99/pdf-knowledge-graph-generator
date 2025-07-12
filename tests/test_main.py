import os
import sys
import json
import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Add the project root to the Python path to allow importing the 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Typer app instance and other necessary components
from app.commands import app
from app.loaders import UnstructuredPDFLoader
from graphrag_sdk.document import Document

# Create a CliRunner instance to invoke the commands
runner = CliRunner()

@pytest.fixture(scope="module")
def mock_ontology_file(tmpdir_factory):
    """Create a temporary, dummy ontology.json file for tests."""
    ontology_data = {
        "entities": [
            {"label": "Person", "attributes": [{"name": "name", "type": "string", "unique": True, "required": True}]},
            {"label": "Paper", "attributes": [{"name": "title", "type": "string", "unique": False, "required": False}]}
        ],
        "relations": [
            {"label": "AUTHORED_BY", "source": {"label": "Paper"}, "target": {"label": "Person"}, "attributes": []}
        ]
    }
    fn = tmpdir_factory.mktemp("data").join("ontology.json")
    fn.write(json.dumps(ontology_data))
    return str(fn)

@pytest.fixture
def mock_pdf_dirs(tmpdir):
    """Create temporary PDF directories with dummy files."""
    initial_dir = Path(tmpdir.mkdir("initial_pdfs"))
    additional_dir = Path(tmpdir.mkdir("additional_pdfs"))
    
    for i in range(5):
        (initial_dir / f"doc_{i}.pdf").touch()
    for i in range(5, 10):
        (additional_dir / f"doc_{i}.pdf").touch()
        
    return str(initial_dir), str(additional_dir)

# --- CORRECTED: Unit test specifically for the UnstructuredPDFLoader ---
def test_unstructured_pdf_loader(tmpdir):
    """
    Unit test for the UnstructuredPDFLoader to ensure it calls the
    unstructured library correctly and creates Document objects.
    """
    # Arrange: Create a dummy PDF file for the loader to find
    pdf_dir = Path(tmpdir.mkdir("pdfs"))
    test_pdf_path = pdf_dir / "test.pdf"
    test_pdf_path.touch()

    # Act: Instantiate our real loader
    loader = UnstructuredPDFLoader()
    
    # Arrange: Mock the partition function on the instance of the loader.
    # Configure the mock's __str__ to return the desired text.
    mock_element_1 = MagicMock()
    mock_element_1.__str__.return_value = "This is a title."
    mock_element_2 = MagicMock()
    mock_element_2.__str__.return_value = "This is a paragraph."
    
    mock_partition = MagicMock(return_value=[mock_element_1, mock_element_2])
    loader._partition = mock_partition
    
    documents = loader.load(str(pdf_dir))

    # Assert: Check that the partition function was called once with the correct filename
    mock_partition.assert_called_once_with(filename=str(test_pdf_path))

    # Assert: Check that we got one Document object back
    assert len(documents) == 1
    doc = documents[0]
    assert isinstance(doc, Document)
    assert "This is a title." in doc.content
    assert "This is a paragraph." in doc.content
    assert doc.id == str(test_pdf_path)


# --- Integration-style tests for the CLI commands ---

@patch('app.cli_commands.build.LiteModel')
@patch('app.cli_commands.build.Ontology')
@patch('app.cli_commands.build.KnowledgeGraph')
@patch('app.cli_commands.build.UnstructuredPDFLoader')
def test_build_command(MockLoader, MockKnowledgeGraph, MockOntology, MockLiteModel, mock_pdf_dirs):
    """Test the 'build' command's logic, mocking the loader and SDK classes."""
    initial_dir, additional_dir = mock_pdf_dirs
    
    mock_loader_instance = MockLoader.return_value
    mock_loader_instance.load.return_value = [MagicMock()] * 5

    mock_onto_instance = MagicMock()
    mock_onto_instance.to_json.return_value = {"entities": [], "relations": []}
    MockOntology.from_documents.return_value = mock_onto_instance
    MockOntology.from_json.return_value = mock_onto_instance

    with patch('app.config.INITIAL_PDF_DIR', initial_dir), \
         patch('app.config.ADDITIONAL_PDF_DIR', additional_dir), \
         patch('app.config.ONTO_PATH', MagicMock(exists=lambda: False, write_text=lambda d: None)):

        result = runner.invoke(app, ["build"])

        assert result.exit_code == 0, result.stdout
        assert "🚀 Starting the knowledge-graph build process…" in result.stdout
        assert "✅ Initial ingestion complete." in result.stdout
        assert "✅ Graph evolution complete." in result.stdout
        
        assert MockKnowledgeGraph.call_count == 1
        mock_kg_instance = MockKnowledgeGraph.return_value
        assert mock_kg_instance.process_documents.call_count == 2

@patch('app.cli_commands.ask.LiteModel')
@patch('app.cli_commands.ask.KnowledgeGraph')
def test_ask_command_with_ontology(MockKG, MockLiteModel, mock_ontology_file):
    """Test the 'ask' command, mocking the KG chat session."""
    with patch('app.config.ONTOLOGY_FILE', mock_ontology_file):
        
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.return_value = {'response': 'This is a test answer.'}
        MockKG.return_value.chat_session.return_value = mock_chat_session
        
        result = runner.invoke(app, ["ask", "What is a test?"])
        
        assert result.exit_code == 0, result.stdout
        assert "❓ Asking: 'What is a test?'" in result.stdout
        assert "✅ Answer:" in result.stdout
        assert "This is a test answer." in result.stdout

# --- CORRECTED: Test for graceful exit when ontology is missing ---
def test_ask_command_no_ontology():
    """Test that 'ask' command fails gracefully if ontology.json is missing."""
    with patch('app.cli_commands.ask.os.path.exists', return_value=False):
        result = runner.invoke(app, ["ask", "test"])
        # Check that the error message is in the output and the success message is not.
        assert "Error: Ontology file 'ontology.json' not found." in result.stdout
        assert "✅ Answer:" not in result.stdout

@patch('asyncio.run')
def test_schema_command(mock_asyncio_run, mock_ontology_file):
    """Test the 'schema' command to ensure it prints the ontology."""
    with patch('app.config.ONTOLOGY_FILE', mock_ontology_file), \
         patch.dict(sys.modules, {'redis.asyncio': MagicMock()}):
        result = runner.invoke(app, ["schema"])
        
        assert result.exit_code == 0, result.stdout
        assert "📦  ENTITY LABELS" in result.stdout
        assert "Person" in result.stdout
        assert "🔗  RELATIONS" in result.stdout
        assert "AUTHORED_BY" in result.stdout

@patch('asyncio.run')
@patch('app.cli_commands.visualize.Network')
def test_visualize_command(MockPyvisNetwork, mock_asyncio_run):
    """Test the 'visualize' command, mocking the DB connection and PyVis."""
    mock_asyncio_run.return_value = [
        [1, 2, 'Paper', 'Person', 'AUTHORED_BY', 'Test Paper', 'Test Author', 1, 1]
    ]
    
    mock_net_instance = MagicMock()
    MockPyvisNetwork.return_value = mock_net_instance
    
    with patch.dict(sys.modules, {'redis.asyncio': MagicMock()}):
        result = runner.invoke(app, ["visualize", "--output", "test_graph.html"])
    
    assert result.exit_code == 0, result.stdout
    assert "Generating interactive graph visualization..." in result.stdout
    assert mock_net_instance.add_node.call_count == 2
    assert mock_net_instance.add_edge.call_count == 1
    mock_net_instance.show.assert_called_with("test_graph.html")
    assert "✅  Graph saved to test_graph.html" in result.stdout

def test_all_commands_help():
    """Ensure every command has a --help flag that works."""
    commands = ["build", "ask", "schema", "visualize", "concepts", "relations"]
    for command in commands:
        args = [command, "--help"] if command != "ask" else [command, "dummy", "--help"]
        with patch('os.path.exists', return_value=True), \
             patch.dict(sys.modules, {'redis.asyncio': MagicMock()}), \
             patch('asyncio.run', return_value=([],[],[],[])):
            result = runner.invoke(app, args)
            assert result.exit_code == 0, f"Help flag failed for command: {command}\n{result.stdout}"
            assert "Usage:" in result.stdout
