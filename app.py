import os
# ... existing imports ...
import re # For splitting text more intelligently
import glob # For finding files in a directory
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv # Used to load environment variables from .env file
import google.generativeai as genai # Google's library for Gemini API


# --- Load Environment Variables ---
load_dotenv() # This line loads variables from the .env file

app = Flask(__name__, static_folder='.') # Serve static files from current directory

# --- Google AI Studio (Gemini) Configuration ---
# Get API key from environment variables (loaded by dotenv)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    # This error will occur if GOOGLE_API_KEY is not set in your .env file
    raise ValueError("GOOGLE_API_KEY not found in .env file or environment variables. Please get one from Google AI Studio.")

# Configure the generative AI library with your API key
genai.configure(api_key=GOOGLE_API_KEY)

# Define the model to use and its generation parameters
# 'gemini-1.5-flash-latest' is generally faster and cheaper for chat
# 'gemini-1.5-pro-latest' is more capable for complex tasks
MODEL_NAME = "gemini-1.5-flash-latest" 

generation_config = {
    "temperature": 0.7, # Controls randomness. Lower = more deterministic, Higher = more creative
    "top_p": 0.95,      # Controls diversity of output via nucleus sampling
    "top_k": 60,        # Controls diversity of output via top-k sampling
    "max_output_tokens": 1024, # Maximum length of the AI's response
}

# Safety settings to block harmful content
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Initialize the Gemini model
gemini_model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
    safety_settings=safety_settings
)


# --- Document Loading and Chunking (Server-Side) ---
DOCUMENT_DATA_PATH = 'data/' # Folder where your .txt files are located
document_chunks = [] # This will store all chunks from pre-loaded documents

def load_documents_on_startup():
    global document_chunks
    all_text = ""
    # Find all .txt files in the specified data path
    for filepath in glob.glob(os.path.join(DOCUMENT_DATA_PATH, '*.txt')):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_text += f.read() + "\n\n" # Concatenate text from all files

        except Exception as e:
            print(f"Error loading document '{filepath}': {e}")
            continue
    
    if not all_text.strip(): # Check if any text was loaded
        print(f"No text documents found in '{DOCUMENT_DATA_PATH}' or documents are empty.")
        document_chunks = []
        return

    # Simple Chunking: Split by sentences or a reasonable delimiter
    # This is a very basic chunking. For better RAG, you'd use a more advanced text splitter.
    # Here we split by common sentence endings and then filter/clean.
    # You can adjust chunking strategy here.
    raw_chunks = re.split(r'[.!?\n]+', all_text) # Split by sentence endings or newlines
    
    # Further refine chunks if they are too long or too short, or just clean whitespace
    final_chunks = []
    max_chunk_size = 500 # Max characters per chunk (adjust based on LLM context window & chunking needs)
    for chunk in raw_chunks:
        cleaned_chunk = chunk.strip()
        if cleaned_chunk: # Ensure chunk is not empty
            # If a chunk is very long, you might need to split it further
            if len(cleaned_chunk) > max_chunk_size:
                # Simple split for oversized chunks
                sub_chunks = [cleaned_chunk[i:i + max_chunk_size] for i in range(0, len(cleaned_chunk), max_chunk_size)]
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(cleaned_chunk)
    
    document_chunks = final_chunks
    print(f"Loaded {len(document_chunks)} chunks from documents in '{DOCUMENT_DATA_PATH}'.")

# --- Call this function when the app starts ---
with app.app_context(): # Ensure we are in an app context for startup tasks
    load_documents_on_startup()

# --- Flask Routes ---



# Route to serve other HTML, CSS, JS, and image files directly
@app.route('/<path:filename>')
def serve_static_files(filename):
    # Basic security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Forbidden", 403
    
    # Determine the correct root based on the file type
    if filename.endswith('.html'):
        return send_from_directory('.', filename) # HTML files from root
    elif filename.startswith('css/') or filename.startswith('images/') or filename.startswith('js/'):
        # For files in subdirectories, correctly serve from their respective paths
        root_dir = os.path.join(app.root_path, os.path.dirname(filename))
        file_to_serve = os.path.basename(filename)
        return send_from_directory(root_dir, file_to_serve)
    else:
        # Fallback for any other file types that might be in the root
        return send_from_directory('.', filename)

# New route to handle chat messages
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"response": "Error: No message provided."}), 400

    # --- Construct Prompt with Document Context (RAG) ---
    context_prompt_part = ""
    if document_chunks:
        # Join all chunks to form the context.
        # IMPORTANT: For very large documents, this can exceed the LLM's context window.
        # In advanced RAG, you'd use embeddings to retrieve *only* the most relevant chunks here.
        full_document_context = "\n".join(document_chunks)
        context_prompt_part = f"""
        **BACKGROUND INFORMATION:**
        {full_document_context}

        ---

        **INSTRUCTIONS:**
        Based on the BACKGROUND INFORMATION provided above (if any), answer the following user question.
        - If the user's question can be directly answered by the BACKGROUND INFORMATION, use only that information.
        - If the BACKGROUND INFORMATION does not contain the answer, or if the question is general and not related to the provided context, answer as a general-purpose AI.
        - If you are asked to provide information that is not in the BACKGROUND INFORMATION, clearly state that the information is not available in the provided document.
        """

    # Combine context and user message into the final prompt for the LLM
    full_prompt = f"{context_prompt_part}\n\n**USER QUESTION:** {user_message}\n\n**AI RESPONSE:**"

    try:
        # Generate content using the Gemini model
        response = gemini_model.generate_content(full_prompt)
        ai_response = response.text

    except Exception as e:
        ai_response = f"Error communicating with AI. Please try again. (Details: {e})"
        print(f"Gemini API Error: {e}") 

    return jsonify({"response": ai_response})

if __name__ == '__main__':
    # Make sure your virtual environment is active before running this!
    print("\n--- Flask Server Running ---")
    print(f"Access your site at: http://127.0.0.1:5000")
    print("To stop the server, press CTRL+C in this terminal.")
    print("---------------------------\n")
    app.run(debug=True, port=5000) # debug=True allows auto-reloading on code changes