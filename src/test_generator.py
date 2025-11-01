
import os
import json
import re
import time

import google.generativeai as genai

# --- Client Initialization ---
gemini_model = None
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite')
    print("--- Google AI (API Key) initialized successfully. ---")
except Exception as e:
    print(f"FATAL ERROR initializing Google AI: {e}")

def parse_ai_response_to_dicts(text: str) -> list:
    """Parses the AI's custom text format into a list of test case dictionaries."""
    test_cases = []
    # Split the entire response into blocks for each test case
    for block in text.split("===TEST CASE START==="):
        if "===TEST CASE END===" not in block:
            continue

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

        steps = re.findall(r"STEP: (.*?)\n", block)
        test_case['steps'] = [s.strip() for s in steps]

        expected_match = re.search(r"EXPECTED: (.*?)\n", block)
        if expected_match: test_case['expected_result'] = expected_match.group(1).strip()

        rtm_match = re.search(r"RTM: (.*?)\n", block)
        if rtm_match: test_case['rtm_compliance_mapping'] = rtm_match.group(1).strip()

        confidence_match = re.search(r"CONFIDENCE: (.*?)\n", block)
        if confidence_match: test_case['confidence_score'] = confidence_match.group(1).strip()

        if test_case.get('description'):
            test_cases.append(test_case)
            
    return test_cases

def generate_test_cases_from_chunk(text_chunk: str) -> list:
    """Generates test cases using a simple, reliable text-based prompt."""
    if not gemini_model:
        raise ConnectionError("Google AI model not initialized.")

    prompt = f"""Your task is to act as a senior QA engineer. Read the following chunk of a software requirement document. For each actionable requirement you find, generate one or more detailed test cases using the exact format below.

    **Document Chunk:**
    {text_chunk}

    **FORMAT:**
    ===TEST CASE START===
    ID: [A unique test case ID]
    REQ: [The requirement ID]
    DESC: [A clear, one-sentence description of the test objective]
    TYPE: [e.g., Positive, Negative, Functional, Boundary, Security, Regression]
    PRIORITY: [High, Medium, or Low]
    STEP: [First step]
    STEP: [Second step]
    STEP: [Third step...]
    EXPECTED: [The expected result]
    RTM: [Traceability info, or N/A if not found]
    CONFIDENCE: [Your confidence percentage, e.g., 95%]
    ===TEST CASE END===

    **INSTRUCTIONS:**
    - You MUST follow the format precisely.
    - You MUST generate a value for the `CONFIDENCE` field for every test case.
    - You MUST generate a value for the `RTM` field for every test case.
    - If no requirements are found, return an empty response.
    """

    try:
        response = gemini_model.generate_content(prompt)
        # Use the reliable text parser
        parsed_test_cases = parse_ai_response_to_dicts(response.text)
        if parsed_test_cases:
            return parsed_test_cases
        else:
            print(f"    -> No test cases could be parsed from the AI's response for this chunk.")
            return []
    except Exception as e:
        print(f"    -> An unexpected error occurred during generation: {e}")
        return []

def edit_test_cases_with_ai(user_prompt: str, test_cases: list) -> list:
    """Uses the AI to edit a list of test cases using the same text-based format."""
    if not gemini_model:
        raise ConnectionError("Google AI model not initialized.")

    # Convert the current test cases into the text format for the AI
    test_cases_text = ""
    for tc in test_cases:
        test_cases_text += "===TEST CASE START===\n"
        test_cases_text += f"ID: {tc.get('test_case_id', 'N/A')}\n"
        test_cases_text += f"REQ: {tc.get('requirement_id', 'N/A')}\n"
        test_cases_text += f"DESC: {tc.get('description', 'N/A')}\n"
        test_cases_text += f"TYPE: {tc.get('test_type', 'N/A')}\n"
        test_cases_text += f"PRIORITY: {tc.get('priority', 'N/A')}\n"
        for step in tc.get('steps', []):
            test_cases_text += f"STEP: {step}\n"
        test_cases_text += f"EXPECTED: {tc.get('expected_result', 'N/A')}\n"
        test_cases_text += f"RTM: {tc.get('rtm_compliance_mapping', 'N/A')}\n"
        test_cases_text += f"CONFIDENCE: {tc.get('confidence_score', 'N/A')}\n"
        test_cases_text += "===TEST CASE END===\n"

    prompt = f"""Your task is to act as an intelligent test case editor. You will be given a user's instruction and a list of test cases in a specific text format. Your goal is to apply the user's instruction to the test cases and return the *entire, complete, and updated* list of test cases in the exact same text format.

    **User's Instruction:**
    {user_prompt}

    **Current Test Cases:**
    {test_cases_text}

    **Output Format Instructions:**
    - You MUST return the test cases in the same `===TEST CASE START===`...`===TEST CASE END===` format.
    - Do NOT return any text, explanations, or formatting outside of this format.
    - The returned text must contain all test cases, including those that were not changed.
    - If the user's instruction is unclear or cannot be applied, return the original, unchanged text that you were given.
    """

    try:
        response = gemini_model.generate_content(prompt)
        # Re-use the reliable text parser
        updated_test_cases = parse_ai_response_to_dicts(response.text)
        if updated_test_cases:
            return updated_test_cases
        else:
            print("    -> AI editor failed to return valid text format. Reverting changes.")
            return test_cases
    except Exception as e:
        print(f"    -> An error occurred during AI editing: {e}")
        return test_cases
