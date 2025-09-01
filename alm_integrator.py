
import os
import json
from jira import JIRA

def format_rtm_for_jira(rtm):
    """Helper function to format the RTM field for the Jira description."""
    if not rtm:
        return 'N/A'
    if isinstance(rtm, str):
        return rtm
    if isinstance(rtm, dict):
        # Format as "ID: Description" if possible, otherwise just show the ID
        rule_id = rtm.get('rule_id', 'N/A')
        description = rtm.get('description')
        return f"{rule_id}: {description}" if description else rule_id
    if isinstance(rtm, list):
        # Format each item in the list on a new line for readability
        return "\n".join([f"- {format_rtm_for_jira(item)}" for item in rtm])
    return str(rtm)

def create_jira_issues(jira_server: str, jira_email: str, jira_token: str, project_key: str, test_cases: list):
    """
    Connects to Jira and creates test case issues with enhanced details including RTM.
    """

    try:
        print(f"--- JIRA INTEGRATION: Connecting to {jira_server}... ---")
        jira_options = {'server': jira_server}
        jira = JIRA(options=jira_options, basic_auth=(jira_email, jira_token))
        # Verify connection by trying to get project details
        jira.project(project_key)
        print("--- JIRA INTEGRATION: Connection successful. ---")
    except Exception as e:
        error_message = f"Error connecting to Jira or finding project '{project_key}'. Please check your Server URL, Email, API Token, and Project Key. Error: {e}"
        print(f"--- JIRA INTEGRATION: {error_message} ---")
        return [error_message]

    confirmations = []
    for test_case in test_cases:
        steps_str = "\n".join(f"# {step}" for step in test_case.get('steps', []))
        rtm_str = format_rtm_for_jira(test_case.get('rtm_compliance_mapping'))

        # Using Jira's rich text formatting (markup)
        description_str = f"""h3. Requirement ID
        {test_case.get('requirement_id', 'N/A')}

        h3. Test Type
        {test_case.get('test_type', 'N/A')}

        h3. Priority
        {test_case.get('priority', 'N/A')}

        h3. RTM Compliance Mapping
        {rtm_str}

        -----

        h3. Steps to Reproduce
        {steps_str}

        -----

        h3. Expected Result
        {test_case.get('expected_result', 'N/A')}
        """

        issue_dict = {
            'project': {'key': project_key},
            'summary': test_case.get('description', 'No description provided'),
            'description': description_str,
            'issuetype': {'name': 'Task'} # Ensure this issue type exists in your project
        }

        try:
            print(f"  - Creating Jira issue for: {issue_dict['summary']}")
            new_issue = jira.create_issue(fields=issue_dict)
            confirmations.append(f"Successfully created issue: {new_issue.key}")
        except Exception as e:
            error_message = f"Error creating issue for '{issue_dict['summary'][:30]}...': {e}"
            print(f"  - {error_message}")
            confirmations.append(error_message)

    return confirmations
