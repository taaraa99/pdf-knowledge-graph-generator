import os
from litellm import completion

# PASTE YOUR API KEY DIRECTLY INTO THE QUOTES BELOW
# This test completely bypasses the .env file.
os.environ["OPENAI_API_KEY"] = "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" 

# A simple message to send to the API
messages = [{"content": "Hello, this is a test.", "role": "user"}]

try:
    print("--- Attempting to call OpenAI API... ---")
    response = completion(model="openai/gpt-4o", messages=messages)
    print("\n--- SUCCESS! The API key and account are working. ---")
    print(response.choices[0].message.content)

except Exception as e:
    print("\n--- ERROR! The API call failed. ---")
    print("This confirms the issue is with your API key or OpenAI account billing.")
    print("The specific error is:")
    print(e)