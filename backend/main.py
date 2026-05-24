import os
import requests
import json
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "localr-secret-key-change-this-later"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///localr.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# --- Models ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    saved_places = db.relationship("SavedPlace", backref="user", lazy=True)

class SavedPlace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    score = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AI Functions ---

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
extract exactly 10 specific activity recommendations that match a '{mood}' experience.

Return ONLY a JSON array with exactly 10 objects. Each object must have:
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

Return only the JSON object, nothing else."""

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"]

def build_itinerary(places, city):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    place_names = [p.name for p in places]
    prompt = f"""You are a travel planner. Create a day-by-day itinerary for {city} using these places: {place_names}.

Return ONLY a JSON array where each object is a day:
- "day": day number
- "title": short title for the day
- "places": array of place names for that day
- "tip": one practical tip for the day

Example:
[
  {{
    "day": 1,
    "title": "Art and Culture",
    "places": ["Van Abbemuseum", "Eindhoven Museum"],
    "tip": "Start early at the museum to avoid crowds, grab lunch nearby."
  }}
]

Spread the places across days logically. Return only the JSON array, nothing else."""

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"]

def get_place_images(name, city):
    UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    
    # Try specific place name first
    params = {"query": name, "per_page": 5, "orientation": "landscape"}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    results = data.get("results", [])
    
    # If less than 2 results, try place + city
    if len(results) < 2:
        params["query"] = f"{name} {city}"
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        results = data.get("results", [])
    
    # If still nothing, fall back to city travel photos
    if len(results) < 2:
        params["query"] = f"{city} travel food restaurant"
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        results = data.get("results", [])
    
    images = []
    for photo in results[:5]:
        images.append({
            "url": photo["urls"]["regular"],
            "credit": photo["user"]["name"],
            "credit_link": photo["user"]["links"]["html"]
        })
    return images

def get_coordinates(name, city):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{name}, {city}",
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "localr-app"}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if data:
        return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
    return None

# --- Routes ---

@app.route("/")
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

@app.route("/save", methods=["POST"])
@login_required
def save_place():
    name = request.form.get("name")
    summary = request.form.get("summary")
    score = request.form.get("score")
    city = request.form.get("city")
    place = SavedPlace(name=name, summary=summary, score=score, city=city, user_id=current_user.id)
    db.session.add(place)
    db.session.commit()
    return {"status": "saved"}

@app.route("/saved")
@login_required
def saved():
    places = SavedPlace.query.filter_by(user_id=current_user.id).all()
    places_with_coords = []
    for place in places:
        coords = get_coordinates(place.name, place.city)
        places_with_coords.append({
            "id": place.id,
            "name": place.name,
            "summary": place.summary,
            "score": place.score,
            "city": place.city,
            "lat": coords["lat"] if coords else None,
            "lon": coords["lon"] if coords else None
        })
    return render_template("saved.html", places=places_with_coords)

@app.route("/itinerary")
@login_required
def itinerary():
    places = SavedPlace.query.filter_by(user_id=current_user.id).all()
    if not places:
        return redirect(url_for("saved"))
    city = places[0].city
    itinerary_raw = build_itinerary(places, city)
    try:
        days = json.loads(itinerary_raw)
    except:
        days = []
    return render_template("itinerary.html", days=days, city=city)

@app.route("/place")
def place():
    name = request.args.get("name")
    city = request.args.get("city")
    details_raw = get_place_details(name, city)
    try:
        details = json.loads(details_raw)
    except:
        details = {"name": name, "description": "No details found.", "price": "Unknown", "location": "Unknown", "hours": "Unknown", "reviews": []}
    images = get_place_images(name, city)
    return render_template("place.html", details=details, city=city, images=images)

@app.route("/images")
def images():
    name = request.args.get("name")
    city = request.args.get("city")
    mood = request.args.get("mood", "")
    imgs = get_place_images(name, city)
    if len(imgs) < 2:
        imgs = get_place_images(mood, city)
    return {"images": imgs}

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already taken.")
        user = User(username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)