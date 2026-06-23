# 🇳🇴 Norge Drakt-sjekk

Sjekker norske butikker automatisk for Norge VM-drakt 2026 og sender Discord-varsel ved funn.

**Kostnad: kr 0. Ingen AI-kall.**

## Oppsett (ca. 5 min)

### 1. Discord webhook
1. Åpne en Discord-kanal → **Rediger kanal** → **Integrasjoner** → **Webhooks**
2. Klikk **Ny webhook** → kopier URL-en

### 2. GitHub repo
1. Lag et nytt privat repo på GitHub
2. Last opp disse filene (eller push med git)
3. Gå til **Settings** → **Secrets and variables** → **Actions**
4. Klikk **New repository secret**:
   - Navn: `DISCORD_WEBHOOK_URL`
   - Verdi: webhook-URL fra steg 1

### 3. Aktiver Actions
- Gå til **Actions**-fanen i repoet og aktiver workflows

### 4. Test
- Klikk **Actions** → **Drakt-sjekk** → **Run workflow** for å kjøre manuelt

## Hvordan det fungerer

- Kjører hvert 30. minutt mellom 08:00–01:00 norsk tid
- Sjekker 7 butikker direkte (ingen AI, ingen tokens)
- Sender Discord-melding kun ved **nytt** funn (varsler ikke samme størrelse/butikk to ganger)
- `seen.json` caches mellom kjøringer i GitHub Actions

## Tilpass størrelser

Endre `SIZES`-listen i `check.py`:
```python
SIZES = ["L", "XL"]  # Legg til f.eks. "M", "XXL"
```
