#!/usr/bin/env python3
"""
LinkedIn Scanner Web App — Flask
Jalanin:  python3 app.py
Buka:     http://localhost:5000

Ephemeral — gak pake database, hasil ilang kalo server restart.
"""

import sys, os, re, time, json, threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Import scanner logic
from ddgs import DDGS

app = Flask(__name__)

# In-memory cache (biar search yg sama gak perlu ulang)
cache = {}
CACHE_TTL = 300  # 5 menit

# ─── SCANNER LOGIC ───

def search_linkedin(keyword, limit=20):
    cache_key = f"{keyword}:{limit}"
    now = time.time()
    
    if cache_key in cache and (now - cache[cache_key]["time"]) < CACHE_TTL:
        return cache[cache_key]["data"]
    
    query = f'site:linkedin.com/in "{keyword}"'
    results = []
    seen = set()
    
    try:
        ddgs = DDGS()
        raw = list(ddgs.text(query, region='wt-wt', max_results=limit * 2))
        
        for r in raw:
            url = r.get("href", "")
            m = re.search(r"linkedin\.com/in/([^/?#]+)", url)
            if not m:
                continue
            
            uid = m.group(1).lower()
            if uid in seen:
                continue
            seen.add(uid)
            
            title = r.get("title", "")
            snippet = r.get("body", "")
            
            # Extract name
            name = extract_name(title, uid)
            job = extract_job(title)
            company = extract_company(title)
            country = detect_country(snippet, title)
            
            results.append({
                "name": name,
                "job": job,
                "company": company,
                "country": country,
                "linkedin": url.split("?")[0].rstrip("/"),
                "username": uid,
            })
            
            if len(results) >= limit:
                break
    except Exception as e:
        return {"error": str(e)}
    
    # Cache
    cache[cache_key] = {"data": results, "time": now}
    return results

def extract_name(title, username):
    text = title
    for s in [" - LinkedIn", " | LinkedIn"]:
        text = text.replace(s, "")
    parts = text.split(" - ")
    name = parts[0].strip() if parts else ""
    
    if name and 3 < len(name) < 60 and not re.search(r'[<>{}()\[\]]', name):
        return name
    
    # Fallback
    name = (username.replace("-", " ").replace("_", " ").replace(".", " ").title())
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:50] if len(name) > 3 else username

def extract_job(title):
    parts = title.replace(" - LinkedIn", "").split(" - ")
    if len(parts) >= 2:
        job = parts[1].strip()
        return job[:80]
    return ""

def extract_company(title):
    parts = title.replace(" | LinkedIn", "").split(" - ")
    if len(parts) >= 3:
        return parts[2].strip()[:60]
    return ""

def detect_country(snippet, title):
    text = (snippet + " " + title).lower()
    
    locations = {
        "Indonesia": ["indonesia", "jakarta", "bandung", "surabaya", "yogyakarta", "bali", "medan", "tangerang", "bekasi", "makassar", "semarang", "depok", "bogor", "malang", "solo", "batam", "pekanbaru", "padang", "lombok", "jawa", "sumatra"],
        "Malaysia": ["malaysia", "kuala lumpur", "selangor", "johor", "penang", "sabah", "sarawak"],
        "Singapore": ["singapore", "singapura"],
        "United States": ["united states", "usa", "california", "new york", "texas", "florida", "washington dc", "san francisco", "los angeles", "chicago", "seattle", "boston", "miami", "new york city"],
        "United Kingdom": ["united kingdom", "london", "england", "uk", "manchester", "birmingham", "edinburgh", "glasgow", "leeds"],
        "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra"],
        "Netherlands": ["netherlands", "amsterdam", "rotterdam", "utrecht", "the hague", "eindhoven"],
        "Germany": ["germany", "berlin", "munich", "hamburg", "frankfurt", "cologne", "stuttgart", "dusseldorf"],
        "India": ["india", "mumbai", "bangalore", "new delhi", "pune", "hyderabad", "chennai", "kolkata", "gurgaon", "noida", "ahmedabad"],
        "Japan": ["japan", "tokyo", "osaka", "kyoto", "yokohama", "nagoya", "sapporo"],
        "Canada": ["canada", "toronto", "vancouver", "montreal", "calgary", "ottawa"],
        "UAE": ["dubai", "abu dhabi", "uae", "sharjah"],
        "Saudi Arabia": ["riyadh", "jeddah", "dammam", "khobar", "saudi arabia"],
        "Philippines": ["philippines", "manila", "cebu", "davao", "quezon city", "makati"],
        "Thailand": ["thailand", "bangkok", "phuket", "chiang mai", "pattaya"],
        "Vietnam": ["vietnam", "ho chi minh", "hanoi", "danang"],
        "South Korea": ["south korea", "seoul", "busan", "incheon"],
        "France": ["france", "paris", "lyon", "marseille", "bordeaux", "toulouse", "lille", "nice"],
        "Brazil": ["brazil", "são paulo", "rio de janeiro", "brasilia", "salvador", "belo horizonte"],
        "Hong Kong": ["hong kong"],
        "Taiwan": ["taiwan", "taipei"],
        "Switzerland": ["switzerland", "zurich", "geneva", "basel", "bern"],
        "Sweden": ["sweden", "stockholm", "gothenburg"],
        "Norway": ["norway", "oslo", "bergen"],
        "Denmark": ["denmark", "copenhagen"],
        "Finland": ["finland", "helsinki"],
        "Italy": ["italy", "milan", "rome", "turin", "florence", "bologna"],
        "Spain": ["spain", "madrid", "barcelona", "valencia", "seville"],
        "Mexico": ["mexico", "mexico city", "guadalajara", "monterrey"],
        "Turkey": ["turkey", "istanbul", "ankara", "izmir"],
        "Poland": ["poland", "warsaw", "krakow", "wroclaw"],
        "Russia": ["russia", "moscow", "st petersburg"],
        "Ireland": ["ireland", "dublin", "cork"],
        "New Zealand": ["new zealand", "auckland", "wellington"],
        "South Africa": ["south africa", "johannesburg", "cape town"],
        "Nigeria": ["nigeria", "lagos", "abuja"],
        "Egypt": ["egypt", "cairo", "alexandria"],
        "Argentina": ["argentina", "buenos aires", "cordoba"],
        "Colombia": ["colombia", "bogota", "medellin"],
        "Chile": ["chile", "santiago"],
        "Morocco": ["morocco", "casablanca", "rabat", "marrakech"],
        "Kenya": ["kenya", "nairobi"],
    }
    
    for country, keywords in locations.items():
        for kw in keywords:
            if kw in text:
                return country
    
    return ""

# ─── ROUTES ───

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/search")
def api_search():
    keyword = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 20))
    
    if not keyword:
        return jsonify({"error": "Keyword required"})
    
    limit = min(max(limit, 5), 100)
    
    results = search_linkedin(keyword, limit)
    
    if isinstance(results, dict) and "error" in results:
        return jsonify({"error": results["error"]})
    
    stats = {
        "total": len(results),
        "with_country": sum(1 for r in results if r["country"]),
    }
    
    return jsonify({"results": results, "stats": stats, "keyword": keyword})

@app.route("/api/clear-cache")
def clear_cache():
    cache.clear()
    return jsonify({"ok": True})

# ─── MAIN ───

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"\n  🔍 LinkedIn Scanner Web App")
    print(f"  {'─'*40}")
    print(f"  Buka: http://localhost:{port}")
    print(f"  Ctrl+C untuk stop\n")
    app.run(host="0.0.0.0", port=port, debug=True)
