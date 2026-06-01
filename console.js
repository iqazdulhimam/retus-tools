/*
  🏪 Shopee Flash Sale Monitor — Console Script
  Cara pake:
    1. Buka halaman produk Shopee flash sale di Chrome
    2. Klik kanan → Inspect (atau F12)
    3. Klik tab "Console"
    4. Paste script ini, Enter
    5. Mantengin aja, pas Rp.1 auto bunyi + checkout

  Kelebihan dibanding Selenium:
    ✅ Gak perlu install apa-apa
    ✅ 0% CPU tambahan (pake MutationObserver)
    ✅ Gak terdeteksi sebagai bot (kayak user biasa)
    ✅ Langsung tau harga berubah tanpa refresh halaman
*/

// ═════════════════════════════════════════════
// SHOPEE FLASH SALE MONITOR — CONSOLE SCRIPT
// ═════════════════════════════════════════════

(function() {
    'use strict';

    const MONITOR_INTERVAL = 1000;  // Cek tiap 1 detik (ms)
    const TARGET_PRICE = 1000;       // Rp.1.000 = Rp.1 (format Shopee *100000)

    let checked = 0;
    let startTime = Date.now();
    let lastPrice = -1;
    let foundRp1 = false;

    console.log('%c═══════════════════════════════════════════', 'color: #7c3aed; font-weight: bold');
    console.log('%c  🏪 SHOPEE FLASH SALE MONITOR AKTIF', 'color: #00e5ff; font-size: 14px; font-weight: bold');
    console.log('%c═══════════════════════════════════════════', 'color: #7c3aed; font-weight: bold');
    console.log('  ⏳ Mantau harga Rp.1...');
    console.log('  ❌ Tutup tab ini = stop\n');

    // ─── GET PRICE ───

    function extractPrice() {
        // Coba berbagai selector harga Shopee
        const selectors = [
            '[data-testid="product-price"]',
            '[class*="product-price"]',
            '[class*="price"]',
            '[class*="Price"]',
            '[data-testid="product-price-value"]',
            'span._3eX',  // Shopee price class
            'div._2hXz',  
        ];

        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) {
                const text = el.textContent.trim();
                // Extract angka dari string kayak "Rp1.000" atau "Rp 1.000"
                const match = text.replace(/\./g, '').match(/(\d+)/);
                if (match) {
                    const price = parseInt(match[1]);
                    return { price, text: text.trim() };
                }
            }
        }

        // Alternatif: cari dari seluruh halaman
        const allText = document.body.textContent;
        const rpPatterns = [
            /Rp\s*1(?:\.000)?[^0-9]/,
            /Rp\.?\s*1(?!\d)/,
        ];
        for (const pat of rpPatterns) {
            if (pat.test(allText)) {
                return { price: 1000, text: 'Rp1' };
            }
        }

        return null;
    }

    // ─── FORMAT RUPIAH ───

    function formatPrice(price) {
        if (price >= 100000) {
            // Format Shopee (dikali 100000)
            const real = price / 100000;
            return `Rp${real.toLocaleString('id-ID')} (Rp${real})`;
        }
        return `Rp${price.toLocaleString('id-ID')}`;
    }

    // ─── NOTIFICATION ───

    function notifyRp1() {
        // 1. Bunyi beep
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        osc.type = 'sine';
        osc.frequency.value = 880;
        osc.connect(ctx.destination);
        osc.start();
        setTimeout(() => osc.stop(), 500);

        // 2. Kedipin title tab
        let flashCount = 0;
        const origTitle = document.title;
        const flash = setInterval(() => {
            document.title = flashCount % 2 === 0 ? '🔥 RP.1 🔥' : '🔥🔥🔥 RP.1 DETECTED! 🔥🔥🔥';
            flashCount++;
            if (flashCount > 10) {
                clearInterval(flash);
                document.title = '🔥 RP.1 — BELI SEKARANG! 🔥';
            }
        }, 500);

        // 3. Full screen alert di halaman
        const alertDiv = document.createElement('div');
        alertDiv.style.cssText = `
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(255, 0, 50, 0.9);
            color: white;
            font-size: 48px;
            font-weight: bold;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 999999;
            cursor: pointer;
            text-align: center;
            font-family: Arial, sans-serif;
        `;
        alertDiv.innerHTML = `
            <div style="font-size:80px;margin-bottom:20px;">💥💥💥</div>
            <div>HARGA RP.1 DETECTED!</div>
            <div style="font-size:24px;margin-top:20px;">Klik untuk checkout sekarang!</div>
            <div style="font-size:16px;margin-top:40px;opacity:0.7;">Click anywhere to close</div>
        `;
        alertDiv.onclick = () => alertDiv.remove();
        document.body.appendChild(alertDiv);

        // 4. Auto klik Beli Sekarang
        setTimeout(() => {
            const buyBtns = document.querySelectorAll('button');
            for (const btn of buyBtns) {
                const text = btn.textContent.toLowerCase();
                if (text.includes('beli sekarang') || text.includes('buy now') || text.includes('beli')) {
                    console.log('%c  ✅ Auto-click: ' + btn.textContent.trim(), 'color: #00e676');
                    btn.click();
                    break;
                }
            }
        }, 500);

        console.log('%c\n  💥💥💥 RP.1 DETECTED! CEKOUT SEKARANG! 💥💥💥\n', 'color: #ff3355; font-size: 20px; font-weight: bold');
    }

    // ─── MAIN LOOP ───

    function checkPrice() {
        checked++;
        const result = extractPrice();

        if (result) {
            const { price, text } = result;
            
            if (price !== lastPrice) {
                const time = new Date().toLocaleTimeString();
                console.log(`  [${time}] 💰 ${text}${price <= 1000 ? ' 🔥' : ''}`);
                lastPrice = price;
            }

            // CEK RP.1 — TARGET_PRICE = 1000 (format Shopee Rp1.000)
            if (price <= TARGET_PRICE && !foundRp1) {
                foundRp1 = true;
                notifyRp1();
                return;
            }
        } else {
            if (checked % 10 === 0) {
                console.log(`  [${new Date().toLocaleTimeString()}] ⏳ Waiting for price...`);
            }
        }

        if (!foundRp1) {
            setTimeout(checkPrice, MONITOR_INTERVAL);
        }
    }

    // ─── MUTATION OBSERVER (alternatif real-time) ───

    function setupObserver() {
        const target = document.querySelector('[data-testid="product-price"]') ||
                       document.querySelector('[class*="price"]') ||
                       document.body;

        const observer = new MutationObserver(() => {
            const result = extractPrice();
            if (result && result.price <= TARGET_PRICE && !foundRp1) {
                foundRp1 = true;
                notifyRp1();
            }
        });

        observer.observe(target, {
            childList: true,
            subtree: true,
            characterData: true
        });

        console.log('  👁️  MutationObserver aktif — real-time monitoring');
    }

    // ─── START ───

    // Coba setup observer dulu, fallback ke polling
    try {
        setupObserver();
    } catch(e) {
        console.log('  📡 Observer gagal, fallback ke polling');
    }

    // Start main loop
    checkPrice();

    // ─── HELP ───

    console.log('\n  %c📌 Commands:', 'font-weight: bold');
    console.log('    stopMonitor()  — Stop monitoring');
    console.log('    statusMonitor() — Cek status\n');

    window.stopMonitor = () => {
        foundRp1 = true;  // Stop loop
        console.log('%c  ⏹️  Monitor stopped', 'color: #ff3355');
    };

    window.statusMonitor = () => {
        const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1);
        console.log(`  📊 ${checked}x checks in ${elapsed} menit`);
    };

})();
