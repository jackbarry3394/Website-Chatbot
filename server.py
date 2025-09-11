from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load API key from .env file

app = Flask(__name__)
CORS(app, origins=["https://68b5a4b4b03f1ce64346a451--webchatbt.netlify.app", "https://webchatbt.netlify.app"])  # Enable CORS for Netlify domains

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/")
def home():
    return jsonify({"message": "Chatbot API is running! Use /chat endpoint to send messages."})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

        conversation_history = [{"role": "user", "content": user_message}]

        if len(conversation_history) > 5: # Limit memory to 5 messages
            conversation_history.pop(0)

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI chatbot that provides clear and concise answers."},
                {"role": "user", "content": user_message}] + conversation_history
        )
        bot_message = completion["choices"][0]["message"]["content"]
        conversation_history.append({"role": "assistant", "content": bot_message})

        return jsonify({"response": bot_message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
