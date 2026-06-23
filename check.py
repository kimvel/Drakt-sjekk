"""
Norge drakt-sjekk med Playwright.
Kjører ekte Chromium, leser faktisk lagerdata, sender Discord-varsel ved funn.
"""

import os
import json
import hashlib
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
SEEN_FILE = "seen.json"
SIZES = ["L", "XL"]

STORES = [
    {
        "name": "Unisport",
        "url": "https://www.unisportstore.no/football-shirts/norway-home-shirt-world-cup-2026/461740/",
        "sold_out": ["varsle meg", "remind me", "not available"],
    },
    {
        "name": "Intersport",
        "url": "https://www.intersport.no/nike-norge-mens-stadium-home-jersey-2026-universityreddkhtm-unisex-ib5316",
        "sold_out": ["utsolgt", "sold out", "ikke tilgjengelig"],
    },
    {
        "name": "XXL",
        "url": "https://www.xxl.no/search?query=norge+hjemmedrakt+2026",
        "sold_out": ["ingen resultater", "0 produkter"],
    },
    {
        "name": "Nike",
        "url": "https://www.nike.com/no/t/norway-national-team-2026-stadium-dri-fit-fotballdrakt-xaR6u79T/IB5316-673",
        "sold_out": ["utsolgt", "sold out", "ikke tilgjengelig"],
    },
    {
        "name": "Sport 1",
        "url": "https://www.sport1.no/nike-norge-mens-stadium-home-jersey-2026-chile-redchile-redwhite-unisex-ib5316",
        "sold_out": ["utsolgt", "sold out", "ikke tilgjengelig"],
    },
    {
        "name": "Anton Sport",
        "url": "https://www.antonsport.no/search?q=norge+drakt+2026",
        "sold_out": ["ingen treff", "0 resultater"],
    },
    {
        "name": "Torshov Sport",
        "url": "https://www.torshovsport.no/fotball/kampanjer/vm-2026-fotballdrakter/nike-norge-herrelandslaget-vm-2026-fotballdrakt-hjemme",
        "sold_out": ["utsolgt", "sold out", "ikke tilgjengelig"],
    },
]


def find_sizes_in_text(text):
    """Kun treff på størrelse som faktisk er en kjøpbar variant."""
    found = []
    text_lower = text.lower()
    for size in SIZES:
        s = size.lower()
        patterns = [
            f'size-{s}"',
            f'size-{s} ',
            f'data-size="{s}"',
            f'data-value="{s}"',
            f'value="{s}"',
            f'"size":"{s}"',
            f'"size": "{s}"',
            f'["{s}"]',
            f'aria-label="{s}"',
            f'>{s}</button>',
            f'>{s}</option>',
            f'>{s}</span>',
            f'>{s}</a>',
            f'>{s}</li>',
        ]
        if any(p in text_lower for p in patterns):
            found.append(size)
    return found


def is_sold_out(text, sold_out_signals):
    text_lower = text.lower()
    return any(signal in text_lower for signal in sold_out_signals)


def check_store(page, store):
    try:
        page.goto(store["url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        text = page.content()
        if is_sold_out(text, store["sold_out"]):
            return [], "utsolgt", None
        sizes = find_sizes_in_text(text)
        return sizes, "sjekket", None
    except Exception as e:
        return [], "feil", str(e)


def send_discord(message):
    requests.post(
        DISCORD_WEBHOOK,
        json={"content": message, "username": "🇳🇴 Drakt-bot"},
        timeout=10,
    )


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)


def make_key(store_name, sizes):
    return hashlib.md5(f"{store_name}-{'-'.join(sorted(sizes))}".encode()).hexdigest()


def main():
    if not DISCORD_WEBHOOK:
        print("FEIL: DISCORD_WEBHOOK_URL mangler")
        raise SystemExit(1)

    mode = os.environ.get("RUN_MODE", "check")  # "check" eller "status"
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    print(f"[{now}] Modus: {mode} — sjekker {len(STORES)} butikker...")

    seen = load_seen()
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="nb-NO",
        )
        page = context.new_page()

        for store in STORES:
            sizes, status, error = check_store(page, store)
            results.append({"store": store, "sizes": sizes, "status": status, "error": error})
            print(f"  {store['name']}: status={status}, sizes={sizes}" + (f", feil={error}" if error else ""))

        browser.close()

    # --- Send varsler ved funn ---
    found_any = False
    for r in results:
        if r["sizes"]:
            key = make_key(r["store"]["name"], r["sizes"])
            if key not in seen:
                size_str = ", ".join(r["sizes"])
                send_discord(
                    f"🚨 **DRAKT PÅ LAGER!**\n"
                    f"**Butikk:** {r['store']['name']}\n"
                    f"**Størrelse:** {size_str}\n"
                    f"**Link:** {r['store']['url']}\n"
                    f"*{now}*"
                )
                seen[key] = now
                found_any = True
                print(f"  → Varsel sendt: {r['store']['name']} ({size_str})")
            else:
                print(f"  → Allerede varslet")

    # --- Status-melding (alltid ved manuell kjøring, aldri ved automatisk) ---
    if mode == "status" or (mode == "check" and not found_any):
        lines = [f"📋 **Drakt-status** — {now}", f"Søker: Norge hjemmedrakt VM 2026 herre, str. {', '.join(SIZES)}", ""]
        for r in results:
            name = r["store"]["name"]
            if r["error"]:
                lines.append(f"⚠️ {name} — feil ved sjekk")
            elif r["sizes"]:
                lines.append(f"✅ **{name} — PÅ LAGER: {', '.join(r['sizes'])}**")
            elif r["status"] == "utsolgt":
                lines.append(f"❌ {name} — utsolgt")
            else:
                lines.append(f"❌ {name} — ikke funnet")

        # Bare send til Discord hvis manuell kjøring (status-modus)
        if mode == "status":
            send_discord("\n".join(lines))

        print("\n".join(lines))

    if not found_any and mode == "check":
        print("Ingen nye funn i riktig størrelse.")

    save_seen(seen)


if __name__ == "__main__":
    main()
