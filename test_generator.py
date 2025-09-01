
import os
import json
import re
import time

# Reverting to the consumer-grade Google AI SDK to bypass Vertex AI issues
import google.generativeai as genai

# --- Configuration ---
# This section is now simplified as we are not using the Vertex AI SDK for generation

# --- Client Initialization ---
gemini_model = None
try:
    # Authenticate using the API Key from the .env file
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
    print("--- Google AI (API Key) initialized successfully. ---")
except Exception as e:
    print(f"FATAL ERROR initializing Google AI: {e}")

# This function is no longer needed for the simplified chat
def search_compliance_database(query: str) -> list[str]:
    # This function would require the Vertex AI Search client, which we are removing
    # to simplify the architecture and solve the core issue.
    return []

def extract_json_from_string(text: str) -> str:
    match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
    if match: return match.group(1).strip()
    start_index = text.find('[')
    end_index = text.rfind(']') + 1
    if start_index != -1 and end_index != 0: return text[start_index:end_index]
    return None

def extract_requirements_from_chunk(text_chunk: str) -> list[str]:
    if not gemini_model: raise ConnectionError("Google AI model not initialized.")
    prompt = f"""Read the following text from a software specification document. Identify and extract any specific, actionable software requirements. List each requirement as a simple bullet point, starting with '*'. If you find no requirements, respond with only the text "No requirements found.".\n\n--- TEXT CHUNK ---\n{text_chunk}\n--- END CHUNK ---"""
    response = gemini_model.generate_content(prompt)
    if "No requirements found." in response.text: return []
    return [line.strip().lstrip('*- ') for line in response.text.split('\n') if line.strip()]

def generate_test_cases_for_requirement(requirement: str) -> list:
    if not gemini_model: raise ConnectionError("Google AI model not initialized.")
    # Since we are simplifying, we remove the compliance search for now
    # compliance_context = search_compliance_database(requirement)
    # context_str = "\n".join(f"- {item}" for item in compliance_context)

    prompt = f"""Your task is to generate a JSON array of test cases for a given software requirement. Follow these steps:
1. **Analyze the Requirement:** Read the software requirement and identify the core functionality to be tested.
2. **Brainstorm Test Scenarios:** Think about positive, negative, and edge cases.
3. **Construct the Test Cases:** For each scenario, create a detailed test case object.
4. **Format the Final Output:** Format your response as a single, clean JSON array. Do not include any text or explanation before or after the JSON block.

**Software Requirement:**
{requirement}

Each test case object in the array must have the fields: 'test_case_id', 'requirement_id', 'description', 'test_type', 'priority', 'steps', 'expected_result', 'rtm_compliance_mapping'. If you cannot generate a meaningful test case, return an empty JSON array `[]`."""

    for attempt in range(2):
        try:
            response = gemini_model.generate_content(prompt)
            json_string = extract_json_from_string(response.text)
            if json_string:
                return json.loads(json_string)
        except Exception as e:
            print(f"    -> Test case generation attempt {attempt + 1} failed: {e}")
        time.sleep(1)
    return []
