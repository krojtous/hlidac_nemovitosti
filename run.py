# -*- coding: utf-8 -*-
"""
Hlídač nemovitostí – hlavní skript.

Spuštění:  python run.py

Projde Sreality.cz a Bezrealitky.cz podle nastavení v config.py, zařadí inzeráty
do sledovaných lokalit, uloží je, zvýrazní novinky, aktualizuje data pro webovou
tabulku a (pokud jsou nastavené údaje) pošle e-mail s novými nemovitostmi.
"""

import os
import sys

import config
from reality import bezrealitky, sreality, store, notify
from reality.geo import area_radius_km, nearest_area, reach_km

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def log(msg):
    print(msg, flush=True)


def assign_area(item):
    """Zjistí nejbližší sledovanou lokalitu; vrátí True, pokud inzerát spadá do některé."""
    area, dist = nearest_area(item.get("lat"), item.get("lon"), config.AREAS)
    if area is None:
        return False
    if not poloha_je_dost_presna(item, area):
        return False
    item["matched_area"] = area["name"]
    item["distance_km"] = round(dist, 2) if dist is not None else None
    return True


def poloha_je_dost_presna(item, area):
    """
    Zahodí inzeráty, u kterých portál zná jen obec.

    Takový inzerát dostane souřadnice středu obce, i když leží kdekoliv v ní.
    U vesnice to nevadí, u Liberce se pozemek „přestěhuje“ na náměstí a spadne
    do lokality, se kterou nemá nic společného. Bereme je proto jen tam, kde je
    sledovaná oblast dost velká na to, aby se do ní celá obec vešla.

    Sreality přesnost popisují dvěma poli, která se často neshodují – jeden
    inzerát na náměstí v Liberci má „municipality“ jen v entity_type, druhý jen
    v inaccuracy_type. Stačí proto, aby to bylo v jednom z nich.
    """
    if "municipality" not in (item.get("location_precision"),
                              item.get("location_inaccuracy")):
        return True
    return reach_km(area) >= config.SETTINGS["city_only_min_reach_km"]


def data_vypadaji_uplne(pocet_stazenych, log):
    """
    Pojistka proti tichému výpadku portálu.

    Když portál neodpoví nebo změní API, stáhne se málo (klidně nula) inzerátů.
    Evidence by pak celou nabídku označila za zmizelou, přepsala data a workflow
    by přitom skončil zeleně. Radši v takovém případě neuložíme nic a spadneme,
    ať je porucha vidět.

    Skutečný pokles nabídky bývá v jednotkách procent za den; propad na polovinu
    znamená problém na naší straně, ne na trhu.
    """
    aktivni = store.active_count()
    if aktivni == 0:
        return True  # první běh nebo prázdná evidence – není s čím porovnávat

    podil = pocet_stazenych / aktivni
    if podil >= config.SETTINGS["min_fresh_ratio"]:
        return True

    log("")
    log("!!! PODEZŘELE MÁLO DAT – nic se neukládá !!!")
    log(f"    Staženo {pocet_stazenych} inzerátů, v evidenci je jich {aktivni} "
        f"({podil:.0%}).")
    log("    Nejspíš neodpověděl některý portál nebo změnil API (viz CHYBA výše).")
    log("    Evidence i tabulka zůstávají beze změny, e-mail se neposílá.")
    log("    Když je propad opravdu skutečný (třeba po zúžení kritérií v config.py),")
    log("    spusť jednorázově s REALITY_FORCE=1 a evidence se srovná.")
    return False


def build_criteria():
    """
    Popis nastavení hledání pro tabulku – aby bylo vidět, podle čeho se vybírá
    a proč se nějaká nemovitost zobrazí (nebo nezobrazí).
    """
    sources = []
    if config.SETTINGS["use_sreality"]:
        sources.append("Sreality.cz")
    if config.SETTINGS["use_bezrealitky"]:
        sources.append("Bezrealitky.cz")
    return {
        "areas": [{
            "name": a["name"],
            "lat": a["lat"],
            "lon": a["lon"],
            "area_radius_km": area_radius_km(a),
            "radius_km": float(a.get("radius_km") or 0.0),
            "reach_km": round(reach_km(a), 2),
        } for a in config.AREAS],
        "searches": [{
            "label": s["label"],
            "price_from": s["price_from"],
            "price_to": s["price_to"],
            "min_area_m2": s.get("min_area_m2"),
        } for s in config.SEARCHES],
        "sources": sources,
    }


def collect():
    """Stáhne a zařadí všechny inzeráty. Vrací slovník {id: záznam}."""
    fresh = {}

    def add(item):
        if not assign_area(item):
            return
        # dedup: stejný inzerát mohl přijít z více dotazů – ponech ten s bližší lokalitou
        old = fresh.get(item["id"])
        if old is None or (item.get("distance_km") or 1e9) < (old.get("distance_km") or 1e9):
            fresh[item["id"]] = item

    for search_cfg in config.SEARCHES:
        log(f"\n▶ Kategorie: {search_cfg['label']}")

        if config.SETTINGS["use_sreality"]:
            for area in config.AREAS:
                try:
                    items = sreality.search(search_cfg, area, config.SETTINGS, log)
                    for it in items:
                        add(it)
                    log(f"  [sreality] {area['name']}: staženo {len(items)}")
                except Exception as e:  # noqa: BLE001 – nechceme, aby jeden dotaz shodil celý běh
                    log(f"  [sreality] {area['name']}: CHYBA {e}")

        if config.SETTINGS["use_bezrealitky"]:
            try:
                items = bezrealitky.search(search_cfg, config.SETTINGS, log)
                for it in items:
                    add(it)
                log(f"  [bezrealitky] staženo {len(items)} (celostátně, filtruje se lokálně)")
            except Exception as e:  # noqa: BLE001
                log(f"  [bezrealitky] CHYBA {e}")

    return fresh


def main():
    log("=== Hlídač nemovitostí ===")
    fresh = collect()
    log(f"\nCelkem inzerátů ve sledovaných lokalitách: {len(fresh)}")

    if not os.environ.get("REALITY_FORCE") and not data_vypadaji_uplne(len(fresh), log):
        return 1  # nenulový kód schválně: workflow zčervená a přijde upozornění

    listings, new_list, price_changes, gone_list, history, first_run = store.reconcile(
        list(fresh.values()), log)
    favorites = set(store.load_favorites())
    store.save(listings, history)
    store.export_dashboard(listings, DOCS_DIR, build_criteria(), favorites)
    log(f"\nUloženo. Data pro tabulku: docs/data.json")

    # Změnu ceny a zmizení hlásíme jen u označených nemovitostí – u všech by to
    # byl každodenní spam. Seznam je v data/favorites.json, plní ho tabulka.
    fav_changes = [ch for ch in price_changes if ch["listing"]["id"] in favorites]
    fav_gone = [rec for rec in gone_list if rec["id"] in favorites]
    log(f"  Oblíbených: {len(favorites)}, z toho dnes změnilo cenu: {len(fav_changes)}, "
        f"zmizelo z nabídky: {len(fav_gone)}")

    if first_run:
        log("  První běh – jen se naplní evidence, e-mail se neposílá "
            "(jinak by přišly stovky položek).")
    else:
        try:
            notify.send_email(new_list, fav_changes, fav_gone, config.SETTINGS, log)
        except Exception as e:  # noqa: BLE001
            log(f"  E-mail se nepodařilo odeslat: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
