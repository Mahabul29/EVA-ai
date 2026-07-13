"""
EvaAI Chat - Flask Application
A beautiful AI chat web app with API integration
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
    Get AI response from Pollinations AI API (free, no key required)
    Falls back to a local response if API fails
    """
    try:
        # Build context from conversation history
        context = ""
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                role = "User" if msg["role"] == "user" else "Assistant"
                context += f"{role}: {msg['content']}\n"
        
        # Pollinations AI - Free, no API key needed
        prompt = message
        if context:
            prompt = f"Previous conversation:\n{context}\n\nUser: {message}\nAssistant:"
        
        url = f"{app.config['AI_API_URL']}{requests.utils.quote(prompt)}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.text.strip()
        else:
            return f"I'm having trouble connecting right now. Status: {response.status_code}"
            
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
        "service": "EvaAI Chat",
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
