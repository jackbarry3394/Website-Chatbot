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

# Map Met Office DataHub weather codes to plain English
WEATHER_CODE_MAP = {
    "0": "clear night",
    "1": "sunny day",
    "2": "partly cloudy night",
    "3": "partly cloudy day",
    "5": "mist",
    "6": "fog",
    "7": "cloudy",
    "8": "overcast",
    "9": "light rain shower night",
    "10": "light rain shower day",
    "11": "drizzle",
    "12": "light rain",
    "13": "heavy rain shower night",
    "14": "heavy rain shower day",
    "15": "torrential rain",
    "16": "sleet shower night",
    "17": "sleet shower day",
    "18": "sleet",
    "19": "hail shower night",
    "20": "hail shower day",
    "21": "hail",
    "22": "light snow shower night",
    "23": "light snow shower day",
    "24": "light snow",
    "25": "heavy snow shower night",
    "26": "heavy snow shower day",
    "27": "thunder shower night",
    "28": "thunder shower day",
    "29": "thunder"
}

conversation_history = []

@app.route("/")
def home():
    return jsonify({"message": "Met Office Chatbot API is running! Use /chat or /weather."})

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

def get_city_coordinates(city):
    """Get lat/lon for UK city using free Nominatim API."""
    url = f"https://nominatim.openstreetmap.org/search?q={city},UK&format=json&limit=1&countrycodes=gb"
    try:
        response = requests.get(url, headers={"User-Agent": "WeatherBot/1.0"})
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None, None
    except Exception:
        return None, None

def get_weather_data(city):
    """Get weather from Met Office DataHub Global Spot Forecast API."""
    api_key = os.getenv("METOFFICE_HUB_KEY")
    if not api_key:
        return None, "Met Office API key is missing"

    lat, lon = get_city_coordinates(city)
    if lat is None or lon is None:
        return None, f"Could not find '{city}' in the UK"

    headers = {"Ocp-Apim-Subscription-Key": api_key}

    try:
        url = f"https://api-metoffice.apiconnect.ibmcloud.com/metoffice/production/v0/forecasts/point?lat={lat}&lon={lon}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Parse GeoJSON response (featureCollection > features[0] > properties > timeSeries[0] > forecast)
        feature_collection = data.get("featureCollection", {})
        features = feature_collection.get("features", [])
        if not features:
            return None, "No forecast data available"

        first_feature = features[0]
        properties = first_feature.get("properties", {})
        time_series = properties.get("timeSeries", [])
        if not time_series:
            return None, "No time series data"

        first_time_series = time_series[0]
        forecast = first_time_series.get("forecast", {})
        weather_code = str(forecast.get("weatherType", "0"))
        weather_description = WEATHER_CODE_MAP.get(weather_code, "unknown weather")
        temperature = forecast.get("temperature", {}).get("value", 0)
        precipitation_prob = forecast.get("precipitationProbability", {}).get("value", 0)
        timestamp = first_time_series.get("forecastPeriod", "")

        return {
            "city": city,
            "weather": weather_description,
            "temperature": temperature,
            "precipitation": precipitation_prob,
            "timestamp": timestamp
        }, None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return None, "Invalid Met Office API key"
        elif e.response.status_code == 404:
            return None, f"Forecast not available for '{city}'"
        return None, f"API error: {e.response.status_code}"
    except Exception as e:
        return None, f"Error: {str(e)}"

@app.route("/chat", methods=["POST"])
def chat():
    global conversation_history
    data = request.json or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    is_weather, city = is_weather_query(user_message)
    weather_info = None

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
        return jsonify({"error": error}), 400 if "not found" in error.lower() else 500
    return jsonify({
        "weather": weather_data["weather"],
        "temperature": weather_data["temperature"],
        "precipitation": weather_data["precipitation"],
        "timestamp": weather_data["timestamp"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
