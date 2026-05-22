# Localr

A travel app that surfaces hidden gem activities by reading what real people say on Reddit, Quora, and other community platforms, not what paid reviewers or sponsored listicles want you to see.

---

## The idea

Every time I tried to find something cool to do in a new city, I'd end up on TripAdvisor looking at the same 10 tourist traps. The good stuff was always buried in a Reddit thread from 3 years ago that took 45 minutes to find.

Localr automates that. You pick a city and a vibe, and the app does the digging for you.

---

## How it works

1. Enter a destination city
2. Pick a mood, Outdoor, Food & Drink, Culture, Nightlife, or Budget
3. The app scans Reddit and community platforms for real recommendations
4. Activities come up as swipeable cards, right to save, left to skip
5. Each card shows a real quote from an actual post, plus a **Local Score** (how many times a place was organically mentioned)
6. Saved activities can be turned into a day-by-day itinerary

---

## Features

- **Human-first sourcing** — every recommendation comes from a real person, not a paid critic
- **Local Score** — a trust metric based on organic mentions across platforms
- **Mood mode** — filters recommendations by the kind of experience you're after
- **Swipe interface** — fast, fun, feels like browsing should
- **Real quotes on cards** — you always know where a recommendation came from
- **Itinerary builder** — turns your saved spots into an actual plan

---

## Tech stack

- Frontend: HTML, CSS, JavaScript (moving to React later)
- Backend: Python + Flask
- AI: Claude API for summarization and extraction
- Data: Reddit API, Quora, Google Places API
- Database: SQLite
- Auth: Flask-Login

---

## Build phases

| Phase | Goal |
|-------|------|
| 1 — AI engine | Terminal only. Prove the core idea works |
| 2 — Web interface | Flask site with search and card results |
| 3 — Swipe mechanic | Right/left swiping, save to a list |
| 4 — Detail pages | Full activity info, raw reviews, Local Score |
| 5 — Accounts + itinerary | Login, saved activities, day-by-day plan |

Currently on: **Phase 1**

---

## Status

Just getting started. Following the build from scratch, documenting everything as I go.

---

## Why "Localr"

Short for local recommender. The missing e is intentional, Tumblr, Flickr, inspiration.
