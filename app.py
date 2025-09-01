
import os
import json
import re
import io
import csv
import concurrent.futures
from flask import Flask, request, jsonify, render_template, send_file, session
from dotenv import load_dotenv
from openpyxl import Workbook
from fpdf import FPDF

# Load environment variables from .env file
load_dotenv()

# Corrected: Use direct, absolute imports as all files are now in the same directory
from document_parser import parse_document
from test_generator import generate_test_cases_from_chunk
from alm_integrator import create_jira_issues
from quality_guardian import run_quality_checks

# Initialize the Flask application
app = Flask(__name__, template_folder='templates', static_folder='../static')
app.secret_key = os.urandom(24)

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
    test_cases = generate_test_cases_from_chunk(chunk)
    if not test_cases:
        return [] # Return empty list if generation fails
    checked_test_cases = run_quality_checks(test_cases)
    return checked_test_cases

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
        return jsonify({'extracted_text': extracted_text, 'test_cases': all_test_cases})

    except Exception as e:
        print(f"Error during generation: {e}")
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
    try:
        confirmations = create_jira_issues(
            jira_server=data.get('server'),
            jira_email=data.get('email'),
            jira_token=data.get('token'),
            project_key=data.get('project_key'),
            test_cases=data.get('test_cases')
        )
        return jsonify({'confirmations': confirmations})
    except Exception as e: return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
