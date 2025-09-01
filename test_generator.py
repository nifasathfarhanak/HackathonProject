
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

def extract_requirements_from_chunk(text_chunk: str) -> list[str]:
    """Uses a robust, two-attempt strategy to extract requirements as a simple list."""
    if not gemini_model: raise ConnectionError("Google AI model not initialized.")
    
    prompt = f"""Read the following text from a software specification document. Identify and extract any specific, actionable software requirements. List each requirement as a simple bullet point, starting with '*'. If you find no requirements, respond with only the text "No requirements found.".\n\n--- TEXT CHUNK ---\n{text_chunk}\n--- END CHUNK ---"""

    for attempt in range(2):
        try:
            response = gemini_model.generate_content(prompt)
            if "No requirements found." in response.text:
                return []
            
            # Use regex to find all lines that start with a bullet point (*, -, •)
            requirements = re.findall(r'^[\*\-•]\s+(.*)', response.text, re.MULTILINE)
            if requirements:
                return requirements
        except Exception as e:
            print(f"    -> Requirement extraction attempt {attempt + 1} failed with an error: {e}")
        
        print(f"    -> Retrying requirement extraction for chunk...")
        time.sleep(1)

    print("    -> All attempts to extract requirements failed for this chunk.")
    return []

def generate_test_cases_for_requirement(requirement: str) -> list:
    """Generates a list of test case dicts for a single requirement."""
    if not gemini_model: raise ConnectionError("Google AI model not initialized.")

    prompt = f"""Your task is to generate a JSON array of test cases for the following single software requirement.

    **Software Requirement:**
    {requirement}

    **Instructions:**
    1.  Create one or more detailed test case objects for this single requirement.
    2.  Combine all test case objects into a single JSON array.
    3.  Each test case object in the array must have the fields: 'test_case_id', 'requirement_id', 'description', 'test_type', 'priority', 'steps', 'expected_result', and 'rtm_compliance_mapping'.
    4.  If you cannot generate a meaningful test case, you MUST return an empty JSON array `[]`.
    5.  Your final output must be ONLY the JSON array. Do not include any other text, explanation, or markdown formatting.
    """

    for attempt in range(2):
        try:
            response = gemini_model.generate_content(prompt)
            json_string = extract_json_from_string(response.text)
            if json_string:
                return json.loads(json_string)
        except Exception as e:
            print(f"    -> Test case generation attempt {attempt + 1} failed for requirement: '{requirement[:30]}...'")
        time.sleep(1)

    return []
