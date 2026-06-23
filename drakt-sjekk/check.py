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
        "size_selector": None,  # Bruker tekstsøk
    },
    {
        "name": "Intersport",
        "url": "https://www.intersport.no/nike-norge-mens-stadium-home-jersey-2026-universityreddkhtm-unisex-ib5316",
        "sold_out": ["utsolgt", "sold out", "ikke tilgjengelig"],
        "size_selector": None,
    },
    {
        "name": "XXL",
        "url": "https://www.xxl.no/search?query=norge+hjemmedrakt+2026",
        "sold_out": ["ingen resultater", "0 produkter"],
        "size_selector": None,
    },
    {
        "name": "Nike",
        "url": "https://www.nike.com/no/w?q=norge+hjemmedrakt+2026&vst=norge+hjemmedrakt+2026",
        "sold_out": ["ingen resultater"],
        "size_selector": None,
    },
    {
        "name": "Sport 1",
        "url": "https://www.sport1.no/search?q=norge+drakt+2026",
        "sold_out": ["ingen treff", "0 treff"],
        "size_selector": None,
    },
    {
        "name": "Anton Sport",
        "url": "https://www.antonsport.no/search?q=norge+drakt+2026",
        "sold_out": ["ingen treff", "0 resultater"],
        "size_selector": None,
    },
    {
        "name": "Torshov Sport",
        "url": "https://www.torshovsport.no/search?q=norge+drakt+2026",
        "sold_out": ["ingen treff", "0 resultater"],
        "size_selector": None,
    },
]


def find_sizes_in_text(text):
    """Finn hvilke av SIZES som er tilgjengelige i sideteksten."""
    found = []
    text_lower = text.lower()
    for size in SIZES:
        s = size.lower()
        # Ser etter størrelsen som eget ord/element, ikke som del av andre ord
        patterns = [
            f'"{s}"',
            f"'{s}'",
            f">{s}<",
            f"size-{s}",
            f"value=\"{s}\"",
            f"data-size=\"{s}\"",
            f" {s} ",
            f"/{s}/",
        ]
        if any(p in text_lower for p in patterns):
            found.append(size)
    return found


def is_sold_out(text, sold_out_signals):
    text_lower = text.lower()
    return any(signal in text_lower for signal in sold_out_signals)


def check_store(page, store):
    """
    Returnerer (sizes_found: list, error: str|None)
    """
    try:
        page.goto(store["url"], wait_until="domcontentloaded", timeout=30000)
        # Vent litt på JS-rendring
        page.wait_for_timeout(3000)

        text = page.content()

        if is_sold_out(text, store["sold_out"]):
            return [], None

        sizes = find_sizes_in_text(text)
        return sizes, None

    except Exception as e:
        return [], str(e)


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

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    print(f"[{now}] Starter Playwright-sjekk av {len(STORES)} butikker...")

    seen = load_seen()
    found_any = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="nb-NO",
        )
        page = context.new_page()

        for store in STORES:
            sizes, error = check_store(page, store)
            status = f"sizes={sizes}" + (f", feil={error}" if error else "")
            print(f"  {store['name']}: {status}")

            if sizes:
                key = make_key(store["name"], sizes)
                if key not in seen:
                    size_str = ", ".join(sizes)
                    msg = (
                        f"🇳🇴 **Drakt på lager!**\n"
                        f"**Butikk:** {store['name']}\n"
                        f"**Størrelse:** {size_str}\n"
                        f"**Link:** {store['url']}\n"
                        f"*{now}*"
                    )
                    send_discord(msg)
                    seen[key] = now
                    found_any = True
                    print(f"  → Varsel sendt: {store['name']} ({size_str})")
                else:
                    print(f"  → Allerede varslet")

        browser.close()

    if not found_any:
        print("Ingen nye funn i riktig størrelse.")

    save_seen(seen)


if __name__ == "__main__":
    main()
