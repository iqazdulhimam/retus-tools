#!/usr/bin/env python3
"""
Shopee Flash Sale Monitor — CLI-friendly, lightweight
Pantau harga flash sale via headless browser

PENTING: Shopee block semua API request. Satu-satunya cara ya pake browser.
Tapi browser bisa di-headless (gak kelihatan) + disable gambar/css biar enteng.

Usage:
  python3 shopee.py "URL_PRODUK"          # Mode monitor (headless, ringan)
  python3 shopee.py "URL" --visible       # Mode auto-buy (kelihatan)
  python3 shopee.py "URL" --interval 0.3  # Cek tiap 0.3 detik
"""

import sys, re, time, os
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    import webdriver_manager.chrome
except ImportError:
    print("  📦 Installing dependencies...")
    os.system("pip install selenium webdriver-manager --quiet --break-system-packages 2>/dev/null")
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    import webdriver_manager.chrome

# ─── LAUNCH BROWSER ───

def create_driver(headless=True):
    """Create lightweight Chrome driver (headless, no images/CSS)."""
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    
    # ── Performance optimizations ──
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-images")
    options.add_argument("--disable-javascript")  # No JS animations
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    # ── Anti-detection ──
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # ── Load page strategy ──
    options.page_load_strategy = "eager"  # Don't wait for all resources
    
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    # Anti-detection CDP command
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        """
    })
    
    return driver

# ─── GET PRICE FROM SHOPEE ───

def get_price(driver):
    """Extract price from Shopee product page."""
    # Multiple price selector patterns
    selectors = [
        "//div[contains(@class, 'price')]//span",
        "//span[contains(@class, 'price')]",
        "//div[@data-testid='product-price']",
        "//div[contains(@class, 'product-price')]",
        "//div[text()*='Rp']",
        "//span[text()*='Rp']",
    ]
    
    for sel in selectors:
        try:
            els = driver.find_elements(By.XPATH, sel)
            for el in els:
                text = el.text.strip()
                if not text:
                    continue
                # Extract numeric price
                clean = re.sub(r'[^\d]', '', text)
                if clean and len(clean) >= 3:  # Min Rp1.000
                    return int(clean), text[:30]
        except:
            continue
    
    return None, None

# ─── MONITOR MODE ───

def monitor_mode(url, interval=1.0):
    """Monitor price changes, notify on Rp.1."""
    print(f"\n  🚀 Starting headless Chrome...")
    driver = create_driver(headless=True)
    
    print(f"  🌐 Loading page...")
    driver.set_page_load_timeout(15)
    
    try:
        driver.get(url)
    except:
        pass  # Timeout is fine, page may have loaded partially
    
    time.sleep(2)  # Wait for dynamic content
    
    # Extract product name
    title = driver.title[:60] if driver.title else url[:50]
    print(f"  📄 {title}")
    print(f"\n{'='*50}")
    print(f"  🏪 MONITOR: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  ⏱️  Interval: {interval}s")
    print(f"  👻 Headless: YES (ringan)")
    print(f"{'='*50}\n")
    
    checked = 0
    start_time = time.time()
    last_price = 0
    
    try:
        while True:
            checked += 1
            now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # Refresh page
            try:
                driver.refresh()
                time.sleep(1.5)
            except:
                try:
                    driver.get(url)
                    time.sleep(2)
                except:
                    pass
            
            price_val, price_text = get_price(driver)
            
            if price_val:
                # Shopee format: price * 100000
                price_rp = price_val / 100000
                
                if price_rp != last_price or checked % 5 == 0:
                    status = "🔥" if price_rp <= 1 else "💰"
                    print(f"  [{now}] {status} Rp{price_rp:,.0f}", end="")
                    if checked % 5 == 0:
                        print(f"  [{checked}x]")
                    else:
                        print(" " * 10, end="\r")
                
                last_price = price_rp
                
                # 🚨 RP.1 DETECTED!
                if price_rp <= 1:
                    print(f"\n\n  {'💥'*30}")
                    print(f"  💥💥💥 HARGA RP.1 DETECTED! 💥💥💥")
                    print(f"  {'💥'*30}")
                    print(f"\n  🔗 BUKA LINK INI SEKARANG:")
                    print(f"  {url}\n")
                    
                    # Auto-open
                    try:
                        import subprocess
                        subprocess.Popen(["xdg-open", url])
                        print(f"  ✅ Browser dibuka otomatis!\n")
                    except:
                        pass
                    
                    break
            else:
                if checked % 5 == 0:
                    print(f"  [{now}] ⏳ Waiting for price data...")
    
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        cpm = checked / (elapsed / 60) if elapsed > 0 else 0
        print(f"\n  ⏹️  Stopped. {checked}x checks in {elapsed:.0f}s ({cpm:.0f} cek/menit)\n")
    
    driver.quit()

# ─── AUTO-BUY MODE (visible) ───

def autobuy_mode(url, interval=0.5):
    """Auto-buy when price hits Rp.1 (visible browser)."""
    print(f"\n  🚀 Starting visible Chrome...")
    driver = create_driver(headless=False)
    
    print(f"  🌐 Loading page...")
    driver.get(url)
    time.sleep(3)
    
    try:
        title = driver.title[:60]
    except:
        title = url[:60]
    
    print(f"\n{'='*50}")
    print(f"  🏪 AUTO-BUY: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  📄 {title}")
    print(f"{'='*50}\n")
    print(f"  🔍 Monitoring + Auto-click when Rp.1\n")
    
    checked = 0
    
    try:
        while True:
            checked += 1
            now = datetime.now().strftime('%H:%M:%S')
            
            # Refresh
            try:
                driver.refresh()
                time.sleep(1.5)
            except:
                try:
                    driver.get(url)
                    time.sleep(2)
                except:
                    pass
            
            price_val, price_text = get_price(driver)
            
            if price_val:
                price_rp = price_val / 100000
                print(f"  [{now}] 💰 Rp{price_rp:,.0f}")
                
                if price_rp <= 1:
                    print(f"\n  💥 Rp.1! Clicking Buy Now...")
                    
                    buy_clicked = False
                    for text in ["Beli Sekarang", "BELI SEKARANG", "Buy Now", "Beli"]:
                        try:
                            btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{text}')]")
                            driver.execute_script("arguments[0].click();", btn)
                            print(f"  ✅ Clicked: {text}")
                            buy_clicked = True
                            break
                        except:
                            continue
                    
                    if buy_clicked:
                        time.sleep(1.5)
                        
                        for text in ["Checkout", "CHECKOUT", "Pesan", "Bayar"]:
                            try:
                                btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{text}')]")
                                driver.execute_script("arguments[0].click();", btn)
                                print(f"  ✅ Checkout clicked!")
                                break
                            except:
                                continue
                        
                        print(f"\n  🎉 BERHASIL! Selesaikan pembayaran manual di browser.\n")
                        input("  Tekan Enter untuk tutup browser...")
                    else:
                        print(f"  ❌ Gagal klik. Mungkin CAPTCHA.\n")
                    
                    break
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n  ⏹️  Stopped.\n")
    
    driver.quit()

# ─── MAIN ───

if __name__ == "__main__":
    print(f"""
  ┌─────────────────────────────────────┐
  │  🏪 SHOPEE FLASH SALE TOOL          │
  │     Monitor + Auto-Buy Rp.1         │
  └─────────────────────────────────────┘
    """)
    
    if len(sys.argv) < 2 or "-h" in sys.argv:
        print("""
  Usage:
    python3 shopee.py "URL"              Monitor mode (headless, ringan)
    python3 shopee.py "URL" --visible    Auto-buy mode (kelihatan)
    python3 shopee.py "URL" -i 0.3       Interval 0.3 detik

  Mode Monitor:
    - Jalan di background, gak kelihatan
    - Pas harga Rp.1, langsung bunyi + buka browser
    - CPU/RAM minimal (headless Chrome)

  Mode Auto-buy:
    - Browser kelihatan
    - Auto klik Beli + Checkout pas Rp.1
    - Lo tinggal bayar

  Tips:
    - Interval 1-2s cukup. Jangan <0.5s (kena limit Shopee)
    - Biarin monitor jalan di terminal, pas harga turun otomatis notify
    - Pastikan udah login Shopee di Chrome default
""")
        sys.exit(0)
    
    url = sys.argv[1]
    visible = "--visible" in sys.argv
    interval = 1.0
    
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a in ("-i", "--interval") and i + 1 < len(args):
            interval = max(0.3, float(args[i + 1]))
    
    if visible:
        autobuy_mode(url, interval)
    else:
        monitor_mode(url, interval)
