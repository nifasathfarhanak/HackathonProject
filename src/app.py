
import os
import json
import re
import io
import csv
import concurrent.futures
import time # Added for retry mechanism
from flask import Flask, request, jsonify, render_template, send_file, session
from dotenv import load_dotenv
from openpyxl import Workbook
from fpdf import FPDF

import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables from .env file
load_dotenv()

# Corrected: Use absolute imports as 'src' is on the path
from document_parser import parse_document
# Corrected: Import the new simplified function
from test_generator import generate_test_cases_from_chunk, edit_test_cases_with_ai
from alm_integrator import create_jira_issues # Keep this import
from quality_guardian import run_quality_checks # Re-enable quality checks

# Initialize the Flask application
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.urandom(24)

# Initialize Firebase
try:
    firebase_credentials_path = os.getenv('FIREBASE_CREDENTIALS')
    print(f"DEBUG: FIREBASE_CREDENTIALS path from .env: {firebase_credentials_path}")
    
    # Fallback to local serviceAccountKey.json if env var not set or path invalid
    if not firebase_credentials_path or not os.path.exists(firebase_credentials_path):
        print("DEBUG: FIREBASE_CREDENTIALS env var not set or path invalid. Checking for config/serviceAccountKey.json...")
        local_credentials_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'serviceAccountKey.json')
        if os.path.exists(local_credentials_path):
            firebase_credentials_path = local_credentials_path
            print(f"DEBUG: Using local serviceAccountKey.json at: {firebase_credentials_path}")
        else:
            print("DEBUG: config/serviceAccountKey.json not found either.")

    if firebase_credentials_path and os.path.exists(firebase_credentials_path):
        cred = credentials.Certificate(firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully.")
    else:
        print("Firebase credentials not found or path is incorrect. Firebase will not be used.")
        db = None
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    db = None

document_cache = {}

# --- Helper Functions for File Generation (Accepting headers) ---

def format_rtm_for_export(rtm):
    if not rtm: return 'N/A'
    if isinstance(rtm, str): return rtm
    if isinstance(rtm, dict): return rtm.get('rule_id', json.dumps(rtm))
    if isinstance(rtm, list): return ', '.join([format_rtm_for_export(item) for item in rtm])
    return str(rtm)

def create_csv(test_cases, headers):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for tc in test_cases:
        row = []
        for header in headers:
            if header == 'steps':
                row.append("\n".join(tc.get('steps', [])))
            elif header == 'rtm_compliance_mapping':
                row.append(format_rtm_for_export(tc.get('rtm_compliance_mapping')))
            else:
                row.append(tc.get(header, 'N/A'))
        writer.writerow(row)
    return io.BytesIO(output.getvalue().encode('utf-8'))

def create_xlsx(test_cases, headers):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Test Cases"
    sheet.append(headers)
    for tc in test_cases:
        row = []
        for header in headers:
            if header == 'steps':
                row.append("\n".join(tc.get('steps', [])))
            elif header == 'rtm_compliance_mapping':
                row.append(format_rtm_for_export(tc.get('rtm_compliance_mapping')))
            else:
                row.append(tc.get(header, 'N/A'))
        sheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return output

def create_pdf(test_cases, headers):
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", size=8)
    col_widths = [20, 25, 50, 20, 20, 50, 50, 50] # Adjusted widths
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header.replace('_', ' ').title(), 1)
    pdf.ln()
    for tc in test_cases:
        row = []
        for header in headers:
            if header == 'steps':
                row.append("\n".join(tc.get('steps', [])))
            elif header == 'rtm_compliance_mapping':
                row.append(format_rtm_for_export(tc.get('rtm_compliance_mapping')))
            else:
                row.append(str(tc.get(header, 'N/A')))
        
        y_before = pdf.get_y()
        max_height = 0
        for i, item in enumerate(row):
            pdf.set_font("Arial", size=8)
            num_lines = len(pdf.multi_cell(col_widths[i], 5, item, split_only=True))
            cell_height = num_lines * 5
            if cell_height > max_height:
                max_height = cell_height

        pdf.set_y(y_before)
        for i, item in enumerate(row):
            pdf.multi_cell(col_widths[i], max_height, item, border=1, align='L')
            if i < len(row) - 1:
                pdf.set_y(y_before)
                pdf.set_x(pdf.get_x() + col_widths[i])
        pdf.ln(max_height)

    output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    return output

def create_txt(test_cases, headers):
    output = io.StringIO()
    for tc in test_cases:
        for header in headers:
            if header == 'steps':
                steps = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(tc.get('steps', []))])
                output.write(f"Steps:\n{steps}\n")
            elif header == 'rtm_compliance_mapping':
                rtm = format_rtm_for_export(tc.get('rtm_compliance_mapping'))
                output.write(f"RTM Compliance Mapping: {rtm}\n")
            else:
                output.write(f"{header.replace('_', ' ').title()}: {tc.get(header, 'N/A')}\n")
        output.write("-" * 30 + "\n")
    return io.BytesIO(output.getvalue().encode('utf-8'))

# New helper function for the fully parallel pipeline
def generate_and_check(chunk):
    """A single task that generates test cases from a chunk and runs quality checks."""
    retries = 3
    delay = 2 # seconds
    for i in range(retries):
        try:
            test_cases = generate_test_cases_from_chunk(chunk)
            if not test_cases:
                return [] # Return empty list if generation fails
            checked_test_cases = run_quality_checks(test_cases) # Re-enable quality checks
            return checked_test_cases
        except Exception as e:
            print(f"Attempt {i+1}/{retries} failed for chunk. Error: {e}")
            if i < retries - 1:
                time.sleep(delay)
                delay *= 2 # Exponential backoff
            else:
                print(f"All {retries} attempts failed for chunk. Skipping this chunk.")
                return [] # Return empty if all retries fail

def save_test_cases_to_firebase(user_id, test_cases):
    print(f"DEBUG: Entering save_test_cases_to_firebase for user_id: {user_id}, with {len(test_cases)} test cases.")
    if not db:
        print("DEBUG: Firebase db object is None. Cannot save test cases.")
        return ["Firebase not initialized. Cannot save test cases."]
    
    confirmations = []
    try:
        doc_ref = db.collection('users').document(user_id).collection('test_case_history').document()
        doc_ref.set({
            'timestamp': firestore.SERVER_TIMESTAMP,
            'test_cases': test_cases
        })
        confirmations.append(f"Test cases saved to Firebase with ID: {doc_ref.id}")
        print(f"DEBUG: Successfully saved to Firebase: {doc_ref.id}")
    except Exception as e:
        confirmations.append(f"Error saving to Firebase: {e}")
        print(f"DEBUG: Error saving to Firebase: {e}")
    return confirmations

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = os.urandom(16).hex()
    return render_template('index.html')

@app.route('/generate_and_analyze', methods=['POST'])
def handle_generate_and_analyze():
    if 'user_id' not in session: return jsonify({'error': 'Session expired'}), 400
    if 'requirement_file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file = request.files['requirement_file']
    if file.filename == '': return jsonify({'error': 'No selected file'}), 400
    
    raw_save_to_firebase_value = request.form.get('save_to_firebase')
    print(f"DEBUG: Raw save_to_firebase value from request.form: {raw_save_to_firebase_value}")
    # Correctly interpret 'on' from checkbox as True, and None (if unchecked) as False
    save_to_firebase = bool(raw_save_to_firebase_value)
    print(f"DEBUG: save_to_firebase flag after conversion: {save_to_firebase}")
    firebase_confirmations = []

    try:
        file_content = file.read()
        text_chunks = parse_document(file.filename, file_content)
        
        extracted_text = "\n\n".join(text_chunks)
        document_cache[session['user_id']] = extracted_text
        
        print(f"--- Found {len(text_chunks)} chunks. Processing in parallel... ---")

        all_test_cases = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_chunk = {executor.submit(generate_and_check, chunk): chunk for chunk in text_chunks}
            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    checked_test_cases = future.result()
                    if checked_test_cases:
                        all_test_cases.extend(checked_test_cases)
                except Exception as exc:
                    print(f"A chunk processing task failed with an exception: {exc}")

        if not all_test_cases:
            return jsonify({'error': 'The AI did not generate any valid test cases.'}), 500

        print("--- All processing complete. ---")

        if save_to_firebase:
            print("DEBUG: Calling save_test_cases_to_firebase from handle_generate_and_analyze.")
            firebase_confirmations = save_test_cases_to_firebase(session['user_id'], all_test_cases)

        response_data = {'extracted_text': extracted_text, 'test_cases': all_test_cases}
        if firebase_confirmations:
            response_data['firebase_confirmations'] = firebase_confirmations
        
        # --- Automatic Jira Export ---
        jira_confirmations = None
        jira_error = None
        if request.form.get('jira_auto_export'):
            jira_server = request.form.get('jira_server')
            jira_email = request.form.get('jira_email')
            jira_token = request.form.get('jira_token')
            jira_project_key = request.form.get('jira_project_key')
            is_zephyr_api_integration = request.form.get('is_zephyr_api_integration') == 'true' # Get Zephyr API integration flag
            zephyr_api_token = request.form.get('zephyr_api_token') # Get Zephyr API Token

            print(f"--- DEBUG: Jira Auto-Export Request ---\n  Server: {jira_server}\n  Email: {jira_email}\n  Project Key: {jira_project_key}\n  Is Zephyr API Integration: {is_zephyr_api_integration}\n  Zephyr API Token: {'*' * len(zephyr_api_token) if zephyr_api_token else 'N/A'}")

            if jira_server and jira_email and jira_token and jira_project_key:
                try:
                    print("--- Attempting automatic Jira export... ---")
                    jira_confirmations = create_jira_issues(
                        jira_server=jira_server,
                        jira_email=jira_email,
                        jira_token=jira_token,
                        project_key=jira_project_key,
                        test_cases=all_test_cases,
                        is_zephyr_api_integration=is_zephyr_api_integration, # Pass the Zephyr API integration flag
                        zephyr_api_token=zephyr_api_token # Pass the Zephyr API Token
                    )
                except Exception as e:
                    print(f"Error during automatic Jira export: {e}")
                    jira_error = str(e)
            else:
                jira_error = "One or more Jira configuration fields were missing."

        if jira_confirmations:
            response_data['jira_confirmations'] = jira_confirmations
        if jira_error:
            response_data['jira_error'] = jira_error

        return jsonify(response_data)


    except Exception as e:
        print(f"Error during generation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/edit_test_cases', methods=['POST'])
def handle_edit_test_cases():
    data = request.get_json()
    user_prompt = data.get('prompt')
    test_cases = data.get('test_cases')

    if not user_prompt or not test_cases:
        return jsonify({'error': 'A prompt and a list of test cases are required.'}), 400

    try:
        updated_test_cases = edit_test_cases_with_ai(user_prompt, test_cases)
        return jsonify({'test_cases': updated_test_cases})
    except Exception as e:
        print(f"Error during test case editing: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def handle_download():
    HEADERS = ['test_case_id', 'requirement_id', 'description', 'test_type', 'priority', 'rtm_compliance_mapping', 'steps', 'expected_result']
    format = request.args.get('format', 'txt')
    data = request.get_json()
    test_cases = data.get('test_cases', [])

    if not test_cases: return jsonify({'error': 'No test cases to download'}), 400
    file_generators = {'csv': create_csv, 'xlsx': create_xlsx, 'pdf': create_pdf, 'txt': create_txt}
    generator = file_generators.get(format)
    if not generator: return jsonify({'error': 'Invalid format'}), 400
    try:
        file_buffer = generator(test_cases, HEADERS)
        return send_file(file_buffer, as_attachment=True, download_name=f'test-cases.{format}', mimetype=f'application/{format}')
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/export_to_jira', methods=['POST'])
def handle_export_to_jira():
    data = request.get_json()
    
    save_to_firebase = data.get('save_to_firebase')
    firebase_confirmations = []

    print(f"DEBUG: handle_export_to_jira - save_to_firebase flag: {save_to_firebase}")

    try:
        # Get Zephyr flag from manual export form
        is_zephyr_api_integration = data.get('is_zephyr_api_integration', False)
        zephyr_api_token = data.get('zephyr_api_token') # Get Zephyr API Token

        print(f"--- DEBUG: Manual Jira Export Request ---\n  Is Zephyr API Integration: {is_zephyr_api_integration}\n  Zephyr API Token: {'*' * len(zephyr_api_token) if zephyr_api_token else 'N/A'}")

        confirmations = create_jira_issues(
            jira_server=data.get('server'),
            jira_email=data.get('email'),
            jira_token=data.get('token'),
            project_key=data.get('project_key'),
            test_cases=data.get('test_cases'),
            is_zephyr_api_integration=is_zephyr_api_integration, # Pass the Zephyr API integration flag
            zephyr_api_token=zephyr_api_token # Pass the Zephyr API Token
        )
        
        if save_to_firebase:
            print("DEBUG: Calling save_test_cases_to_firebase from handle_export_to_jira.")
            firebase_confirmations = save_test_cases_to_firebase(session['user_id'], data.get('test_cases'))

        response_data = {'confirmations': confirmations}
        if firebase_confirmations:
            response_data['firebase_confirmations'] = firebase_confirmations

        return jsonify(response_data)
    except Exception as e: return jsonify({'error': str(e)}), 500

# The if __name__ == '__main__' block is now removed from this file.
# The application should only be run via run.py
