import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def search_reddit(city, vibe):
    print(f"\nSearching for {vibe} things to do in {city}...\n")
    
    query = f"{city} hidden gems {vibe} things to do site:reddit.com"
    url = "https://www.google.com/search"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    }
    
    params = {"q": query, "num": 10}
    response = requests.get(url, headers=headers, params=params)
    return response.text

def ask_groq(content, city, vibe):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""You are a local travel expert. Based on the following search results about {city}, 
extract 5 specific activity recommendations that match a '{vibe}' vibe.

For each activity, write:
- Name of the place or activity
- One sentence description
- Why it fits the {vibe} vibe

Search results:
{content[:3000]}

List only real, specific places. No generic advice."""

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    return result["choices"][0]["message"]["content"]

def main():
    city = input("Enter a city: ")
    vibe = input("Pick a vibe (Adventurous / Chill / Foodie / Culture / Nightlife / Broke Student): ")
    
    raw = search_reddit(city, vibe)
    recommendations = ask_groq(raw, city, vibe)
    
    print("\n--- LOCALR RECOMMENDATIONS ---\n")
    print(recommendations)

if __name__ == "__main__":
    main()