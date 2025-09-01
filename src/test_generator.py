
import os
import json
import re
import time

# Using the consumer-grade Google AI SDK as it is more reliable for your project
import google.generativeai as genai

# --- Client Initialization ---
gemini_model = None
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
    print("--- Google AI (API Key) initialized successfully. ---")
except Exception as e:
    print(f"FATAL ERROR initializing Google AI: {e}")

def extract_json_from_string(text: str) -> str:
    """More robustly extracts a JSON array from a string."""
    match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback for cases where the AI forgets the markdown
    start_index = text.find('[')
    end_index = text.rfind(']') + 1
    if start_index != -1 and end_index != 0:
        return text[start_index:end_index]
    return None

def generate_test_cases_from_chunk(text_chunk: str) -> list:
    """Generates a list of test case dicts from a chunk of a requirement document."""
    if not gemini_model:
        raise ConnectionError("Google AI model not initialized.")

    # The prompt now asks the AI to find and process all requirements within the chunk.
    prompt = f"""Your task is to act as a senior QA engineer. Read the following chunk of a software requirement document. Identify any and all specific, actionable requirements within this text. For each requirement you find, generate a detailed set of test cases.

    **Document Chunk:**
    {text_chunk}

    **Instructions:**
    1.  Carefully read the entire text chunk.
    2.  Identify all distinct functional or non-functional requirements.
    3.  For each requirement, create one or more test case objects.
    4.  Combine all test case objects from this chunk into a single JSON array.
    5.  Each test case object in the array must have the fields: 'test_case_id', 'requirement_id', 'description', 'test_type', 'priority', 'steps', 'expected_result', and 'rtm_compliance_mapping'.
    6.  If you find no actionable requirements in this chunk, you MUST return an empty JSON array `[]`.
    7.  Your final output must be ONLY the JSON array. Do not include any other text, explanation, or markdown formatting.
    """

    for attempt in range(2):
        try:
            response = gemini_model.generate_content(prompt)
            json_string = extract_json_from_string(response.text)
            if json_string:
                return json.loads(json_string)
            else:
                print(f"    -> Attempt {attempt + 1} failed: No JSON found in response for chunk.")
        except json.JSONDecodeError as e:
            print(f"    -> Attempt {attempt + 1} failed: Could not decode JSON. Error: {e}")
        except Exception as e:
            print(f"    -> Attempt {attempt + 1} failed with an unexpected error: {e}")
        
        print("    -> Retrying chunk...")
        time.sleep(1)

    print("    -> All attempts failed for this chunk. Returning empty list.")
    return []
