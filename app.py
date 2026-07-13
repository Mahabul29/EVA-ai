"""
EvaAI Chat - Flask Application (Gemini API)
A beautiful AI chat web app with Google Gemini API integration
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import uuid
from datetime import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for all origins (required for Koyeb cross-origin access)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# In-memory conversation storage (use Redis/DB in production)
conversations = {}


def get_ai_response(message, conversation_history=None):
    """
    Get AI response from Google Gemini API
    Free tier: 1500 requests/day with Flash models
    Get API key: https://aistudio.google.com/app/apikey
    """
    api_key = app.config['GEMINI_API_KEY']
    model = app.config['GEMINI_MODEL']
    
    if not api_key:
        return "⚠️ Please set your GEMINI_API_KEY environment variable.\n\nGet a free API key from: https://aistudio.google.com/app/apikey"
    
    try:
        # Build conversation history for Gemini
        contents = []
        
        # Add system instruction
        contents.append({
            "role": "user",
            "parts": [{"text": "You are EvaAI, a helpful and friendly AI assistant. You provide clear, accurate, and engaging responses. You can help with coding, writing, analysis, explanations, and general conversation."}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Understood! I'm EvaAI, ready to help you with anything you need."}]
        })
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
        
        # Add current message
        contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })
        
        # Gemini API endpoint
        url = f"{app.config['GEMINI_API_URL']}{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract text from response
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    text_parts = [part["text"] for part in candidate["content"]["parts"] if "text" in part]
                    return "\n".join(text_parts).strip()
            
            return "I received a response but couldn't parse it properly."
            
        elif response.status_code == 429:
            return "⚠️ Rate limit exceeded. Gemini free tier allows 1500 requests/day. Please try again later or upgrade to paid tier."
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Bad request")
            return f"⚠️ API Error: {error_msg}"
        elif response.status_code == 403:
            return "⚠️ API key invalid or expired. Please check your GEMINI_API_KEY."
        else:
            return f"⚠️ API Error (Status {response.status_code}): {response.text[:200]}"
            
    except requests.exceptions.Timeout:
        return "The AI service is taking too long to respond. Please try again."
    except requests.exceptions.ConnectionError:
        return "Unable to connect to the AI service. Please check your internet connection."
    except Exception as e:
        return f"An error occurred: {str(e)}"


@app.route("/")
def index():
    """Render the main chat interface"""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat API endpoint
    Expects JSON: {"message": "user message", "conversation_id": "optional"}
    Returns JSON: {"response": "ai response", "conversation_id": "id"}
    """
    data = request.get_json()
    
    if not data or "message" not in data:
        return jsonify({"error": "Message is required"}), 400
    
    user_message = data["message"].strip()
    conversation_id = data.get("conversation_id", str(uuid.uuid4()))
    
    # Get or create conversation
    if conversation_id not in conversations:
        conversations[conversation_id] = []
    
    # Add user message to history
    conversations[conversation_id].append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Get AI response
    ai_response = get_ai_response(user_message, conversations[conversation_id])
    
    # Add AI response to history
    conversations[conversation_id].append({
        "role": "assistant",
        "content": ai_response,
        "timestamp": datetime.now().isoformat()
    })
    
    # Trim history if too long
    if len(conversations[conversation_id]) > app.config["MAX_HISTORY"] * 2:
        conversations[conversation_id] = conversations[conversation_id][-(app.config["MAX_HISTORY"] * 2):]
    
    return jsonify({
        "response": ai_response,
        "conversation_id": conversation_id,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """
    Streaming chat API endpoint for real-time responses
    """
    data = request.get_json()
    
    if not data or "message" not in data:
        return jsonify({"error": "Message is required"}), 400
    
    user_message = data["message"].strip()
    conversation_id = data.get("conversation_id", str(uuid.uuid4()))
    
    # Get AI response
    ai_response = get_ai_response(user_message, conversations.get(conversation_id, []))
    
    return jsonify({
        "response": ai_response,
        "conversation_id": conversation_id,
        "done": True
    })


@app.route("/api/history/<conversation_id>", methods=["GET"])
def get_history(conversation_id):
    """Get conversation history"""
    history = conversations.get(conversation_id, [])
    return jsonify({"history": history})


@app.route("/api/clear/<conversation_id>", methods=["POST"])
def clear_history(conversation_id):
    """Clear conversation history"""
    if conversation_id in conversations:
        conversations[conversation_id] = []
    return jsonify({"status": "cleared"})


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for Koyeb"""
    return jsonify({
        "status": "healthy",
        "service": "EvaAI Chat (Gemini)",
        "timestamp": datetime.now().isoformat()
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=app.config["PORT"],
        debug=app.config["DEBUG"]
    )
