# -*- coding: utf-8 -*-
"""Stahování inzerátů ze Sreality.cz (neoficiální JSON API /api/v1/estates/search)."""

import time
import urllib.parse

from . import http
from .geo import reach_km
from .model import make_listing, parse_areas_from_name, slugify

API = "https://www.sreality.cz/api/v1/estates/search"
PER_PAGE = 100

# Obrázkové CDN Seznamu (sdn.cz) holou adresu z API nevydá – vrátí 401.
# Pustí jen přesně ty úpravy obrázku, které používá web Sreality; cokoliv jiného
# je 400. Proto se adresa z API doplňuje o jeden z těchto ověřených řetězců.
_IMG_CARD = "?fl=res,800,600,3|shr,,20|webp,60"   # náhled u výpisu, ~100 kB
_IMG_THUMB = "?fl=res,100,100,1|jpg,80"           # miniatura do tabulky, ~3 kB


def _img_url(raw, transform):
    """Doplní protokol a povolenou úpravu obrázku. Bez ní CDN vrací 401."""
    if not raw:
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    return raw + transform

# category_main_cb -> část URL detailu
_MAIN_SEO = {1: "byt", 2: "dum", 3: "pozemek"}
# category_main_cb -> naše kategorie
_MAIN_TO_CATEGORY = {1: "byt", 2: "dum", 3: "pozemek"}


def search(search_cfg, area, settings, log):
    """
    Vrátí seznam normalizovaných inzerátů pro danou kategorii a lokalitu.
    Server Sreality umí filtrovat přímo podle GPS + poloměru (v km).
    Poloměr = velikost oblasti + okruh navíc (viz geo.reach_km).
    """
    s = search_cfg["sreality"]
    params = {
        "category_type_cb": 1,                     # prodej
        "category_main_cb": s["category_main_cb"],
        "locality_gps_lat": round(area["lat"], 6),
        "locality_gps_lon": round(area["lon"], 6),
        "locality_radius": max(0.5, round(reach_km(area), 1)),  # v km, min 0.5
        "price_from": search_cfg["price_from"],
        "price_to": search_cfg["price_to"],
        "per_page": PER_PAGE,
    }
    if s.get("category_sub_cb"):
        # více dispozic se odděluje čárkou (funguje jako "nebo")
        params["category_sub_cb"] = ",".join(str(x) for x in s["category_sub_cb"])
    if search_cfg.get("min_area_m2"):
        params["usable_area_from"] = search_cfg["min_area_m2"]

    out = []
    offset = 0
    total = None
    while True:
        params["offset"] = offset
        url = API + "?" + urllib.parse.urlencode(params, safe=",")
        try:
            data = http.get_json(url)
        except RuntimeError as e:
            log(f"    [sreality] chyba: {e}")
            break
        if total is None:
            total = (data.get("pagination") or {}).get("total", 0)
        results = data.get("results") or []
        if not results:
            break
        for e in results:
            item = _normalize(e, search_cfg)
            if item:
                out.append(item)
        offset += PER_PAGE
        if offset >= total or offset >= settings["max_per_query"]:
            break
        time.sleep(0.4)  # slušnost k serveru
    return out


def _total_price(e):
    """
    Celková cena za nemovitost.

    Pozor: u části inzerátů (typicky pole a jiné pozemky) uvádí Sreality
    v `price_czk` cenu ZA m² – celková cena je pak v `price_summary_czk`.
    Poznáme to podle jednotky (value 1 = „za nemovitost“, 3 = „za m²“).
    Když ani jedno pole není cena za nemovitost, radši vrátíme None
    („cena neuvedena“) než abychom ukázali jednotkovou cenu jako celkovou.
    """
    if (e.get("price_summary_unit_cb") or {}).get("value") == 1 and e.get("price_summary_czk"):
        return int(e["price_summary_czk"])
    if (e.get("price_unit_cb") or {}).get("value") == 1 and e.get("price_czk"):
        return int(e["price_czk"])
    return None


def _normalize(e, search_cfg):
    loc = e.get("locality") or {}
    lat = loc.get("gps_lat")
    lon = loc.get("gps_lon")
    if lat is None or lon is None:
        return None  # bez GPS neumíme zařadit do lokality

    main_cb = (e.get("category_main_cb") or {}).get("value")
    sub = (e.get("category_sub_cb") or {}).get("name")
    name = e.get("advert_name") or ""
    area_m2, land_m2 = parse_areas_from_name(name)

    price = _total_price(e)
    ppm2 = e.get("price_czk_m2")
    ppm2 = int(ppm2) if ppm2 else None

    # Server filtruje podle ceny v inzerátu – u „ceny za m²“ tedy podle jednotkové
    # ceny, ne celkové. Pole za 250 Kč/m² projde i při stropu 5 mil., ačkoliv
    # celkem stojí třeba 12 mil. Proto rozsah ověřujeme ještě jednou u sebe.
    if price is not None and not (search_cfg["price_from"] <= price <= search_cfg["price_to"]):
        return None

    hash_id = e.get("hash_id")
    main_seo = _MAIN_SEO.get(main_cb, "x")
    sub_seo = slugify(sub) if sub else "x"
    city_seo = loc.get("city_seo_name") or "x"
    url = f"https://www.sreality.cz/detail/prodej/{main_seo}/{sub_seo}/{city_seo}/{hash_id}"

    imgs = e.get("advert_images") or []
    raw_img = imgs[0] if imgs else None
    image = _img_url(raw_img, _IMG_CARD)
    image_thumb = _img_url(raw_img, _IMG_THUMB)

    address = ", ".join(x for x in [
        loc.get("street"), loc.get("citypart") or loc.get("city")
    ] if x)

    return make_listing(
        source="sreality",
        native_id=hash_id,
        category=_MAIN_TO_CATEGORY.get(main_cb, search_cfg["key"]),
        title=name,
        price=price,
        area_m2=area_m2,
        land_area_m2=land_m2,
        disposition=sub if main_cb == 1 else None,
        city=loc.get("city"),
        address=address or loc.get("city"),
        lat=lat,
        lon=lon,
        url=url,
        image=image,
        image_thumb=image_thumb,
        price_per_m2=ppm2,
    )
