# api.py
import falkordb
from fastapi import FastAPI
from litellm import completion

# --- FastAPI App & Database Connection ---
app = FastAPI()
r = falkordb.FalkorDB(host="localhost", port=6379)
db = r.select_graph("assignment_kg")

@app.get("/ask")
def ask_question(question: str):
    """
    Takes a user's natural language question, converts it to a Cypher query using an LLM,
    queries the graph, and returns the result.
    """
    print(f"Received question: {question}")

    # Use an LLM to generate a Cypher query from the user's question
    system_prompt = """
    You are an expert FalkorDB developer. Based on the user's question, generate a single, simple Cypher query to answer it.
    The available node types are PERSON, TECHNOLOGY, ORGANIZATION, MOVIE.
    The available relationship types are WORKED_ON, DIRECTED, INFLUENCED.
    Respond with ONLY the Cypher query. Do not include any other text, explanations, or markdown.
    """
    
    print("Generating Cypher query...")
    response = completion(
        model="openai/gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    )
    cypher_query = response.choices[0].message.content
    
    # --- Clean the LLM output ---
    # Remove markdown code block fences if they exist
    if "```" in cypher_query:
        # Assumes the query is between the first and last backticks
        cypher_query = cypher_query.split("```")[1]
        # remove the language specifier if it exists
        if cypher_query.lower().startswith("cypher"):
            cypher_query = cypher_query[len("cypher"):].strip()

    # Strip any leading/trailing whitespace
    cypher_query = cypher_query.strip()
    print(f"Generated Cypher (cleaned): {cypher_query}")

    try:
        # Execute the cleaned query against the database
        result = db.query(cypher_query)
        return {"question": question, "cypher_query": cypher_query, "answer": result.result_set}
    except Exception as e:
        return {"error": str(e), "cypher_query": cypher_query}