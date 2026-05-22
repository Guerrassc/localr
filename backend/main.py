import os
import requests
import json
from flask import Flask, render_template, request
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = Flask(__name__, template_folder="../templates", static_folder="../static")

def search_reddit(city, mood):
    query = f"{city} hidden gems {mood} things to do site:reddit.com"
    url = "https://www.google.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    }
    params = {"q": query, "num": 10}
    response = requests.get(url, headers=headers, params=params)
    soup = BeautifulSoup(response.text, "html.parser")
    texts = [p.get_text() for p in soup.find_all("div", class_="BNeawe")]
    return " ".join(texts[:20])

def ask_groq(content, city, mood):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""You are a local travel expert. Based on the following content about {city}, 
extract exactly 5 specific activity recommendations that match a '{mood}' experience.

Return ONLY a JSON array with exactly 5 objects. Each object must have:
- "name": name of the place or activity
- "summary": one sentence description
- "quote": a realistic quote someone might say about this place
- "score": a number between 50 and 500 representing how often it's mentioned online

Example format:
[
  {{
    "name": "LX Factory",
    "summary": "A creative hub in a repurposed industrial space with food, art and markets.",
    "quote": "honestly one of the coolest spots in lisbon, go on a sunday",
    "score": 342
  }}
]

Content: {content[:3000]}

Return only the JSON array, nothing else."""

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"]

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    city = request.form.get("city")
    mood = request.form.get("mood")
    raw = search_reddit(city, mood)
    recommendations_raw = ask_groq(raw, city, mood)

    try:
        recommendations = json.loads(recommendations_raw)
    except:
        recommendations = []

    return render_template("results.html", city=city, mood=mood, recommendations=recommendations)

def get_place_details(name, city):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""You are a local travel expert. Give detailed information about "{name}" in {city}.

Return ONLY a JSON object with these fields:
- "name": full name of the place
- "description": 2-3 sentence description
- "price": estimated cost per person (e.g. "Free", "€5-10", "€20-30")
- "location": neighborhood or address
- "hours": opening hours if known, otherwise "Check locally"
- "reviews": array of 3 short realistic reviews someone might post online, each under 20 words

Example:
{{
  "name": "LX Factory",
  "description": "A repurposed industrial complex hosting independent shops, restaurants and a Sunday market. One of Lisbon's most creative spaces.",
  "price": "Free entry, €10-20 for food",
  "location": "Alcântara, near the 25 de Abril Bridge",
  "hours": "Tuesday to Sunday, 12pm - midnight",
  "reviews": [
    "the sunday market here is absolutely worth waking up early for",
    "best collection of independent shops in lisbon by far",
    "go for brunch and stay for the afternoon, you won't regret it"
  ]
}}

Return only the JSON object, nothing else."""

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"]

@app.route("/place")
def place():
    name = request.args.get("name")
    city = request.args.get("city")
    details_raw = get_place_details(name, city)
    try:
        details = json.loads(details_raw)
    except:
        details = {"name": name, "description": "No details found.", "price": "Unknown", "location": "Unknown", "hours": "Unknown", "reviews": []}
    return render_template("place.html", details=details, city=city)

if __name__ == "__main__":
    app.run(debug=True)