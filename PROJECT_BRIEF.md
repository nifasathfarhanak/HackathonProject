# Project Brief: AI-Powered Compliance-Aware Test Case Generation System (TCGS)

## 1. The Core Problem

In regulated industries like healthcare and finance, QA teams spend an enormous amount of time manually translating complex specification documents (PDFs, DOCX) into detailed test cases. This process is slow, error-prone, and creates a significant bottleneck in the development lifecycle. Furthermore, every test case must be meticulously justified and traced back to specific regulatory standards (e.g., IEC 62304, ISO 13485), which is a tedious and critical documentation task.

## 2. Our Solution: The TCGS Prototype

This prototype is an intelligent web application designed to automate and accelerate this entire process. It acts as a powerful assistant for QA engineers, autonomously generating high-quality, compliance-aware test cases directly from requirement documents. The system significantly reduces manual effort, ensures thoroughness, and embeds compliance directly into the testing workflow.

## 3. Key Features Implemented

- **Automated Document Ingestion:** The system accepts requirement documents in various standard formats, including **PDF, DOCX, XML, Markdown, and TXT**.
- **Intelligent, Compliance-Aware Test Case Generation:**
    - The system uses a **Retrieval-Augmented Generation (RAG)** architecture. It doesn't just read the requirement; it simultaneously searches a dedicated **compliance knowledge base** (your uploaded ISO, FDA, etc., standards) to find relevant rules.
    - The AI then generates test cases that are grounded in both the software requirement and the specific regulatory context.
- **Comprehensive Test Case Details (with RTM):** The AI generates a rich, structured set of data for each test case, including:
    - Test Case ID
    - Requirement ID
    - A detailed Description
    - Test Type (e.g., Functional, Security)
    - Priority (High, Medium, Low)
    - Step-by-Step Instructions
    - Expected Results
    - **RTM Compliance Mapping:** A crucial field that explicitly states which regulatory rule the test case is designed to verify, automating the creation of a Requirement Traceability Matrix.
- **Full Document Coverage:** The application intelligently breaks down large documents into smaller, meaningful chunks and generates test cases for each chunk, ensuring requirements from all parts of the document are covered.
- **Interactive Document Chatbot:** After processing a document, users can engage in a Q&A session with a chatbot that has "read" the document. This allows for quick clarification of requirements and exploration of the document's content in a conversational way.
- **Multi-Format Data Export:** Users can download the complete set of generated test cases in standard enterprise formats: **CSV, XLSX (Excel), PDF, and TXT**.
- **Enterprise ALM Integration (Ready):** The application is fully equipped with the UI and backend logic to connect to **Jira**. With live credentials, it can automatically create Jira issues from the generated test cases, including all the detailed fields and RTM information.

## 4. Technical Architecture

- **Frontend:** A **Flask-based web application**. We migrated from Streamlit to Flask to provide a more stable, standard server environment that resolved critical conflicts with Google Cloud's authentication libraries. The UI is built with standard HTML, CSS, and JavaScript.
- **Backend:** A **Python** server powered by the Flask framework, which provides API endpoints for file uploads, test generation, downloads, and the chatbot.
- **AI Core (A Hybrid Approach):**
    - **Knowledge Base & Search:** **Google Cloud Vertex AI Search** is used to create and search the compliance knowledge base (RAG). This uses robust `gcloud` authentication.
    - **AI Generation:** The **Google Gemini 1.5 Pro** model is used for the creative task of generating test cases and chat responses. This uses the simpler **Google AI (MakerSuite) API key** method to ensure compatibility and avoid the environment conflicts we discovered.
- **Supporting Modules:** The project is cleanly structured with dedicated Python modules for `document_parser`, `test_generator`, and `alm_integrator`.
