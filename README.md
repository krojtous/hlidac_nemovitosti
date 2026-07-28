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

Skript stojí na standardní knihovně Pythonu, jediná závislost je **`certifi`** –
aktuální seznam certifikačních autorit (viz níže).

---

## A) Vyzkoušení na svém počítači

Potřebuješ nainstalovaný Python 3.11+.

```bash
python -m pip install -r requirements.txt
```

```bash
python run.py
```

Pak otevři tabulku. Kvůli prohlížečovému omezení ji spusť přes malý server:

```bash
cd docs
python -m http.server 8000
# a v prohlížeči otevři http://localhost:8000
```

> **Chyba certifikátu u Bezrealitky?** Windows si drží jen ty certifikační autority,
> na které kdy narazil, a Python pak hlásí `certificate has expired` i u serveru
> s platným certifikátem. Řeší to balíček `certifi` z `requirements.txt`; když se
> chyba objeví znovu, stačí ho aktualizovat:
>
> ```bash
> python -m pip install --upgrade certifi
> ```
>
> Úplně nouzově jde ověřování vypnout přes `set REALITY_INSECURE_SSL=1` (Windows),
> ale pak se s protistranou komunikuje bez kontroly totožnosti – ber to jako
> poslední možnost, ne jako běžné řešení.

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
| `SMTP_USER` | gmailová adresa, ze které se odesílá |
| `SMTP_PASS` | **App Password** z Google (viz níže) |
| `MAIL_TO` | adresa, kam upozornění chodí |

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
- **Panel „Podle čeho se hledá“** nad tabulkou – rozbalí přehled lokalit
  (oblast + okruh + celkový dosah), cenových stropů a minimálních ploch,
  takže je vidět, proč se nemovitost zobrazí nebo nezobrazí
- **Řazení** kliknutím na hlavičku sloupce (cena, plocha, Kč/m², vzdálenost, datum…)
- **Filtry**: lokalita, typ, portál, „jen nové“, „jen oblíbené“, „skrýt zmizelé“
- **Hledání** v názvu a adrese
- **Kč/m²** – když ho portál neuvádí, dopočítá se z ceny a plochy
- **Zvýraznění nových** (žlutý štítek *NOVÉ*), zmizelé jsou přeškrtnuté
- **Označování hvězdičkou** (viz níže) – dá se podle ní i řadit a filtrovat
- Náhledový obrázek a klikací odkaz přímo na inzerát

## Oblíbené nemovitosti a hlídání ceny

Hvězdičkou v prvním sloupci si označíš nemovitosti, které tě zaujaly.
**U označených chodí e-mail i při změně ceny a když zmizí z nabídky**
(typicky prodej) – u ostatních ne, jinak by upozornění chodila každý den.

Označení se ukládá do prohlížeče, takže je okamžité a funguje i offline.
Aby o něm ale věděl i hlídač v cloudu (ten e-maily posílá), musí se seznam
dostat do repozitáře:

1. V tabulce rozbal panel **Oblíbené** – ukazuje, kolik označených ještě není uloženo.
2. **Zkopírovat** → **Otevřít favorites.json na GitHubu** → přepsat obsah
   (Ctrl+A, Ctrl+V) → **Commit changes**.
3. Od dalšího běhu hlídač sleduje cenu přesně u těchto nemovitostí.

Tlačítko **Načíst seznam z repozitáře** jde opačným směrem – hodí se na dalším
zařízení (mobil, druhý počítač), aby mělo stejný výběr.

Seznam je v [`data/favorites.json`](data/favorites.json) a je to obyčejný
seznam id, takže se dá upravit i ručně.

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

## Když workflow zčervená

Hlídač schválně **skončí chybou, když stáhne podezřele málo inzerátů** (méně než
polovinu toho, co má v evidenci). Bez téhle pojistky by nedostupný portál vypadal
jako by ze dne na den zmizela celá nabídka – evidence by se přepsala a workflow
by přitom skončil zeleně.

Když ti tedy z GitHubu přijde upozornění na neúspěšný běh:

1. Otevři log v **Actions** a najdi řádky se slovem `CHYBA` – ukážou, který portál
   neodpověděl.
2. Většinou jde o dočasný výpadek a další den se to spraví samo. **Data zůstala
   nedotčená**, nic se neztratilo.
3. Když se to opakuje, portál nejspíš změnil API – opravit je potřeba soubory
   v `reality/`.
4. Pokud je propad skutečný (třeba jsi zúžil kritéria v `config.py`), spusť
   jednorázově s `REALITY_FORCE=1` a evidence se srovná. Práh se dá změnit
   v `config.py` položkou `min_fresh_ratio`.

## Časté otázky
- **Přijde e-mail každý den?** Ne. Jen když přibyla nová nemovitost nebo se
  u některé z oblíbených změnila cena či zmizela z nabídky.
- **První běh** naplní evidenci a e-mail schválně nepošle (bylo by tam stovky položek).
- **Portály změní API?** Pak stačí upravit soubory v `reality/`. Endpointy byly ověřeny
  v červenci 2026 (Sreality: `api/v1/estates/search`, Bezrealitky: GraphQL `listAdverts`).
