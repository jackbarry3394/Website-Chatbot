from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()  # Load API key from .env file

app = Flask(__name__)
# Updated CORS to include the new Netlify subdomain and wildcard for previews
CORS(app, origins=[
    "https://68c96f6ee112d8a557177d0c--webchatbt.netlify.app",  # Your current frontend origin
    "https://webchatbt.netlify.app"  # Main domain
    #"https://*.--webchatbt.netlify.app"  # Wildcard for Netlify preview subdomains (e.g., random-id--webchatbt.netlify.app)
])

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Global conversation history (in production, use a database)
conversation_history = []

def register_routes(app):  # Function to register routes with the app
    @app.route("/weather", methods=["POST"])
    def get_weather():
        city = request.json.get("city", "")
        api_key = "eyJ4NXQjUzI1NiI6Ik5XVTVZakUxTkRjeVl6a3hZbUl4TkdSaFpqSmpOV1l6T1dGaE9XWXpNMk0yTWpRek5USm1OVEE0TXpOaU9EaG1NVFJqWVdNellXUm1ZalUyTTJJeVpBPT0iLCJraWQiOiJnYXRld2F5X2NlcnRpZmljYXRlX2FsaWFzIiwidHlwIjoiSldUIiwiYWxnIjoiUlMyNTYifQ==.eyJzdWIiOiJqYWNrYmFycnkzMzk0QGdtYWlsLmNvbUBjYXJib24uc3VwZXIiLCJhcHBsaWNhdGlvbiI6eyJvd25lciI6ImphY2tiYXJyeTMzOTRAZ21haWwuY29tIiwidGllclF1b3RhVHlwZSI6bnVsbCwidGllciI6IlVubGltaXRlZCIsIm5hbWUiOiJzaXRlX3NwZWNpZmljLWMyNTJjMWQxLWQ1YzYtNDY1YS05NDY2LTQ2ZGJlYWVlMTZkMSIsImlkIjoyNTU5NywidXVpZCI6IjY2YjEzOWQ3LWQ2ZjItNDAxNS1hZmVlLWZjMWMzYzk4OWI5YyJ9LCJpc3MiOiJodHRwczpcL1wvYXBpLW1hbmFnZXIuYXBpLW1hbmFnZW1lbnQubWV0b2ZmaWNlLmNsb3VkOjQ0M1wvb2F1dGgyXC90b2tlbiIsInRpZXJJbmZvIjp7IndkaF9zaXRlX3NwZWNpZmljX2ZyZWUiOnsidGllclF1b3RhVHlwZSI6InJlcXVlc3RDb3VudCIsImdyYXBoUUxNYXhDb21wbGV4aXR5IjowLCJncmFwaFFMTWF4RGVwdGgiOjAsInN0b3BPblF1b3RhUmVhY2giOnRydWUsInNwaWtlQXJyZXN0TGltaXQiOjAsInNwaWtlQXJyZXN0VW5pdCI6InNlYyJ9fSwia2V5dHlwZSI6IlBST0RVQ1RJT04iLCJzdWJzY3JpYmVkQVBJcyI6W3sic3Vic2NyaWJlclRlbmFudERvbWFpbiI6ImNhcmJvbi5zdXBlciIsIm5hbWUiOiJTaXRlU3BlY2lmaWNGb3JlY2FzdCIsImNvbnRleHQiOiJcL3NpdGVzcGVjaWZpY1wvdjAiLCJwdWJsaXNoZXIiOiJKYWd1YXJfQ0kiLCJ2ZXJzaW9uIjoidjAiLCJzdWJzY3JpcHRpb25UaWVyIjoid2RoX3NpdGVfc3BlY2lmaWNfZnJlZSJ9XSwidG9rZW5fdHlwZSI6ImFwaUtleSIsImlhdCI6MTc1ODI1NDQ3OCwianRpIjoiOWE4MTY0NTItZWU3Mi00MWJjLWJjYTEtNTk0MTRmYWZjNTlkIn0=.Y0lH4WVYNYZi4s1pHLcr5lfs_aN88RGt2s03r1uYif0zFU_EJLAQioOLHMnKPRKYmrTjOt2reoTFmV874wuQKvL3uNCISYWgRQckCXV0oLmXw4n0GS8PSA7fM-fMHP_Ir8EMJsp4HMPQCFzNuyP9HOpw0frn5RVvxJwynW-c0opJx1aIRCv0Tivrbjrd6yq4Jtyba6RNVYZfG2CF5pH3R4ZKWv9jxMi9dNvvrofZwwU1tiUy4eS3vznpEQG1Iq-AwUMaQb9iDLQu1FP4xqeR0my7QgdBmuOHuPQSKgxm0vt_d5VHOI_rVO4moHqazMg6oVZ3ay5i2gCog4qfrLmDBA=="  # Replace with your Met Office API key

        if not city:
            return jsonify({"error": "City is required"}), 400

        url = f"http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/sitelist?key={api_key}"

        try:
            response = requests.get(url)
            response.raise_for_status()
            locations = response.json()

            location_id = None
            for location in locations.get("Locations", {}).get("Location", []):
                if location["name"].lower() == city.lower():
                    location_id = location["id"]
                    break

            if not location_id:
                return jsonify({"error": f"City '{city}' not found"}), 404

            weather_url = f"http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/{location_id}?res=3hourly&key={api_key}"
            response = requests.get(weather_url)
            response.raise_for_status()
            data = response.json()

            latest_period = data["SiteRep"]["DV"]["Location"]["Period"][0]["Rep"][0]
            weather = latest_period["W"]  # Weather type code
            temperature = latest_period["T"]  # Temperature in Celsius

            return jsonify({"weather": weather, "temperature": temperature})

        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Request failed: {str(e)}"}), 500
        except (KeyError, IndexError) as e:
            return jsonify({"error": f"Error parsing response: {str(e)}"}), 500

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


