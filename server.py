from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    "https://68c96f6ee112d8a557177d0c--webchatbt.netlify.app",
    "https://webchatbt.netlify.app"
])

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

WEATHER_CODE_MAP = {
    "0": "clear night",
    "1": "sunny",
    "2": "partly cloudy night",
    "3": "partly cloudy",
    "5": "mist",
    "6": "fog",
    "7": "cloudy",
    "8": "overcast",
    "9": "light rain shower night",
    "10": "light rain shower",
    "11": "drizzle",
    "12": "light rain",
    "13": "heavy rain shower",
    "14": "heavy rain",
    "15": "torrential rain",
    "16": "sleet shower night",
    "17": "sleet shower",
    "18": "sleet",
    "19": "hail shower night",
    "20": "hail shower",
    "21": "hail",
    "22": "light snow shower night",
    "23": "light snow shower",
    "24": "light snow",
    "25": "heavy snow shower",
    "26": "heavy snow",
    "27": "thunder shower night",
    "28": "thunder shower",
    "29": "thunder"
}

conversation_history = []

@app.route("/")
def home():
    return jsonify({"message": "Chatbot API is running! Use /chat or /weather."})

def is_weather_query(message):
    weather_keywords = ["weather", "umbrella", "rain", "sunny", "snow", "cloudy", "forecast", "temperature"]
    message_lower = message.lower()
    if any(keyword in message_lower for keyword in weather_keywords):
        words = message_lower.split()
        if "in" in words:
            city_index = words.index("in") + 1
            if city_index < len(words):
                return True, words[city_index].capitalize()
        if words and words[-1] not in weather_keywords and words[-1] not in ["today", "tomorrow"]:
            return True, words[-1].capitalize()
        return True, None
    return False, None

def get_weather_data(city):
    api_key = os.getenv("METOFFICE_HUB_KEY")
    if not api_key:
        return None, "Met Office API key is missing"

    try:
        # Get locations
        location_url = f"https://api-metoffice.apiconnect.ibmcloud.com/metoffice/production/v0/sites?key={api_key}"
        response = requests.get(location_url)
        response.raise_for_status()
        locations = response.json()
        
        location_id = None
        for site in locations.get("sites", []):
            if site.get("name", "").lower() == city.lower():
                location_id = site.get("id")
                break

        if not location_id:
            return None, f"City '{city}' not found"

        # Get forecast
        forecast_url = f"https://api-metoffice.apiconnect.ibmcloud.com/metoffice/production/v0/forecasts/point/{location_id}?key={api_key}"
        response = requests.get(forecast_url)
        response.raise_for_status()
        data = response.json()

        # Get today's forecast (first location period)
        today_forecast = data.get("forecastPeriods", [{}])[0]
        location_periods = today_forecast.get("locationPeriods", [{}])[0]
        
        weather_code = location_periods.get("weatherType", "0")
        weather_description = WEATHER_CODE_MAP.get(weather_code, "unknown weather")
        temperature = location_periods.get("temperature", {}).get("value", 0)
        precipitation_prob = location_periods.get("precipitationProbability", {}).get("value", 0)
        timestamp = today_forecast.get("forecastPeriod", "")

        return {
            "city": city,
            "weather": weather_description,
            "temperature": temperature,
            "precipitation": precipitation_prob,
            "timestamp": timestamp
        }, None

    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"
    except (KeyError, IndexError) as e:
        return None, f"Error parsing response: {str(e)}"

@app.route("/chat", methods=["POST"])
def chat():
    global conversation_history
    data = request.json or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    is_weather, city = is_weather_query(user_message)
    weather_info = None
    weather_error = None

    if is_weather and city:
        weather_data, error = get_weather_data(city)
        if error:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": error})
            return jsonify({"response": error})
        weather_info = weather_data

    conversation_history.append({"role": "user", "content": user_message})
    if len(conversation_history) > 10:
        conversation_history = conversation_history[-10:]

    try:
        system_prompt = "You are a friendly, concise AI chatbot. For weather queries, provide practical advice (e.g., mention umbrellas for rain, sunscreen for sun) based on the provided weather data, and keep the tone conversational."
        if weather_info:
            system_prompt += f" Today's weather in {weather_info['city']} is {weather_info['weather']} with a temperature of {weather_info['temperature']}°C and {weather_info['precipitation']}% chance of precipitation."

        messages = [{"role": "system", "content": system_prompt}] + conversation_history
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        bot_message = completion.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": bot_message})
        return jsonify({"response": bot_message})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/weather", methods=["POST"])
def get_weather():
    city = request.json.get("city", "")
    weather_data, error = get_weather_data(city)
    if error:
        return jsonify({"error": error}), 400 if "not found" in error else 500
    return jsonify({
        "weather": weather_data["weather"],
        "temperature": weather_data["temperature"],
        "precipitation": weather_data["precipitation"],
        "timestamp": weather_data["timestamp"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
