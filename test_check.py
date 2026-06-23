"""
Testmodus — kjøres via GitHub Actions workflow_dispatch.
Sender detaljert rapport til Discord om hva som faktisk finnes på hver side.
"""

import os
import requests
from playwright.sync_api import sync_playwright

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
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
        "url": "https://www.nike.com/no/w?q=norge+hjemmedrakt+2026&vst=norge+hjemmedrakt+2026",
        "sold_out": ["ingen resultater"],
    },
    {
        "name": "Sport 1",
        "url": "https://www.sport1.no/search?q=norge+drakt+2026",
        "sold_out": ["ingen treff", "0 treff"],
    },
    {
        "name": "Anton Sport",
        "url": "https://www.antonsport.no/search?q=norge+drakt+2026",
        "sold_out": ["ingen treff", "0 resultater"],
    },
    {
        "name": "Torshov Sport",
        "url": "https://www.torshovsport.no/search?q=norge+drakt+2026",
        "sold_out": ["ingen treff", "0 resultater"],
    },
]


def send_discord(msg):
    # Discord har 2000 tegn-grense per melding
    for i in range(0, len(msg), 1900):
        requests.post(
            DISCORD_WEBHOOK,
            json={"content": msg[i:i+1900], "username": "🇳🇴 Drakt-test"},
            timeout=10,
        )


def check_store(page, store):
    lines = [f"**{store['name']}**"]
    try:
        page.goto(store["url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()

        if len(html) < 500:
            lines.append(f"⛔ Blokkert (kun {len(html)} tegn)")
            return "\n".join(lines)

        # Utsolgt-signaler
        for signal in store["sold_out"]:
            if signal in html.lower():
                lines.append(f"⛔ Utsolgt-signal: `{signal}`")

        # Synlig tekst — første 300 tegn
        visible = page.inner_text("body")[:300].replace("\n", " ").strip()
        lines.append(f"Tekst: `{visible}`")

        # Størrelsestreff
        for size in SIZES:
            hits = []
            text_lower = html.lower()
            s = size.lower()
            idx = 0
            while len(hits) < 3:
                pos = text_lower.find(s, idx)
                if pos == -1:
                    break
                snippet = html[max(0,pos-40):pos+len(s)+40].replace("\n"," ").strip()
                hits.append(f"`{snippet}`")
                idx = pos + 1
            if hits:
                lines.append(f"Str. {size}: {' | '.join(hits)}")
            else:
                lines.append(f"Str. {size}: ingen treff")

    except Exception as e:
        lines.append(f"❌ Feil: {e}")

    return "\n".join(lines)


def main():
    if not DISCORD_WEBHOOK:
        print("FEIL: DISCORD_WEBHOOK_URL mangler")
        raise SystemExit(1)

    send_discord("🔍 **Drakt-test startet** — sjekker alle butikker...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            locale="nb-NO",
        )
        page = context.new_page()

        for store in STORES:
            result = check_store(page, store)
            print(result)
            send_discord(result)

        browser.close()

    send_discord("✅ **Test ferdig**")


if __name__ == "__main__":
    main()
