import os
import sys
import json
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Add the project root to the Python path to allow importing the 'app' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Typer app instance from your main script
from app.__main__ import app, typer

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

@patch('app.__main__.LiteModel')
@patch('app.__main__.Ontology')
@patch('app.__main__.KnowledgeGraph')
def test_build_command(MockKnowledgeGraph, MockOntology, MockLiteModel, mock_pdf_dirs):
    """Test the 'build' command to ensure it processes files and creates the graph."""
    initial_dir, additional_dir = mock_pdf_dirs
    
    mock_onto_instance = MagicMock()
    mock_onto_instance.to_json.return_value = {"entities": [], "relations": []}
    MockOntology.from_sources.return_value = mock_onto_instance
    MockOntology.from_json.return_value = mock_onto_instance

    with patch('app.__main__.INITIAL_PDF_DIR', initial_dir), \
         patch('app.__main__.ADDITIONAL_PDF_DIR', additional_dir), \
         patch('app.__main__.ONTO_PATH', MagicMock(exists=lambda: False, write_text=lambda d: None)):

        result = runner.invoke(app, ["build"])

        assert result.exit_code == 0, result.stdout
        assert "🚀 Starting the knowledge-graph build process…" in result.stdout
        assert "✅ Initial ingestion complete." in result.stdout
        assert "✅ Graph evolution complete." in result.stdout
        
        assert MockKnowledgeGraph.call_count == 1
        mock_kg_instance = MockKnowledgeGraph.return_value
        assert mock_kg_instance.process_sources.call_count == 2

@patch('app.__main__.KnowledgeGraph')
def test_ask_command_with_ontology(MockKG, mock_ontology_file):
    """Test the 'ask' command, mocking the KG chat session."""
    with patch('app.__main__.ONTOLOGY_FILE', mock_ontology_file):
        
        mock_chat_session = MagicMock()
        mock_chat_session.send_message.return_value = {'response': 'This is a test answer.'}
        MockKG.return_value.chat_session.return_value = mock_chat_session
        
        result = runner.invoke(app, ["ask", "What is a test?"])
        
        assert result.exit_code == 0, result.stdout
        assert "❓ Asking: 'What is a test?'" in result.stdout
        assert "✅ Answer:" in result.stdout
        assert "This is a test answer." in result.stdout

def test_ask_command_no_ontology():
    """Test that 'ask' command fails gracefully if ontology.json is missing."""
    with patch('app.__main__.os.path.exists', return_value=False):
        result = runner.invoke(app, ["ask", "test"])
        # typer.Exit() defaults to exit_code 0, so we check the output message instead.
        assert "Error: Ontology file 'ontology.json' not found." in result.stdout
        assert "✅ Answer:" not in result.stdout

@patch('asyncio.run')
def test_schema_command(mock_asyncio_run, mock_ontology_file):
    """Test the 'schema' command to ensure it prints the ontology."""
    with patch('app.__main__.ONTOLOGY_FILE', mock_ontology_file):
        # Mock redis import for the --counts flag, even if not used
        with patch.dict(sys.modules, {'redis.asyncio': MagicMock()}):
            result = runner.invoke(app, ["schema"])
        
        assert result.exit_code == 0, result.stdout
        assert "📦  ENTITY LABELS" in result.stdout
        assert "Person" in result.stdout
        assert "🔗  RELATIONS" in result.stdout
        assert "AUTHORED_BY" in result.stdout

@patch('asyncio.run')
@patch('app.__main__.Network')
def test_visualize_command(MockPyvisNetwork, mock_asyncio_run):
    """Test the 'visualize' command, mocking the DB connection and PyVis."""
    mock_asyncio_run.return_value = [
        [1, 2, 'Paper', 'Person', 'AUTHORED_BY', 'Test Paper', 'Test Author', 1, 1]
    ]
    
    mock_net_instance = MagicMock()
    MockPyvisNetwork.return_value = mock_net_instance
    
    # Mock the optional redis import
    with patch.dict(sys.modules, {'redis.asyncio': MagicMock()}):
        result = runner.invoke(app, ["visualize", "--output", "test_graph.html"])
    
    assert result.exit_code == 0, result.stdout
    assert "Generating interactive graph visualization..." in result.stdout
    assert mock_net_instance.add_node.call_count == 2
    assert mock_net_instance.add_edge.call_count == 1
    mock_net_instance.show.assert_called_with("test_graph.html")
    assert "✅  Graph saved to test_graph.html" in result.stdout

# @patch('asyncio.run')
# def test_examples_command(mock_asyncio_run):
#     """Test the 'examples' command with a mocked graph."""
#     mock_asyncio_run.return_value = (
#         ['Concept A'],
#         [['NodeA', 'RELATES_TO', 'NodeB', 0.5]],
#         ['Paper A'],
#         [['Paper A', 'Author X', 0.5]]
#     )
    
#     # Mock the optional redis import
#     mock_redis = MagicMock()
#     mock_redis.asyncio = MagicMock()
#     with patch.dict(sys.modules, {'redis': mock_redis, 'redis.asyncio': mock_redis.asyncio}):
#         result = runner.invoke(app, ["examples"])
    
#     assert result.exit_code == 0, result.stdout
#     assert "💡 Here are some example questions tailored to your graph:" in result.stdout
#     assert "Who authored the paper" in result.stdout or "What papers did" in result.stdout

def test_all_commands_help():
    """Ensure every command has a --help flag that works."""
    commands = ["build", "ask", "schema", "visualize", "concepts", "relations"]
    for command in commands:
        args = [command, "--help"] if command != "ask" else [command, "dummy", "--help"]
        # Mock dependencies that might be checked early
        mock_redis = MagicMock()
        mock_redis.asyncio = MagicMock()
        with patch('app.__main__.os.path.exists', return_value=True), \
             patch.dict(sys.modules, {'redis': mock_redis, 'redis.asyncio': mock_redis.asyncio}), \
             patch('asyncio.run', return_value=([],[],[],[])):
            result = runner.invoke(app, args)
            assert result.exit_code == 0, f"Help flag failed for command: {command}\n{result.stdout}"
            assert "Usage:" in result.stdout
