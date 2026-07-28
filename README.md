# 🏠 Hlídač nemovitostí

Automaticky sleduje nabídku nemovitostí na **Sreality.cz** a **Bezrealitky.cz**
ve vybraných lokalitách. Jednou denně projde inzeráty, uloží je, **zvýrazní nové**,
pošle **e-mail** s novinkami a udržuje **přehlednou tabulku** s historií.

## Co hlídá (výchozí nastavení)

| Kategorie | Podmínky |
|---|---|
| Dům se zahradou | cena do 12 mil. Kč |
| Byt 4+1 / 4+kk | plocha od 80 m², cena do 12 mil. Kč |
| Pozemek | cena do 5 mil. Kč |

**Lokality** – vždy *celá oblast + okruh navíc* kolem ní:

| Lokalita | Velikost oblasti | Okruh navíc | Hledá se do |
|---|---|---|---|
| Vratislavice nad Nisou | 2,0 km | 1,0 km | 3,0 km |
| Vlašim | 2,5 km | 15,0 km | 17,5 km |
| Ruprechtice – Liberec | 1,5 km | 1,2 km | 2,7 km |
| Masarykova třída – Liberec | 0,5 km | 0,5 km | 1,0 km |

Vše se dá změnit v souboru [`config.py`](config.py) – je bohatě okomentovaný.

## Jak to funguje

```
run.py  ──►  stáhne inzeráty (Sreality + Bezrealitky)
        ──►  zařadí je do lokalit podle GPS (poloměr)
        ──►  porovná s minulým stavem → nové / změna ceny / zmizelé
        ──►  uloží data + historii, připraví tabulku, pošle e-mail
```

- Data: [`data/listings.json`](data/listings.json) – aktuální stav všech inzerátů
- Historie: [`data/history.json`](data/history.json) – kdy co přibylo / zdražilo / zmizelo
- Tabulka: [`docs/index.html`](docs/index.html) – interaktivní, řaditelná

Skript používá **jen standardní knihovnu Pythonu** – nic se neinstaluje.

---

## A) Vyzkoušení na svém počítači

Potřebuješ nainstalovaný Python 3.11+.

```bash
python run.py
```

Pak otevři tabulku. Kvůli prohlížečovému omezení ji spusť přes malý server:

```bash
cd docs
python -m http.server 8000
# a v prohlížeči otevři http://localhost:8000
```

> Pokud počítač hlásí chybu certifikátu u Bezrealitky, spusť jednorázově:
> `set REALITY_INSECURE_SSL=1` (Windows) a pak `python run.py`. V cloudu to není potřeba.

E-mail se lokálně neposílá, dokud nenastavíš přihlašovací údaje (viz níže) –
novinky ale uvidíš v tabulce.

---

## B) Automatický běh v cloudu zdarma (GitHub Actions)

Takto poběží každý den sám, i když máš počítač vypnutý.

### 1. Nahraj projekt na GitHub
Založ nový repozitář (klidně soukromý) a nahraj do něj tyto soubory.

### 2. Nastav e-mail (GitHub Secrets)
V repozitáři: **Settings → Secrets and variables → Actions → New repository secret**
a přidej tři položky:

| Název | Hodnota |
|---|---|
| `SMTP_USER` | tvoje gmailová adresa, např. `matousp@gmail.com` |
| `SMTP_PASS` | **App Password** z Google (viz níže) |
| `MAIL_TO` | kam posílat upozornění (např. `matousp@gmail.com`) |

**App Password** = jednorázové heslo pro aplikace:
Google účet → *Zabezpečení* → zapni *dvoufázové ověření* →
*Hesla aplikací* → vytvoř heslo a zkopíruj ho do `SMTP_PASS`.
(Běžné heslo k účtu Gmail přes SMTP nepustí.)

> Bez těchto údajů skript poběží dál, jen nepošle e-mail (novinky budou v tabulce).

### 3. Zapni tabulku na webu (GitHub Pages)
**Settings → Pages → Build and deployment → Source: „Deploy from a branch“**,
branch `main`, složka **`/docs`**. Po chvíli bude tabulka na adrese
`https://<tvé-jméno>.github.io/<repo>/`.

### 4. Hotovo
Workflow [`.github/workflows/daily.yml`](.github/workflows/daily.yml) se spustí
každý den ráno. Ručně ho vyzkoušíš v záložce **Actions → Hlídač nemovitostí → Run workflow**.

---

## Tabulka – co umí
- **Řazení** kliknutím na hlavičku sloupce (cena, plocha, Kč/m², vzdálenost, datum…)
- **Filtry**: lokalita, typ, portál, „jen nové“, „skrýt zmizelé“
- **Hledání** v názvu a adrese
- **Zvýraznění nových** (žlutý štítek *NOVÉ*), zmizelé jsou přeškrtnuté
- Náhledový obrázek a klikací odkaz přímo na inzerát

## Úpravy hledání
Otevři [`config.py`](config.py) a uprav:
- `AREAS` – lokality. GPS střed si ověříš na mapě, k němu dvě čísla:
  - `area_radius_km` – jak je velká **samotná oblast** (od středu k jejímu okraji),
  - `radius_km` – **okruh navíc** kolem oblasti.

  Hledá se v jejich součtu. „Vratislavice + 1 km“ tedy znamená celé Vratislavice
  a k tomu ještě kilometr okolo, ne jen kilometr od návsi.
- `SEARCHES` – ceny, minimální plochu, typy.

> Po větší změně lokalit doporučuji smazat soubory v `data/`, aby se evidence
> „srovnala“ znovu podle nových kritérií (jinak se posun může projevit jako spousta
> nových / zmizelých položek).

## Časté otázky
- **Přijde e-mail každý den?** Ne. Jen když opravdu přibyla nová nemovitost.
- **První běh** naplní evidenci a e-mail schválně nepošle (bylo by tam stovky položek).
- **Portály změní API?** Pak stačí upravit soubory v `reality/`. Endpointy byly ověřeny
  v červenci 2026 (Sreality: `api/v1/estates/search`, Bezrealitky: GraphQL `listAdverts`).
