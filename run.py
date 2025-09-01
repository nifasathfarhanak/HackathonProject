
import sys
import os

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Now that the path is set, we can import the app and serve it
from app import app
from waitress import serve

if __name__ == '__main__':
    print("--- Starting production server with Waitress... ---")
    serve(app, host='0.0.0.0', port=5001)
