# -*- coding: utf-8 -*-
"""Ukládání dat, výpočet novinek/změn a historie."""

import json
import os
from datetime import date, datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LISTINGS_FILE = os.path.join(DATA_DIR, "listings.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")


def _today():
    return date.today().isoformat()


def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def load_listings():
    """Vrátí uložené inzeráty jako slovník {id: záznam}."""
    return _load(LISTINGS_FILE, {})


def load_history():
    return _load(HISTORY_FILE, [])


def load_favorites():
    """
    Vrátí seznam id oblíbených nemovitostí z data/favorites.json.

    Soubor plní tabulka (tlačítkem „Uložit do repozitáře“), dá se ale klidně
    upravit i ručně. Očekává se tvar {"ids": ["sreality:123", ...]}; kvůli
    ručním úpravám bereme i holý seznam id.
    """
    data = _load(FAVORITES_FILE, {})
    ids = data.get("ids") if isinstance(data, dict) else data
    if not isinstance(ids, list):
        return []
    return [i for i in ids if isinstance(i, str)]


def active_count():
    """Kolik inzerátů je v evidenci vedeno jako stále v nabídce."""
    return sum(1 for r in load_listings().values() if not r.get("removed_on"))


def reconcile(fresh_items, log):
    """
    Porovná čerstvě stažené inzeráty s uloženými.
    Vrací (all_listings, new_list, price_changes, gone_list, history, first_run).

    Do každého záznamu doplní:
      first_seen, last_seen, removed_on, price_history, is_new
    """
    stored = load_listings()
    history = load_history()
    today = _today()
    first_run = len(stored) == 0

    fresh_by_id = {it["id"]: it for it in fresh_items}
    new_list = []
    price_changes = []
    gone_list = []

    # 1) projdi čerstvé -> nové nebo aktualizace
    for lid, it in fresh_by_id.items():
        if lid in stored:
            rec = stored[lid]
            # obnov "živá" pole z čerstvých dat
            old_price = rec.get("price")
            rec.update({k: it[k] for k in it})  # přepiš aktuálními hodnotami
            rec["last_seen"] = today
            rec["removed_on"] = None
            rec["is_new"] = False
            if old_price != it.get("price") and it.get("price"):
                rec.setdefault("price_history", []).append(
                    {"date": today, "price": it.get("price")})
                # starou cenu si neseme zvlášť – v záznamu už je přepsaná novou
                price_changes.append({"listing": rec, "old_price": old_price,
                                      "new_price": it.get("price")})
                history.append({"date": today, "event": "price_changed", "id": lid,
                                "title": rec.get("title"), "old_price": old_price,
                                "new_price": it.get("price"), "url": rec.get("url")})
        else:
            it["first_seen"] = today
            it["last_seen"] = today
            it["removed_on"] = None
            it["is_new"] = True
            it["price_history"] = [{"date": today, "price": it.get("price")}] if it.get("price") else []
            stored[lid] = it
            new_list.append(it)
            history.append({"date": today, "event": "appeared", "id": lid,
                            "title": it.get("title"), "price": it.get("price"),
                            "area": it.get("matched_area"), "url": it.get("url")})

    # 2) inzeráty, které zmizely z nabídky
    for lid, rec in stored.items():
        if lid not in fresh_by_id and not rec.get("removed_on"):
            rec["removed_on"] = today
            rec["is_new"] = False
            gone_list.append(rec)
            history.append({"date": today, "event": "removed", "id": lid,
                            "title": rec.get("title"), "url": rec.get("url")})

    log(f"  Nových: {len(new_list)}, změn ceny: {len(price_changes)}, "
        f"zmizelo: {len(gone_list)}, celkem v evidenci: {len(stored)}")
    return stored, new_list, price_changes, gone_list, history, first_run


def save(listings, history):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LISTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=1, sort_keys=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=1)


def export_dashboard(listings, docs_dir, criteria=None, favorites=None):
    """
    Uloží data pro webovou tabulku do docs/data.json.

    `criteria` je popis toho, podle čeho se hledalo (viz run.py) – tabulka ho
    ukazuje v rozbalovacím panelu, aby bylo vidět, proč se co zobrazuje.
    `favorites` je seznam oblíbených z repozitáře; tabulka podle něj pozná,
    které označené nemovitosti už hlídá i e-mail.
    """
    os.makedirs(docs_dir, exist_ok=True)
    # seřaď: nejdřív nové, pak podle data (nejnovější nahoře)
    rows = sorted(listings.values(),
                  key=lambda r: (not r.get("is_new"), r.get("first_seen", "")),
                  reverse=False)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "count": len(rows),
        "criteria": criteria or {},
        "favorites": sorted(favorites or []),
        "listings": rows,
    }
    with open(os.path.join(docs_dir, "data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
