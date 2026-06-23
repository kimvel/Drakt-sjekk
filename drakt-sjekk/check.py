"""
Norge drakt-sjekk — ingen AI, ingen kostnad.
Sjekker butikker direkte og sender Discord-varsel ved funn.
"""

import os
import json
import hashlib
import requests
from datetime import datetime

# --- Konfig ---
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
SEEN_FILE = "seen.json"  # Husker hva som er varslet (lagres i GitHub Actions cache)

SIZES = ["L", "XL"]  # Størrelser å se etter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "no,en;q=0.9",
}

# --- Butikker med direkte URL + lagersignal ---
# "sold_out_signal": tekst som indikerer utsolgt
# "in_stock_signal": tekst som indikerer på lager (valgfritt)
STORES = [
    {
        "name": "Unisport",
        "url": "https://www.unisportstore.no/football-shirts/norway-home-shirt-world-cup-2026/461740/",
        "sold_out_signals": ["remind me", "varsle meg", "ikke på lager"],
        "size_signals": ["størrelse l", "størrelse xl", ">l<", ">xl<", '"L"', '"XL"'],
        "shop_url": "https://www.unisportstore.no/football-shirts/norway-home-shirt-world-cup-2026/461740/",
    },
    {
        "name": "Intersport",
        "url": "https://www.intersport.no/nike-norge-mens-stadium-home-jersey-2026-universityreddkhtm-unisex-ib5316",
        "sold_out_signals": ["ikke tilgjengelig", "utsolgt", "sold out"],
        "size_signals": [">l<", ">xl<", '"L"', '"XL"', "size-l", "size-xl"],
        "shop_url": "https://www.intersport.no/nike-norge-mens-stadium-home-jersey-2026-universityreddkhtm-unisex-ib5316",
    },
    {
        "name": "XXL",
        "url": "https://www.xxl.no/catalogsearch/result/?q=norge+hjemmedrakt+2026",
        "sold_out_signals": ["ingen resultater", "0 produkter"],
        "size_signals": ["norge", "hjemmedrakt", "2026"],
        "shop_url": "https://www.xxl.no/catalogsearch/result/?q=norge+hjemmedrakt+2026",
    },
    {
        "name": "Nike",
        "url": "https://www.nike.com/no/w?q=norge+drakt+2026&vst=norge+drakt+2026",
        "sold_out_signals": ["ingen resultater"],
        "size_signals": ["norway", "norge", "home jersey 2026"],
        "shop_url": "https://www.nike.com/no/w?q=norge+drakt+2026&vst=norge+drakt+2026",
    },
    {
        "name": "Sport 1",
        "url": "https://www.sport1.no/search?q=norge+drakt+2026",
        "sold_out_signals": ["ingen treff", "0 treff"],
        "size_signals": ["norge", "drakt", "2026"],
        "shop_url": "https://www.sport1.no/search?q=norge+drakt+2026",
    },
    {
        "name": "Anton Sport",
        "url": "https://www.antonsport.no/search?q=norge+drakt+2026",
        "sold_out_signals": ["ingen treff", "0 resultater"],
        "size_signals": ["norge", "drakt", "2026"],
        "shop_url": "https://www.antonsport.no/search?q=norge+drakt+2026",
    },
    {
        "name": "Torshov Sport",
        "url": "https://www.torshovsport.no/search?q=norge+drakt",
        "sold_out_signals": ["ingen treff", "0 resultater"],
        "size_signals": ["norge", "drakt"],
        "shop_url": "https://www.torshovsport.no/search?q=norge+drakt",
    },
]


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)


def check_store(store):
    """
    Returnerer (found: bool, sizes_found: list, error: str|None)
    """
    try:
        r = requests.get(store["url"], headers=HEADERS, timeout=15)
        html = r.text.lower()

        # Sjekk utsolgt-signal først
        for signal in store["sold_out_signals"]:
            if signal.lower() in html:
                return False, [], None

        # Sjekk om noen av størrelsene finnes
        sizes_found = []
        for size in SIZES:
            # Søk etter størrelse i HTML
            size_lower = size.lower()
            if (
                f">{size_lower}<" in html
                or f'value="{size_lower}"' in html
                or f'data-size="{size_lower}"' in html
                or f'"size":"{size_lower}"' in html
                or f"size-{size_lower}" in html
            ):
                sizes_found.append(size)

        # Sjekk generelle size_signals (for søkeresultat-sider)
        general_match = any(s.lower() in html for s in store["size_signals"])

        if sizes_found:
            return True, sizes_found, None
        elif general_match and not any(s.lower() in html for s in store["sold_out_signals"]):
            # Søkeside treffer — mulig funn, rapporter uten størrelsesbekreftelse
            return True, ["ukjent størrelse"], None

        return False, [], None

    except Exception as e:
        return False, [], str(e)


def send_discord(message):
    payload = {"content": message, "username": "🇳🇴 Drakt-bot"}
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)


def make_key(store_name, sizes):
    key_str = f"{store_name}-{'-'.join(sorted(sizes))}"
    return hashlib.md5(key_str.encode()).hexdigest()


def main():
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook:
        print("FEIL: DISCORD_WEBHOOK_URL ikke satt som secret!")
        raise SystemExit(1)

    seen = load_seen()
    found_any = False
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    print(f"[{now}] Starter sjekk av {len(STORES)} butikker...")

    for store in STORES:
        found, sizes, error = check_store(store)
        print(f"  {store['name']}: found={found}, sizes={sizes}, error={error}")

        if found and sizes:
            key = make_key(store["name"], sizes)
            if key not in seen:
                # Nytt funn — send varsel
                size_str = ", ".join(sizes)
                msg = (
                    f"🇳🇴 **Drakt funnet!**\n"
                    f"**Butikk:** {store['name']}\n"
                    f"**Størrelse:** {size_str}\n"
                    f"**Link:** {store['shop_url']}\n"
                    f"*{now}*"
                )
                send_discord(msg)
                seen[key] = now
                found_any = True
                print(f"  → Discord-varsel sendt for {store['name']} ({size_str})")
            else:
                print(f"  → Allerede varslet, hopper over")

    if not found_any:
        print("Ingen nye funn.")

    save_seen(seen)


if __name__ == "__main__":
    main()
