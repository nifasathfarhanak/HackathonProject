
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = "tcgs-new-project-2025"
VERTEX_LOCATION = "us-central1"

print(f"--- Initializing Vertex AI for project {PROJECT_ID} in {VERTEX_LOCATION} ---")

try:
    vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)
    print("--- Vertex AI Initialized Successfully ---")
except Exception as e:
    print(f"CRITICAL FAILURE: Could not initialize Vertex AI. Error: {e}")
    exit()

print("\n--- Checking for available models ---")

# Test for Gemini 1.0 Pro
try:
    model_1_0 = GenerativeModel("gemini-1.0-pro")
    print("✅ SUCCESS: Your project has access to 'gemini-1.0-pro'.")
except Exception as e:
    print("❌ FAILED: Your project does NOT have access to 'gemini-1.0-pro'.")
    print(f"   Error: {e}")

# Test for Gemini 1.5 Pro
try:
    model_1_5 = GenerativeModel("gemini-1.5-pro")
    print("✅ SUCCESS: Your project has access to 'gemini-1.5-pro'.")
except Exception as e:
    print("❌ FAILED: Your project does NOT have access to 'gemini-1.5-pro'.")
    print(f"   Error: {e}")

