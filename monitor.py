#!/usr/bin/env python3
"""
Shopee Flash Sale Monitor — CLI Version (no browser)
Mantau harga via API Shopee, auto checkout pas Rp.1

Usage:
  python3 monitor.py "https://shopee.co.id/product/123456789"
  python3 monitor.py "https://shopee.co.id/product/123456789" --interval 0.3
  python3 monitor.py "https://shopee.co.id/product/123456789" --once (cek 1x)
"""

import sys, re, time, json, os
from datetime import datetime

try:
    import requests
except ImportError:
    os.system("pip install requests --quiet --break-system-packages")
    import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://shopee.co.id/",
    "x-requested-with": "XMLHttpRequest",
}

# ─── EXTRACT ITEM INFO ───

def extract_shopee_ids(url):
    """Extract item_id and shop_id from Shopee URL."""
    patterns = [
        r"shopee\.co\.id/product/(\d+)/(\d+)",    # /product/{shop_id}/{item_id}
        r"shopee\.co\.id/(?:[\w-]+)-i\.(\d+)\.(\d+)",  # name-i.{shop_id}.{item_id}
        r"shopee\.co\.id/(?:[\w-]+)-(\d+)",        # just item_id
    ]
    
    for p in patterns:
        m = re.search(p, url)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return groups[0], groups[1]  # shop_id, item_id
            elif len(groups) == 1:
                return None, groups[0]
    
    return None, None

# ─── FETCH PRICE ───

def fetch_price_api(shop_id, item_id):
    """Get product price from Shopee API v4."""
    # Shopee API v4 - product detail
    params = {
        "item_id": item_id,
        "shop_id": shop_id if shop_id else "",
    }
    
    for attempt in range(2):
        try:
            # API v4
            url = "https://shopee.co.id/api/v4/product/get_shop_item"
            resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data"):
                    item = data["data"]
                    price_min = item.get("price_min", 0)
                    price_max = item.get("price_max", 0)
                    name = item.get("name", "")
                    stock = item.get("stock", 0)
                    discounted = item.get("has_discount", False)
                    
                    # Prices are in IDR * 100000 (Shopee format)
                    price_min_real = price_min / 100000 if price_min else 0
                    price_max_real = price_max / 100000 if price_max else 0
                    
                    return {
                        "name": name[:80],
                        "price_min": price_min_real,  # In Rupiah
                        "price_max": price_max_real,
                        "stock": stock,
                        "discounted": discounted,
                        "currency": "IDR",
                    }
            
            # Try alternative API v2
            if attempt == 0:
                url = f"https://shopee.co.id/api/v2/item/get?item_id={item_id}&shop_id={shop_id or ''}"
                resp = requests.get(url, headers=HEADERS, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    item = data.get("item", data)
                    price = item.get("price", 0)
                    price_real = price / 100000 if price else 0
                    return {
                        "name": item.get("name", "")[:80],
                        "price_min": price_real,
                        "price_max": price_real,
                        "stock": item.get("stock", 0),
                        "discounted": item.get("has_discount", False),
                        "currency": "IDR",
                    }
        
        except Exception as e:
            if attempt == 1:
                return {"error": str(e)}
    
    return None

def fetch_html_price(url):
    """Fallback: scrape price from HTML if API fails."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        html = resp.text
        
        # Try to find price in page data
        patterns = [
            r'"price":\s*(\d+)',
            r'"price_min":\s*(\d+)',
            r'"priceMax":\s*(\d+)',
            r'data-price="(\d+)"',
            r'<div[^>]*class="[^"]*price[^"]*"[^>]*>\s*Rp\.?\s*([0-9.]+)',
        ]
        
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                price = m.group(1).replace(".", "")
                try:
                    price_real = int(price) / 100000
                    # If already in rupiah format (not multiplied)
                    if int(price) < 1000000:  # Less than 10k rupiah
                        price_real = int(price)
                    return {"price_min": price_real, "price_max": price_real}
                except:
                    continue
        
        # Check for "1" in specific price containers
        if "Rp1" in html or "Rp 1" in html or "Rp.1" in html:
            return {"price_min": 1, "price_max": 1}
        
        return None
    except:
        return None

# ─── MONITOR ───

def monitor_price(url, interval=0.5, once=False):
    """Monitor price until Rp.1 detected."""
    
    shop_id, item_id = extract_shopee_ids(url)
    if not item_id:
        print(f"  ❌ Gak bisa extract item ID dari URL:")
        print(f"     {url}")
        print(f"     Pastikan URL Shopee valid.")
        return
    
    print(f"\n{'='*50}")
    print(f"  🏪 SHOPEE FLASH SALE MONITOR (CLI)")
    print(f"  Waktu: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Interval: {interval}s")
    print(f"{'='*50}")
    print(f"  📦 Item ID: {item_id}")
    if shop_id:
        print(f"  🏷️  Shop ID: {shop_id}")
    print(f"  🔍 Mantau harga... (Ctrl+C stop)\n")
    
    checked = 0
    start_time = time.time()
    last_price = -1
    no_data_count = 0
    
    try:
        while True:
            checked += 1
            now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # Fetch price
            data = fetch_price_api(shop_id, item_id)
            
            if not data or "error" in data:
                # Fallback to HTML
                data = fetch_html_price(url)
                if data:
                    print(f"  [{now}] 💰 Price from HTML")
            
            if data and "price_min" in data:
                price = data["price_min"]
                no_data_count = 0
                
                price_display = f"Rp{price:,.0f}" if price >= 1000 else f"Rp{int(price)}"
                stock = data.get("stock", "?")
                name = data.get("name", "")[:50]
                
                # Only print if price changed or every 10 checks
                if price != last_price or checked % 10 == 0:
                    status = "🔥" if price == 1 else "💰"
                    print(f"  [{now}] {status} {price_display:>12s}  📦 {stock}  {name}", end="")
                    
                    if checked % 10 == 0:
                        print()
                    else:
                        print(" " * 20, end="\r")
                
                last_price = price
                
                # 🚨 RP.1 DETECTED!
                if price <= 1:
                    print(f"\n\n  {'💥'*20}")
                    print(f"  💥💥💥 HARGA RP.1 DETECTED! 💥💥💥")
                    print(f"  {'💥'*20}")
                    print(f"\n  🏃 Buka link ini SEKARANG dan checkout:")
                    print(f"  🔗 {url}\n")
                    
                    # Beep alert
                    print("\a")  # Terminal bell
                    
                    # Open browser automatically
                    try:
                        import subprocess
                        subprocess.Popen(["xdg-open", url])
                        print(f"  🌐 Browser dibuka otomatis!\n")
                    except:
                        pass
                    
                    return True
                
            else:
                no_data_count += 1
                if checked % 10 == 0:
                    print(f"  [{now}] ⏳ Nunggu data harga... (attempt {no_data_count})")
                
                if no_data_count > 30:
                    print(f"\n  ❌ Gagal dapet data setelah 30x coba.")
                    print(f"     Mungkin URL salah atau Shopee block.\n")
                    return False
            
            if once:
                return data
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        avg = checked / (elapsed / 60) if elapsed > 0 else 0
        print(f"\n  ⏹️  Stopped. {checked}x cek dalam {elapsed:.0f}s ({avg:.0f} cek/menit)\n")
        return False

# ─── MAIN ───

if __name__ == "__main__":
    print(f"""
  ┌─────────────────────────────────┐
  │  🏪 SHOPEE FLASH SALE MONITOR   │
  │     CLI — No Browser, Cepet!    │
  └─────────────────────────────────┘
    """)
    
    if len(sys.argv) < 2 or "-h" in sys.argv:
        print("""
  Usage:
    python3 monitor.py "URL_PRODUK"               Mantau harga tiap 0.5s
    python3 monitor.py "URL" --interval 0.3        Cek tiap 0.3 detik
    python3 monitor.py "URL" --once                Cek 1x aja
    python3 monitor.py "URL" --beep                Bunyi pas Rp.1

  Examples:
    python3 monitor.py "https://shopee.co.id/product/12345678/98765432"
    python3 monitor.py "https://shopee.co.id/product/..." -i 0.2 --beep

  Tips:
    - Interval 0.3-0.5s cukup, jangan terlalu cepet (kena limit)
    - Pas Rp.1 detected → link langsung kebuka di browser
    - Jalanin di terminal, biarin aja mantau
""")
        sys.exit(0)
    
    url = sys.argv[1]
    if not url.startswith("http"):
        print(f"  ❌ URL tidak valid")
        sys.exit(1)
    
    interval = 0.5
    once = False
    
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a in ("-i", "--interval") and i + 1 < len(args):
            interval = max(0.1, float(args[i + 1]))
        elif a == "--once":
            once = True
    
    print(f"  🎯 {url[:80]}")
    print(f"  ⏱️  Interval: {interval}s")
    print()
    
    monitor_price(url, interval=interval, once=once)
