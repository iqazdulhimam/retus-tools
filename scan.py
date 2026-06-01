#!/usr/bin/env python3
"""
LinkedIn Scanner v3 — Cari profil LinkedIn berdasarkan keyword
Menggunakan Google Programmable Search API (free, 100 queries/day)

Cara setup (sekali doang):
  1. Buka https://programmablesearchengine.google.com/
  2. Klik "Create" → masukin nama bebas (misal "LinkedIn Scanner")
  3. Di "Sites to search" pilih "Search the entire web" (penting!)
  4. Klik Create, nanti dapet Search Engine ID (cx)
  5. Buka https://console.cloud.google.com/apis/credentials
  6. Create Credentials → API Key → copy API Key nya
  7. Simpen di file config.json (isi nya ada di bawah)

Usage:
  python3 scan.py "Konstruksi"
  python3 scan.py "Data Scientist" --limit 30
  python3 scan.py --setup           (buat config file)
"""

import sys, re, json, os, csv, time
from datetime import datetime

try:
    import requests
except ImportError:
    os.system("pip install requests --quiet --break-system-packages")
    import requests

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "scan_config.json")
TIMEOUT = 15

# ─── CONFIG ───

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(api_key, cx):
    config = {"api_key": api_key, "cx": cx}
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  ✅ Config saved to {CONFIG_FILE}")

def setup_wizard():
    print(f"\n{'='*60}")
    print("  LinkedIn Scanner — Setup")
    print(f"{'='*60}")
    print("""
  1. Buka https://programmablesearchengine.google.com/
  2. Klik "Create" → nama bebas (misal "LinkedIn Scanner")
  3. Pilih "Search the entire web" — ini penting!
  4. Klik Create → copy "Search engine ID" (cx)
  
  5. Buka https://console.cloud.google.com/apis/credentials
  6. Create Credentials → API Key → copy key nya
""")
    
    cx = input("  Paste Search Engine ID (cx): ").strip()
    api_key = input("  Paste API Key: ").strip()
    
    if cx and api_key:
        save_config(api_key, cx)
        print("  ✅ Setup selesai! Tinggal jalanin scan nya.\n")
    else:
        print("  [!] Kedua field harus diisi.\n")

# ─── GOOGLE CUSTOM SEARCH ───

def google_search(api_key, cx, query, num=10, start=1):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(num, 10),
        "start": start,
    }
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        data = resp.json()
        
        if "error" in data:
            err = data["error"]
            print(f"  [!] API Error: {err.get('message', '?')}")
            if "rate" in str(err).lower():
                print("  [!] Rate limit exceeded. Tunggu bentar atau upgrade API key.")
            return []
        
        return data.get("items", [])
    except Exception as e:
        print(f"  [!] Request failed: {e}")
        return []

# ─── FILTER LINKEDIN ───

def is_linkedin_profile(url):
    return bool(re.search(r"linkedin\.com/in/[^/]+", url, re.I))

def extract_username(url):
    m = re.search(r"linkedin\.com/in/([^/?#]+)", url, re.I)
    return m.group(1) if m else ""

def clean_url(url):
    return url.split("?")[0].rstrip("/")

# ─── NAME EXTRACTION ───

def extract_name(title, snippet, url):
    text = title
    
    # Remove LinkedIn branding
    for s in [" - LinkedIn", " | LinkedIn", " - LinkedIn Profile"]:
        text = text.replace(s, "")
    
    parts = text.split(" - ")
    name = parts[0].strip()
    
    # Validate name
    if name and 3 < len(name) < 60 and not re.search(r'[<>{}[\]\\]', name):
        return name
    
    # Fallback: username → name format
    username = extract_username(url)
    if username:
        return username.replace("-", " ").replace("_", " ").title()
    
    return name

# ─── COUNTRY DETECTION ───

def detect_country(snippet, title):
    """Detect country from snippet + title."""
    text = (snippet + " " + title).lower()
    
    # Direct location mentions
    locations = {
        "Indonesia": ["indonesia", "jakarta", "bandung", "surabaya", "yogyakarta", "bali", "medan", "makassar", "semarang", "tangerang", "bekasi", "depok", "bogor"],
        "Malaysia": ["malaysia", "kuala lumpur", "selangor", "johor", "penang", "sabah", "sarawak"],
        "Singapore": ["singapore", "singapura"],
        "United States": ["united states", "usa", "california", "new york", "texas", "florida", "washington dc", "san francisco", "new york city", "los angeles", "chicago"],
        "United Kingdom": ["united kingdom", "london", "england", "uk", "manchester", "birmingham", "edinburgh"],
        "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "canberra"],
        "Netherlands": ["netherlands", "amsterdam", "rotterdam", "utrecht", "hague", "eindhoven"],
        "Germany": ["germany", "berlin", "munich", "hamburg", "frankfurt", "cologne", "stuttgart"],
        "India": ["india", "mumbai", "bangalore", "new delhi", "pune", "hyderabad", "chennai", "kolkata"],
        "Japan": ["japan", "tokyo", "osaka", "kyoto", "yokohama", "nagoya"],
        "Canada": ["canada", "toronto", "vancouver", "montreal", "calgary", "ottawa"],
        "UAE": ["dubai", "abu dhabi", "uae", "united arab emirates", "sharjah"],
        "Saudi Arabia": ["riyadh", "jeddah", "dammam", "khobar", "saudi arabia"],
        "Philippines": ["philippines", "manila", "cebu", "davao", "quezon"],
        "Thailand": ["thailand", "bangkok", "phuket", "chiang mai", "pattaya"],
        "Vietnam": ["vietnam", "ho chi minh", "hanoi", "danang", "haiphong"],
        "South Korea": ["south korea", "seoul", "busan", "incheon", "daegu"],
        "France": ["france", "paris", "lyon", "marseille", "bordeaux", "toulouse"],
        "Brazil": ["brazil", "são paulo", "rio de janeiro", "brasilia", "salvador"],
        "Hong Kong": ["hong kong"],
        "Taiwan": ["taiwan", "taipei"],
        "Switzerland": ["switzerland", "zurich", "geneva", "basel", "bern"],
        "Sweden": ["sweden", "stockholm", "gothenburg", "malmo"],
    }
    
    detected = []
    for country, keywords in locations.items():
        for kw in keywords:
            if kw in text:
                detected.append(country)
                break
    
    return detected[0] if detected else ""

# ─── EMAIL SEARCH ───

def search_email(name, api_key, cx):
    """Search for email using Google Custom Search."""
    if not name or len(name) < 5:
        return ""
    
    query = f'"{name}" email "@"'
    results = google_search(api_key, cx, query, num=3)
    
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found = set()
    
    for r in results:
        snippet = r.get("snippet", "")
        title = r.get("title", "")
        emails = re.findall(email_pattern, snippet + " " + title)
        for e in emails:
            e = e.lower()
            skip = ["google.com", "youtube.com", "facebook.com", "twitter.com", "x.com",
                    "linkedin.com", "instagram.com", "github.com", "wikipedia.org",
                    "example.com", ".png", ".jpg", ".gif", ".svg"]
            if not any(s in e for s in skip):
                found.add(e)
    
    return ", ".join(list(found)[:3]) if found else ""

# ─── MAIN SCAN ───

def scan_linkedin(keyword, limit=20, api_key=None, cx=None):
    print(f"\n{'═'*70}")
    print(f"  🔍 LinkedIn Scanner — Keyword: \"{keyword}\"")
    print(f"  Target: {limit} profiles")
    print(f"{'═'*70}\n")
    
    query = f'site:linkedin.com/in "{keyword}"'
    all_results = []
    
    # Google CSE returns max 10 per page, need multiple pages
    pages = (limit // 10) + (1 if limit % 10 else 0)
    
    for page in range(pages):
        remaining = limit - len(all_results)
        if remaining <= 0:
            break
        
        num = min(remaining, 10)
        start = page * 10 + 1
        
        print(f"  Page {page+1}/{pages} (start={start}, num={num})...")
        items = google_search(api_key, cx, query, num=num, start=start)
        
        # Filter LinkedIn profiles
        for item in items:
            url = item.get("link", "")
            if is_linkedin_profile(url):
                all_results.append({
                    "url": clean_url(url),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                })
        
        if len(items) < num:
            break  # No more results
        
        time.sleep(0.5)  # Rate limit
    
    if not all_results:
        print(f"\n  [!] No LinkedIn profiles found.\n")
        return []
    
    print(f"\n  Found {len(all_results)} profiles. Analyzing...\n")
    
    output = []
    for i, p in enumerate(all_results[:limit], 1):
        name = extract_name(p["title"], p["snippet"], p["url"])
        country = detect_country(p["snippet"], p["title"])
        
        # Search email
        sys.stdout.write(f"    \r  [{i}/{len(all_results)}] {name[:28]:28s} 🔎")
        sys.stdout.flush()
        email = search_email(name, api_key, cx)
        
        status = "✅" if email else " "
        sys.stdout.write(f"\r  [{i}/{len(all_results)}] {name[:28]:28s} {status}")
        sys.stdout.flush()
        print()
        
        output.append({
            "no": i,
            "name": name,
            "linkedin": p["url"],
            "email": email,
            "country": country,
            "keyword": keyword,
        })
    
    print()
    return output

# ─── DISPLAY ───

def display_results(results, keyword):
    if not results:
        return
    
    print(f"\n{'═'*80}")
    print(f"  ✅ \"{keyword}\" — {len(results)} profiles")
    print(f"{'═'*80}\n")
    
    for r in results:
        e = r["email"] if r["email"] else "—"
        c = r["country"] if r["country"] else "—"
        print(f"  [{r['no']:2d}] {r['name'][:30]:30s} 🌍 {c[:20]:20s}")
        print(f"       🔗 {r['linkedin']}")
        print(f"       📧 {e}")
        print()
    
    # Stats
    we = sum(1 for r in results if r["email"])
    wc = sum(1 for r in results if r["country"] != "")
    print(f"  {'─'*50}")
    print(f"  Total: {len(results)} | Email ditemukan: {we}/{len(results)} | Negara: {wc}/{len(results)}")
    
    save_results(results, keyword)

def save_results(results, keyword):
    fname = re.sub(r'[^\w]', '_', keyword.lower())[:20]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    jp = f"scan_{fname}_{ts}.json"
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    cp = f"scan_{fname}_{ts}.csv"
    if results:
        with open(cp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)
    
    print(f"  📄 Saved: {jp}")
    print(f"  📄 Saved: {cp}")

# ─── ENTRY ───

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
  LinkedIn Scanner v3

  Usage:
    python3 scan.py --setup             🔧 Setup API key (pertama kali)
    python3 scan.py "Konstruksi"         🔍 Scan LinkedIn
    python3 scan.py "Data Scientist" --limit 30
    python3 scan.py "Marketing" --save hasil.csv

  Setup pertama kali:
    python3 scan.py --setup
    → Masukin Google API Key + Search Engine ID
    → Gratis, 100 query/hari
""")
        sys.exit(1)
    
    if sys.argv[1] == "--setup":
        setup_wizard()
        sys.exit(0)
    
    keyword = sys.argv[1]
    limit = 20
    
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        limit = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 20
    
    # Load config
    config = load_config()
    if not config.get("api_key") or not config.get("cx"):
        print("\n  [!] Belum setup! Jalankan: python3 scan.py --setup\n")
        sys.exit(1)
    
    results = scan_linkedin(keyword, limit=limit, **config)
    
    if results:
        display_results(results, keyword)
    else:
        print("""
  [!] No results. Kemungkinan:
    1. Keyword terlalu spesifik — coba yang lebih umum
    2. API key limit habis — cek Google Console
    3. Search Engine ID salah — pastikan pilih "Search the entire web"
""")
