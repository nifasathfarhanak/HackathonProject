
import os
import json
import requests # New import for making HTTP requests
import base64 # New import for encoding credentials
from jira import JIRA

def format_rtm_for_jira(rtm):
    """Helper function to format the RTM field for the Jira description."""
    if not rtm:
        return 'N/A'
    if isinstance(rtm, str):
        return rtm
    if isinstance(rtm, dict):
        rule_id = rtm.get('rule_id', 'N/A')
        description = rtm.get('description')
        return f"{rule_id}: {description}" if description else rule_id
    if isinstance(rtm, list):
        return "\n".join([f"- {format_rtm_for_jira(item)}" for item in rtm])
    return str(rtm)

# --- NEW HELPER FUNCTION FOR ZEPHYR SCALE API ---
def create_zephyr_test_case(jira_server: str, zephyr_api_token: str, project_key: str, jira_issue_key: str, test_case_data: dict):
    """
    Creates a structured test case in Zephyr Scale via its REST API.
    This assumes a Jira issue (e.g., a Story) has already been created and linked.
    """
    zephyr_api_base_url = "https://api.zephyrscale.smartbear.com/v2" # Base URL for Zephyr Scale Cloud API
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {zephyr_api_token}" # Use Bearer token for JWT
    }

    # Format steps for Zephyr Scale API
    zephyr_steps = []
    for i, step_desc in enumerate(test_case_data.get('steps', [])):
        zephyr_steps.append({
            "step": step_desc,
            "testData": "", # Our current test case format doesn't have separate test data
            "expectedResult": test_case_data.get('expected_result', '') if i == len(test_case_data.get('steps', [])) - 1 else "" # Expected result usually goes with the last step
        })

    # Construct Zephyr Scale Test Case payload
    zephyr_payload = {
        "name": test_case_data.get('description', 'No description provided'),
        "projectKey": project_key,
        "jiraIssueKey": jira_issue_key, # Link to the Jira issue we just created
        "status": "Draft", # Default status
        "priority": test_case_data.get('priority', 'Normal'),
        "objective": test_case_data.get('description', 'No objective provided'),
        "precondition": "", # Our current format doesn't explicitly have preconditions
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": zephyr_steps
        },
        "labels": [test_case_data.get('test_type', 'Automated')],
        "customFields": {
            # Example: If you had a custom field in Zephyr Scale for RTM
            # "RTM Mapping": test_case_data.get('rtm_compliance_mapping', 'N/A')
        }
    }

    print(f"--- DEBUG: Zephyr Scale API Payload: {json.dumps(zephyr_payload, indent=2)}")

    try:
        response = requests.post(f"{zephyr_api_base_url}/testcases", headers=headers, data=json.dumps(zephyr_payload))
        response.raise_for_status() # Raise an exception for HTTP errors
        zephyr_response = response.json()
        print(f"--- DEBUG: Zephyr Scale API Response: {json.dumps(zephyr_response, indent=2)}")
        return zephyr_response.get('key') # Returns the Zephyr Test Case Key (e.g., SCRUM-T1)
    except requests.exceptions.RequestException as e:
        print(f"--- ERROR: Zephyr Scale API call failed: {e}")
        if response is not None:
            print(f"--- ERROR: Zephyr Scale API Response Text: {response.text}")
        raise # Re-raise the exception to be caught by the calling function

# --- MODIFIED create_jira_issues FUNCTION ---
def create_jira_issues(jira_server: str, jira_email: str, jira_token: str, project_key: str, test_cases: list, is_zephyr_api_integration: bool = False, zephyr_api_token: str = None):
    """
    Connects to Jira and creates issues. If is_zephyr_api_integration is True,
    it creates a Jira 'Story' and then a linked Zephyr Scale Test Case.
    """
    try:
        print(f"--- JIRA INTEGRATION: Connecting to {jira_server}... ---")
        jira_options = {'server': jira_server}
        jira = JIRA(options=jira_options, basic_auth=(jira_email, jira_token))
        jira.project(project_key)
        print("--- JIRA INTEGRATION: Connection successful. ---")
    except Exception as e:
        error_message = f"Error connecting to Jira or finding project '{project_key}'. Please check your Server URL, Email, API Token, and Project Key. Error: {e}"
        print(f"--- JIRA INTEGRATION: {error_message} ---")
        return [error_message]

    confirmations = []
    for test_case in test_cases:
        steps = test_case.get('steps', [])
        rtm_str = format_rtm_for_jira(test_case.get('rtm_compliance_mapping'))
        steps_str = "\n".join(f"# {step}" for step in steps) # Format steps for description

        # Prepare common description content
        description_content = f"""h3. Requirement ID
        {test_case.get('requirement_id', 'N/A')}

        h3. Test Type
        {test_case.get('test_type', 'N/A')}

        h3. Priority
        {test_case.get('priority', 'N/A')}

        h3. RTM Compliance Mapping
        {rtm_str}

        h3. Confidence Score
        {test_case.get('confidence_score', 'N/A')}

        -----

        h3. Steps to Reproduce
        {steps_str}

        -----

        h3. Expected Result
        {test_case.get('expected_result', 'N/A')}
        """

        jira_issue_key = None
        zephyr_test_case_key = None

        try:
            if is_zephyr_api_integration:
                if not zephyr_api_token:
                    error_message = "Error: Zephyr Scale API integration requires a Zephyr Scale API Token."
                    print(f"  - {error_message}")
                    confirmations.append(error_message)
                    continue

                # 1. Create a Jira issue (e.g., a Story) to link the Zephyr Test Case to
                jira_issue_dict = {
                    'project': {'key': project_key},
                    'summary': f"Test Case Container: {test_case.get('description', 'No description provided')}",
                    'description': description_content, # Full details in Jira description
                    'issuetype': {'name': 'Story'} # Use 'Story' as the container issue type
                }
                print(f"--- DEBUG: Creating Jira container issue (Story) for Zephyr: {jira_issue_dict['summary']}")
                new_jira_issue = jira.create_issue(fields=jira_issue_dict)
                jira_issue_key = new_jira_issue.key
                confirmations.append(f"Successfully created Jira container issue: {jira_issue_key}")

                # 2. Create the Zephyr Scale Test Case and link it to the Jira issue
                print(f"--- DEBUG: Attempting to create Zephyr Scale Test Case for Jira issue {jira_issue_key} ---")
                zephyr_test_case_key = create_zephyr_test_case(
                    jira_server=jira_server,
                    zephyr_api_token=zephyr_api_token,
                    project_key=project_key,
                    jira_issue_key=jira_issue_key,
                    test_case_data=test_case
                )
                if zephyr_test_case_key:
                    confirmations.append(f"Successfully created Zephyr Scale Test Case: {zephyr_test_case_key} linked to {jira_issue_key}")
                else:
                    confirmations.append(f"Failed to create Zephyr Scale Test Case for {jira_issue_key}")

            else:
                # Standard Jira issue creation (Task)
                issue_dict = {
                    'project': {'key': project_key},
                    'summary': test_case.get('description', 'No description provided'),
                    'description': description_content,
                    'issuetype': {'name': 'Task'}
                }
                print(f"--- DEBUG: Creating standard Jira issue with issuetype: {issue_dict['issuetype']['name']}")
                new_issue = jira.create_issue(fields=issue_dict)
                confirmations.append(f"Successfully created issue: {new_issue.key}")

        except Exception as e:
            error_message = f"Error creating issue for '{test_case.get('description', 'Unknown')[:30]}...'. Jira/Zephyr API Error: {e}"
            print(f"  - {error_message}")
            confirmations.append(error_message)

    return confirmations
