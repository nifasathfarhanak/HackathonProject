
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
    gemini_model = genai.GenerativeModel('gemini-pro-latest')
    print("--- Google AI (API Key) initialized successfully. ---")
except Exception as e:
    print(f"FATAL ERROR initializing Google AI: {e}")

def parse_ai_response_to_dicts(text: str) -> list:
    """Parses a structured text response from the AI into a list of dictionaries."""
    test_cases = []
    # Regex to find entire test case blocks
    test_case_blocks = re.findall(r"===TEST CASE START===\n(.*?)\n===TEST CASE END===", text, re.DOTALL)

    for block in test_case_blocks:
        test_case = {}
        # Use regex to find each field, making it robust to missing fields
        id_match = re.search(r"ID: (.*?)\n", block)
        if id_match: test_case['test_case_id'] = id_match.group(1).strip()

        req_match = re.search(r"REQ: (.*?)\n", block)
        if req_match: test_case['requirement_id'] = req_match.group(1).strip()

        desc_match = re.search(r"DESC: (.*?)\n", block)
        if desc_match: test_case['description'] = desc_match.group(1).strip()

        type_match = re.search(r"TYPE: (.*?)\n", block)
        if type_match: test_case['test_type'] = type_match.group(1).strip()

        priority_match = re.search(r"PRIORITY: (.*?)\n", block)
        if priority_match: test_case['priority'] = priority_match.group(1).strip()

        # Find all steps
        steps = re.findall(r"STEP: (.*?)\n", block)
        test_case['steps'] = [s.strip() for s in steps]

        expected_match = re.search(r"EXPECTED: (.*?)\n", block)
        if expected_match: test_case['expected_result'] = expected_match.group(1).strip()

        rtm_match = re.search(r"RTM: (.*?)\n", block)
        if rtm_match: test_case['rtm_compliance_mapping'] = rtm_match.group(1).strip()
        
        confidence_match = re.search(r"CONFIDENCE: (.*?)\n", block)
        if confidence_match: test_case['confidence_score'] = confidence_match.group(1).strip()

        # Only add the test case if it has a description
        if test_case.get('description'):
            test_cases.append(test_case)
            
    return test_cases

def generate_test_cases_from_chunk(text_chunk: str) -> list:
    """Generates a list of test case dicts from a chunk of a requirement document."""
    if not gemini_model:
        raise ConnectionError("Google AI model not initialized.")

    # New prompt asking for a simple, structured text format instead of JSON
    prompt = f"""Your task is to act as a senior QA engineer. Read the following chunk of a software requirement document. Identify any and all specific, actionable requirements within this text. For each requirement you find, generate a detailed set of test cases in the specified format.

    **Document Chunk:**
    {text_chunk}

    **Output Format Instructions:**
    - For each test case, you MUST start with the line `===TEST CASE START===`.
    - Each field must be on its own line, starting with the field name, a colon, and a space.
    - The fields are: `ID`, `REQ`, `DESC`, `TYPE`, `PRIORITY`, `STEP` (use one line for each step), `EXPECTED`, `RTM`, `CONFIDENCE`.
    - For the 'TYPE' field, you should generate a variety of test cases for each requirement, including (where applicable): Functional, Regression, Positive, Negative, Boundary, Edge, and Security.
    - You MUST provide a value for the `RTM` field. If no specific traceability information is available, you MUST write `RTM: N/A`.
    - A `CONFIDENCE` score (e.g., `CONFIDENCE: 95%`) indicating how accurately the test case reflects the source requirement.
    - You MUST end each test case with the line `===TEST CASE END===`.
    - If you find no actionable requirements in this chunk, return an empty response.

    **Example of a perfect, complete response:**
    ===TEST CASE START===
    ID: TC-001
    REQ: REQ-4.2.1
    DESC: Verify that the user can log in with valid credentials.
    TYPE: Positive
    PRIORITY: High
    STEP: Navigate to the login page.
    STEP: Enter a valid username and password.
    STEP: Click the login button.
    EXPECTED: The user is successfully logged in and redirected to the dashboard.
    RTM: IEC 62304 - 5.2.2
    CONFIDENCE: 98%
    ===TEST CASE END===
    ===TEST CASE START===
    ID: TC-002
    REQ: REQ-4.2.1
    DESC: Verify that the user cannot log in with invalid credentials.
    TYPE: Negative
    PRIORITY: High
    STEP: Navigate to the login page.
    STEP: Enter an invalid username and password.
    STEP: Click the login button.
    EXPECTED: An error message is displayed to the user.
    RTM: N/A
    CONFIDENCE: 95%
    ===TEST CASE END===
    """

    try:
        response = gemini_model.generate_content(prompt)
        # Use the new, ultra-robust text parser
        parsed_test_cases = parse_ai_response_to_dicts(response.text)
        if parsed_test_cases:
            return parsed_test_cases
        else:
            print(f"    -> No test cases could be parsed from the AI's response for this chunk.")
    except Exception as e:
        print(f"    -> An unexpected error occurred during generation: {e}")

    return [] # Return an empty list if anything goes wrong
