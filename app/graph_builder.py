# app/graph_builder.py
import json
from litellm import completion

class GraphBuilder:
    """Extracts a knowledge graph from text using an LLM."""
    def __init__(self, model_name="openai/gpt-4o"):
        self.model_name = model_name
        self.system_prompt = """
        You are an expert at creating knowledge graphs. From the text provided, extract entities and their relationships.
        An entity should have a 'name', a 'type' (e.g., PERSON, ORGANIZATION, TECHNOLOGY), and a 'description'.
        A relationship should have a 'source' entity name, a 'target' entity name, and a 'type' (e.g., DIRECTED, WORKED_ON, INFLUENCED).
        Respond with ONLY a valid JSON object containing two keys: "entities" and "relationships". Do not include any other text or explanations.
        Example: {"entities": [{"name": "Neo", "type": "PERSON", "description": "The protagonist"}], "relationships": []}
        """

    def extract_graph_from_chunk(self, text_chunk):
        """Sends a single text chunk to the LLM for graph extraction."""
        print("  - Calling LLM to extract graph from text chunk...")
        try:
            response = completion(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text_chunk}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"    ERROR: Could not get valid JSON from LLM. Error: {e}")
            return None