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
    item["matched_area"] = area["name"]
    item["distance_km"] = round(dist, 2) if dist is not None else None
    return True


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

    listings, new_list, price_changes, history, first_run = store.reconcile(
        list(fresh.values()), log)
    favorites = store.load_favorites()
    store.save(listings, history)
    store.export_dashboard(listings, DOCS_DIR, build_criteria(), favorites)
    log(f"\nUloženo. Data pro tabulku: docs/data.json")

    # Na změnu ceny upozorňujeme jen u označených nemovitostí – u všech by to
    # byl každodenní spam. Seznam je v data/favorites.json, plní ho tabulka.
    fav_changes = [ch for ch in price_changes if ch["listing"]["id"] in set(favorites)]
    log(f"  Oblíbených: {len(favorites)}, z toho dnes změnilo cenu: {len(fav_changes)}")

    if first_run:
        log("  První běh – jen se naplní evidence, e-mail se neposílá "
            "(jinak by přišly stovky položek).")
    else:
        try:
            notify.send_email(new_list, fav_changes, config.SETTINGS, log)
        except Exception as e:  # noqa: BLE001
            log(f"  E-mail se nepodařilo odeslat: {e}")

    # Návratový kód: nenulový by shodil workflow, proto vždy 0.
    return 0


if __name__ == "__main__":
    sys.exit(main())
