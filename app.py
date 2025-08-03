import os
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import google.generativeai as genai
import re
import glob
import numpy as np

# --- Load Environment Variables ---
load_dotenv()

app = Flask(__name__, static_folder='.')

# --- Google AI Studio (Gemini) Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file or environment variables. Please get one from Google AI Studio.")

genai.configure(api_key=GOOGLE_API_KEY)

MODEL_NAME = "gemini-1.5-flash-latest" 
EMBEDDING_MODEL_NAME = "text-embedding-004" # This is the model name for embedding

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 60,
    "max_output_tokens": 1024,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Initialize the Gemini LLM model (for text generation)
gemini_model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
    safety_settings=safety_settings
)

# --- Embedding Helper Function ---
# This function now correctly calls genai.embed_content directly
def get_embedding(text):
    try:
        response = genai.embed_content( # CORRECTED: Call genai.embed_content directly
            model=EMBEDDING_MODEL_NAME,
            content=text
        )
        return np.array(response['embedding'])
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

# --- Vector Search Helper Function ---
def find_relevant_chunks(query_embedding, num_results=3):
    if not document_data or query_embedding is None:
        return []

    similarities = []
    for i, doc_chunk in enumerate(document_data):
        if doc_chunk['embedding'] is not None:
            # Calculate cosine similarity (dot product for normalized vectors)
            similarity = np.dot(query_embedding, doc_chunk['embedding'])
            similarities.append((similarity, doc_chunk['text']))
    
    similarities.sort(key=lambda x: x[0], reverse=True)
    
    return [text for score, text in similarities[:num_results]]


# --- Document Loading and Chunking (Server-Side) ---
DOCUMENT_DATA_PATH = 'data/'
document_data = [] # This will store a list of dictionaries: [{'text': 'chunk_text', 'embedding': numpy_array}]

def load_documents_on_startup():
    global document_data
    document_data = []

    all_raw_text = ""
    for filepath in glob.glob(os.path.join(DOCUMENT_DATA_PATH, '*.txt')):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_raw_text += f.read() + "\n\n"
        except Exception as e:
            print(f"Error loading document '{filepath}': {e}")
            continue
    
    if not all_raw_text.strip():
        print(f"No text documents found in '{DOCUMENT_DATA_PATH}' or documents are empty.")
        return

    paragraphs = [p.strip() for p in all_raw_text.split('\n\n') if p.strip()]
    
    final_chunks = []
    max_chunk_chars = 1000
    
    current_chunk_parts = []
    current_chunk_len = 0

    for paragraph in paragraphs:
        if current_chunk_len + len(paragraph) + len(current_chunk_parts) + 1 > max_chunk_chars:
            if current_chunk_parts:
                final_chunks.append("\n".join(current_chunk_parts))
            current_chunk_parts = [paragraph]
            current_chunk_len = len(paragraph)
        else:
            current_chunk_parts.append(paragraph)
            current_chunk_len += len(paragraph)
    
    if current_chunk_parts:
        final_chunks.append("\n".join(current_chunk_parts))

    print(f"Generated {len(final_chunks)} raw text chunks.")

    # Generate embeddings for each chunk
    for i, chunk_text in enumerate(final_chunks):
        try:
            response = genai.embed_content( # CORRECTED: Call genai.embed_content directly here too
                model=EMBEDDING_MODEL_NAME,
                content=chunk_text
            )
            chunk_embedding = np.array(response['embedding'])
            
            document_data.append({
                'text': chunk_text,
                'embedding': chunk_embedding
            })
            # print(f"Chunk {i+1}/{len(final_chunks)} embedded.") # Uncomment for verbose chunking
        except Exception as e:
            print(f"Error embedding chunk {i} ('{chunk_text[:50]}...'): {e}")
            continue
    
    print(f"Successfully loaded and embedded {len(document_data)} document chunks.")


# --- Call this function when the app starts ---
with app.app_context():
    load_documents_on_startup()


# --- Flask Routes ---

@app.route('/')
def index():
    return send_from_directory('.', 'Home.html')

@app.route('/<path:filename>')
def serve_static_files(filename):
    if '..' in filename or filename.startswith('/'):
        return "Forbidden", 403
    
    return send_from_directory('.', filename)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"response": "Error: No message provided."}), 400

    retrieved_context = []
    if document_data:
        user_query_embedding = get_embedding(user_message)
        if user_query_embedding is not None:
            retrieved_context = find_relevant_chunks(user_query_embedding, num_results=3)
            # print(f"Retrieved {len(retrieved_context)} relevant chunks.") # Uncomment for verbose retrieval

    context_prompt_part = ""
    if retrieved_context:
        combined_context = "\n---\n".join(retrieved_context)
        context_prompt_part = f"""
        **BACKGROUND INFORMATION (from documents):**
        {combined_context}

        ---

        **INSTRUCTIONS:**
        Based on the BACKGROUND INFORMATION provided above (if any), answer the following user question.
        - If the user's question can be directly answered *only* by the BACKGROUND INFORMATION, use only that information.
        - If the BACKGROUND INFORMATION does not contain the answer, or if the question is general and not directly related to the provided context, answer as a general-purpose AI.
        - If you are specifically asked for information that is explicitly stated as being in the BACKGROUND INFORMATION but is not found, clearly state that the information is not available in the provided document.
        """
    
    full_prompt = f"{context_prompt_part}\n\n**USER QUESTION:** {user_message}\n\n**AI RESPONSE:**"

    try:
        response = gemini_model.generate_content(full_prompt)
        ai_response = response.text

    except Exception as e:
        ai_response = f"Error communicating with AI. Please try again. (Details: {e})"
        print(f"Gemini API Error: {e}") 

    return jsonify({"response": ai_response})
  
if __name__ == '__main__':
    print("\n--- Flask Server Running ---")
    print(f"Access your site at: http://127.0.0.1:5000")
    print("To stop the server, press CTRL+C in this terminal.")
    print("---------------------------\n")
    app.run(debug=True, port=5000)