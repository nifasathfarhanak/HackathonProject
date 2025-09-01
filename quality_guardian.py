
import json
import re

# Import the new, single gemini_model instance from test_generator
from test_generator import gemini_model

# A set of all the keys we expect to be in a valid test case object
EXPECTED_KEYS = {
    "test_case_id",
    "requirement_id",
    "description",
    "test_type",
    "priority",
    "steps",
    "expected_result",
    "rtm_compliance_mapping"
}

def validate_structure(test_case: dict) -> tuple[bool, str]:
    """Checks if the test case dictionary has the correct structure and all required keys."""
    missing_keys = EXPECTED_KEYS - set(test_case.keys())
    if missing_keys:
        return False, f"Missing required keys: {', '.join(missing_keys)}"
    
    if not isinstance(test_case.get('steps'), list):
        return False, "'steps' field must be a list."

    return True, "Structure is valid."

def critique_plausibility(test_case: dict) -> tuple[bool, str]:
    """Uses a live AI call to check if the test case is logically plausible."""
    if not gemini_model:
        return True, "Plausibility check skipped: Vertex AI model not initialized."

    prompt = f"""As a QA Reviewer, analyze the following test case. Are the steps clear, logical, and easy to follow? Does the expected result directly test the objective in the description? Based on your analysis, is this a plausible and well-formed test case? Answer with only the word "Yes" or "No", followed by a brief one-sentence justification."""
    try:
        response = gemini_model.generate_content(prompt)
        critique = response.text.strip()
        if critique.lower().startswith('yes'):
            return True, critique
        else:
            return False, critique
    except Exception as e:
        print(f"  -> Plausibility check failed with error: {e}")
        return True, f"Plausibility check could not be performed due to an error: {e}" # Default to passing if the check fails

def validate_rtm_link(test_case: dict) -> tuple[bool, str]:
    """Uses a live AI call to validate the link between the test case and the compliance rule."""
    if not gemini_model:
        return True, "RTM validation skipped: Vertex AI model not initialized."

    prompt = f"""As a Compliance Auditor, analyze the following link between a test case and a compliance rule. Test Case Description: "{test_case.get('description')}". Compliance Rule Mapping: "{test_case.get('rtm_compliance_mapping')}". Is there a clear and logical connection between this test case and this compliance rule? Answer with only the word "Yes" or "No", followed by a brief one-sentence justification."""
    try:
        response = gemini_model.generate_content(prompt)
        validation_notes = response.text.strip()
        if validation_notes.lower().startswith('yes'):
            return True, validation_notes
        else:
            return False, validation_notes
    except Exception as e:
        print(f"  -> RTM validation failed with error: {e}")
        return True, f"RTM validation could not be performed due to an error: {e}" # Default to passing if the check fails

def run_quality_checks(test_cases: list) -> list:
    """Runs all quality checks on a list of test cases and adds quality metadata."""
    for tc in test_cases:
        tc['quality_assessment'] = {'passed': True, 'checks': []}

        struct_ok, struct_notes = validate_structure(tc)
        tc['quality_assessment']['checks'].append({'check': 'Structure', 'passed': struct_ok, 'notes': struct_notes})
        if not struct_ok:
            tc['quality_assessment']['passed'] = False
            continue # If structure is invalid, no point in running further checks

        plausibility_ok, plausibility_notes = critique_plausibility(tc)
        tc['quality_assessment']['checks'].append({'check': 'Plausibility', 'passed': plausibility_ok, 'notes': plausibility_notes})
        if not plausibility_ok:
            tc['quality_assessment']['passed'] = False

        rtm_ok, rtm_notes = validate_rtm_link(tc)
        tc['quality_assessment']['checks'].append({'check': 'RTM Validation', 'passed': rtm_ok, 'notes': rtm_notes})
        if not rtm_ok:
            tc['quality_assessment']['passed'] = False

    return test_cases
