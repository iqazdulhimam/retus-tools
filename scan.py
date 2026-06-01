#!/usr/bin/env python3
"""
LinkedIn Scanner — Cari profil LinkedIn by keyword
Menggunakan DuckDuckGo (free, no API key, no database, ephemeral)

Usage:
  python3 scan.py "Konstruksi"
  python3 scan.py "Data Scientist" --limit 50
  python3 scan.py "Software Engineer" --email
  python3 scan.py "Marketing" --save    (save hasil kalo mau)

Hasil ditampilkan di layar, gak disimpan di database.
--save optional kalo mau export CSV/JSON.
"""

import sys, re, time, json, csv, os
from datetime import datetime

try:
    from ddgs import DDGS
except ImportError:
    os.system("pip install ddgs --quiet --break-system-packages")
    from ddgs import DDGS

try:
    import requests
except ImportError:
    os.system("pip install requests --quiet --break-system-packages")
    import requests

DELAY = 1.5

# ─── CORE SEARCH ───

def search_linkedin(keyword, limit=20):
    """Search LinkedIn profiles using DuckDuckGo."""
    query = f'site:linkedin.com/in {keyword}'
    print(f"  🔍 Searching: \"{query}\"")
    
    try:
        ddgs = DDGS()
        # Use text search
        raw_results = list(ddgs.text(
            query,
            region='wt-wt',  # Worldwide
            max_results=limit * 2,
        ))
    except Exception as e:
        print(f"  [!] Search error: {e}")
        return []
    
    # Filter + dedupe LinkedIn profiles
    seen = set()
    profiles = []
    
    for r in raw_results:
        url = r.get("href", "")
        if not re.search(r"linkedin\.com/in/[^/]+", url):
            continue
        
        # Dedupe
        username = extract_username(url)
        if username in seen:
            continue
        seen.add(username)
        
        profiles.append({
            "url": clean_url(url),
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "username": username,
        })
        
        if len(profiles) >= limit:
            break
    
    return profiles

# ─── EXTRACTORS ───

def extract_username(url):
    m = re.search(r"linkedin\.com/in/([^/?#]+)", url, re.I)
    return m.group(1).lower() if m else ""

def clean_url(url):
    return url.split("?")[0].rstrip("/")

def extract_name(profile):
    """Extract name from username + title."""
    title = profile["title"]
    
    # Remove LinkedIn suffix
    for s in [" - LinkedIn", " | LinkedIn", " | LinkedIn Profile"]:
        title = title.replace(s, "")
    
    # Title usually format: "Name - Job Title - Company"
    parts = title.split(" - ")
    name = parts[0].strip() if parts else ""
    
    if name and 3 < len(name) < 60 and not re.search(r'[<>{}()\[\]]', name):
        return name
    
    # Fallback: make username human-readable
    username = profile["username"]
    name = (username
        .replace("-", " ")
        .replace("_", " ")
        .replace(".", " ")
        .title())
    
    # Clean up weird username-based names
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:50] if len(name) > 3 else username

def extract_job(title):
    """Extract job title from LinkedIn search result."""
    parts = title.replace(" - LinkedIn", "").split(" - ")
    if len(parts) >= 2:
        return parts[1].strip()
    return ""

def extract_company(title):
    """Extract company from LinkedIn search result."""
    parts = title.replace(" - LinkedIn", "").split(" - ")
    if len(parts) >= 3:
        return parts[2].strip()
    return ""

def detect_country(profile):
    """Detect country from snippet + title."""
    text = (profile["snippet"] + " " + profile["title"]).lower()
    
    locations = {
        "Indonesia": ["indonesia", "jakarta", "bandung", "surabaya", "yogyakarta", "bali", "medan", "tangerang", "bekasi", "makassar", "semarang", "depok", "bogor", "malang", "solo", "samarinda", "palembang", "aceh", "lombok", "batam"],
        "Malaysia": ["malaysia", "kuala lumpur", "selangor", "johor bahru", "penang", "sabah", "sarawak", "petaling jaya"],
        "Singapore": ["singapore"],
        "United States": ["united states", "usa", "california", "new york", "texas", "florida", "washington dc", "san francisco", "los angeles", "chicago", "seattle", "boston", "miami", "silicon valley", "san jose"],
        "United Kingdom": ["united kingdom", "london", "england", "uk", "manchester", "birmingham", "edinburgh", "glasgow", "leeds", "liverpool"],
        "Australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra", "gold coast"],
        "Netherlands": ["netherlands", "amsterdam", "rotterdam", "utrecht", "the hague", "eindhoven", "groningen"],
        "Germany": ["germany", "berlin", "munich", "hamburg", "frankfurt", "cologne", "stuttgart", "dusseldorf", "dresden", "leipzig", "nuremberg"],
        "India": ["india", "mumbai", "bangalore", "new delhi", "pune", "hyderabad", "chennai", "kolkata", "ahmedabad", "gurgaon", "noida"],
        "Japan": ["japan", "tokyo", "osaka", "kyoto", "yokohama", "nagoya", "sapporo", "kobe"],
        "Canada": ["canada", "toronto", "vancouver", "montreal", "calgary", "ottawa", "edmonton", "quebec"],
        "UAE": ["dubai", "abu dhabi", "uae", "sharjah", "ajman", "ras al khaimah"],
        "Saudi Arabia": ["riyadh", "jeddah", "dammam", "khobar", "mecca", "madinah"],
        "Philippines": ["philippines", "manila", "cebu", "davao", "quezon city", "makati"],
        "Thailand": ["thailand", "bangkok", "phuket", "chiang mai", "pattaya", "nonthaburi"],
        "Vietnam": ["vietnam", "ho chi minh city", "hanoi", "danang", "haiphong", "can tho"],
        "South Korea": ["south korea", "seoul", "busan", "incheon", "daegu", "daejeon"],
        "France": ["france", "paris", "lyon", "marseille", "bordeaux", "toulouse", "lille", "nice", "nantes", "strasbourg"],
        "Brazil": ["brazil", "são paulo", "rio de janeiro", "brasilia", "salvador", "fortaleza", "belo horizonte", "curitiba", "recife", "porto alegre"],
        "Hong Kong": ["hong kong"],
        "Taiwan": ["taiwan", "taipei", "kaohsiung", "taichung", "tainan"],
        "Switzerland": ["switzerland", "zurich", "geneva", "basel", "bern", "lausanne"],
        "Sweden": ["sweden", "stockholm", "gothenburg", "malmo", "uppsala", "lund"],
        "Norway": ["norway", "oslo", "bergen", "trondheim", "stavanger"],
        "Denmark": ["denmark", "copenhagen", "aarhus", "odense", "aalborg"],
        "Finland": ["finland", "helsinki", "espoo", "tampere", "vantaa", "turku"],
        "Poland": ["poland", "warsaw", "krakow", "wroclaw", "poznan", "gdansk"],
        "Italy": ["italy", "milan", "rome", "turin", "florence", "bologna", "naples", "venice"],
        "Spain": ["spain", "madrid", "barcelona", "valencia", "seville", "bilbao"],
        "Mexico": ["mexico", "mexico city", "guadalajara", "monterrey", "puebla", "tijuana"],
        "Turkey": ["turkey", "istanbul", "ankara", "izmir", "antalya", "bursa"],
        "Russia": ["russia", "moscow", "st petersburg", "novosibirsk", "yekaterinburg"],
        "Ireland": ["ireland", "dublin", "cork", "galway", "limerick"],
        "New Zealand": ["new zealand", "auckland", "wellington", "christchurch", "queenstown"],
        "South Africa": ["south africa", "johannesburg", "cape town", "durban", "pretoria"],
        "Nigeria": ["nigeria", "lagos", "abuja", "port harcourt", "ibadan"],
        "Egypt": ["egypt", "cairo", "alexandria", "giza", "sharm el sheikh"],
        "Morocco": ["morocco", "casablanca", "rabat", "marrakech", "tangier", "fes"],
        "Argentina": ["argentina", "buenos aires", "cordoba", "rosario", "mendoza"],
        "Colombia": ["colombia", "bogota", "medellin", "cali", "barranquilla", "cartagena"],
        "Chile": ["chile", "santiago", "valparaiso", "concepcion", "la serena"],
    }
    
    for country, keywords in locations.items():
        for kw in keywords:
            if kw in text:
                return country
    
    return ""

def search_email(name, ddgs):
    """Cari email berdasarkan nama via DuckDuckGo."""
    if not name or len(name) < 5:
        return ""
    
    query = f'"{name}" email'
    try:
        results = list(ddgs.text(query, region='wt-wt', max_results=5))
    except:
        return ""
    
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found = set()
    
    for r in results:
        snippet = r.get("body", "")
        title = r.get("title", "") 
        emails = re.findall(email_pattern, f"{snippet} {title}")
        
        for e in emails:
            e = e.lower()
            # Skip generic/logo emails
            skip_domains = [
                "google.com", "youtube.com", "facebook.com", "twitter.com",
                "x.com", "linkedin.com", "instagram.com", "github.com",
                "wikipedia.org", "example.com", "domain.com", "email.com",
                "test.com", "mail.com", "outlook.com", "yahoo.com",
                "hotmail.com", "gmail.com", "icloud.com", "protonmail.com",
            ]
            # Skip if it's a common personal email domain (we want work emails)
            if "." in e.split("@")[0]:
                # Has dot in username - more likely to be a work email
                # e.g. john.doe@company.com
                if not any(d in e for d in ["google", "facebook", "twitter", "linkedin", "wikipedia"]):
                    found.add(e)
    
    return ", ".join(list(found)[:2]) if found else ""

# ─── DISPLAY ───

def display_results(profiles, keyword, search_email_flag=False, ddgs=None):
    """Display results in terminal (ephemeral — no database)."""
    if not profiles:
        print(f"\n  [!] No LinkedIn profiles found for \"{keyword}\".")
        print("  [!] Coba keyword yang lebih umum (Bahasa Inggris).")
        return []
    
    results = []
    total = len(profiles)
    
    print(f"\n  ✅ Found {total} profiles. Processing...\n")
    
    for i, p in enumerate(profiles, 1):
        name = extract_name(p)
        job = extract_job(p["title"])
        company = extract_company(p["title"])
        country = detect_country(p)
        email = ""
        
        # Progress
        sys.stdout.write(f"\r    [{i}/{total}] {name[:28]:28s} ⏳")
        sys.stdout.flush()
        
        # Email search (optional - slow)
        if search_email_flag and ddgs:
            email = search_email(name, ddgs)
            time.sleep(DELAY)
        
        status = "📧" if email else "  "
        sys.stdout.write(f"\r    [{i}/{total}] {name[:28]:28s} {status}")
        sys.stdout.flush()
        print()
        
        results.append({
            "name": name,
            "job": job,
            "company": company,
            "country": country,
            "email": email,
            "linkedin": p["url"],
        })
    
    # ─── DISPLAY TABLE ───
    print(f"\n{'═'*90}")
    print(f"  📋 RESULTS: \"{keyword}\" — {total} profiles")
    print(f"{'═'*90}\n")
    
    for r in results:
        name = r["name"]
        country = r["country"] if r["country"] else "?"
        email = r["email"] if r["email"] else "—"
        job = r["job"] if r["job"] else ""
        company = r["company"] if r["company"] else ""
        
        # Format: Name | Country | Email | LinkedIn
        print(f"  👤 {name}")
        if job:
            print(f"     💼 {job}")
        if company:
            print(f"     🏢 {company}")
        print(f"     🌍 {country}")
        print(f"     📧 {email}")
        print(f"     🔗 {r['linkedin']}")
        print()
    
    # Stats
    with_email = sum(1 for r in results if r["email"])
    with_country = sum(1 for r in results if r["country"])
    print(f"  {'─'*50}")
    print(f"  Total: {total} | With email: {with_email} | With country: {with_country}/{total}")
    print()
    
    return results

# ─── SAVE (optional) ───

def save_results(results, keyword):
    if not results:
        return
    
    fname = re.sub(r'[^\w]', '_', keyword.lower())[:20]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV
    cpath = f"scan_{fname}_{ts}.csv"
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
    
    # JSON
    jpath = f"scan_{fname}_{ts}.json"
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"  📄 CSV: {cpath}")
    print(f"  📄 JSON: {jpath}")

# ─── HELP ───

def show_help():
    print("""
  🔍 LinkedIn Scanner — Ephemeral (no database)

  USAGE:
    python3 scan.py "Konstruksi"           Cari profil LinkedIn
    python3 scan.py "Data Scientist" -l50  Limit 50 results
    python3 scan.py "Marketing" --email    Cari email juga (lebih lambat)
    python3 scan.py "Engineer" --save      Export CSV + JSON
    python3 scan.py "Manager" -l100 -e -s  Kombinasi

  OPTIONS:
    -l, --limit N    Max results (default: 20, max: 200)
    -e, --email      Cari email (lebih lambat, tapi dapet kontak)
    -s, --save       Save ke CSV + JSON
    -h, --help       Tampilkan ini

  DATA HIDUP SAJA: Hasil cuma ditampilkan di layar, 
  gak disimpan di database. --save kalo lo mau export.
""")

# ─── MAIN ───

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        show_help()
        sys.exit(0)
    
    keyword = sys.argv[1]
    limit = 20
    search_email_flag = False
    save_flag = False
    
    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg in ("-l", "--limit") and i + 1 < len(args):
            limit = min(int(args[i + 1]), 200)
        elif arg in ("-e", "--email"):
            search_email_flag = True
        elif arg in ("-s", "--save"):
            save_flag = True
    
    print(f"\n{'='*60}")
    print(f"  🔍 LinkedIn Scanner")
    print(f"  Keyword: \"{keyword}\"")
    print(f"  Limit:   {limit} profiles")
    if search_email_flag:
        print(f"  Email:   YES (slower)")
    if save_flag:
        print(f"  Save:    CSV + JSON")
    print(f"{'='*60}\n")
    
    # Search
    profiles = search_linkedin(keyword, limit=limit)
    
    if not profiles:
        print(f"\n  [!] No results. Coba keyword lebih umum atau Bahasa Inggris.\n")
        sys.exit(0)
    
    # Process & display
    ddgs = DDGS() if search_email_flag else None
    results = display_results(profiles, keyword, search_email_flag, ddgs)
    
    # Optional save
    if save_flag and results:
        save_results(results, keyword)
    
    print(f"  ✅ Done. Data cuma ada di layar — gak disimpan di database.\n")
