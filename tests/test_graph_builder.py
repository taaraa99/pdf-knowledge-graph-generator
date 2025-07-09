# tests/test_graph_builder.py
import pytest
from unittest.mock import patch
from app.graph_builder import GraphBuilder

# A simple unit test to check if the GraphBuilder class can be initialized
def test_graph_builder_initialization():
    """Tests that the GraphBuilder can be created."""
    builder = GraphBuilder()
    assert builder.model_name == "openai/gpt-4o"
    assert "You are an expert" in builder.system_prompt

# This is a more advanced test that 'mocks' the OpenAI API call
# It checks if our class correctly processes a fake response from the LLM
@patch('app.graph_builder.completion')
def test_extract_graph_from_chunk(mock_completion):
    """Tests the graph extraction logic with a mocked API call."""
    # Define a fake response from the litellm.completion function
    class MockChoice:
        class MockMessage:
            content = '{"entities": [{"name": "Test"}], "relationships": []}'
        message = MockMessage()
    
    class MockResponse:
        choices = [MockChoice()]

    mock_completion.return_value = MockResponse()

    builder = GraphBuilder()
    result = builder.extract_graph_from_chunk("some text")

    # Assert that the function correctly parsed the fake JSON
    assert result is not None
    assert "entities" in result
    assert result["entities"][0]["name"] == "Test"