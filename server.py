from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load API key from .env file

app = Flask(__name__)
# Updated CORS to include the new Netlify subdomain and wildcard for previews
CORS(app, origins=[
    "https://68c96f6ee112d8a557177d0c--webchatbt.netlify.app",  # Your current frontend origin
    "https://webchatbt.netlify.app",  # Main domain
    "https://*.--webchatbt.netlify.app"  # Wildcard for Netlify preview subdomains (e.g., random-id--webchatbt.netlify.app)
])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global conversation history (in production, use a database)
conversation_history = []

@app.route("/")
def home():
    return jsonify({"message": "Chatbot API is running! Use /chat endpoint to send messages."})

@app.route("/chat", methods=["POST"])
def chat():
    global conversation_history
    data = request.json or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # Add user message to conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    # Limit memory to 10 messages (5 exchanges)
    if len(conversation_history) > 10:
        conversation_history = conversation_history[-10:]

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI chatbot that provides clear and concise answers."}
            ] + conversation_history
        )
        bot_message = completion.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": bot_message})

        return jsonify({"response": bot_message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
