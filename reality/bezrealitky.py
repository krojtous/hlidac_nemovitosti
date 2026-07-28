# -*- coding: utf-8 -*-
"""
Stahování inzerátů z Bezrealitky.cz (GraphQL API).

Poznámka: GPS filtr na jejich API nefiltruje spolehlivě, proto stáhneme všechny
inzeráty dané kategorie (je jich řádově stovky) a do lokalit je zařadíme sami
podle GPS (haversine) až v run.py.
"""

import time

from . import http
from .model import make_listing, parse_areas_from_name

API = "https://api.bezrealitky.cz/graphql/"
LIMIT = 100

# Bezrealitky disposition -> lidský popis
_DISP = {
    "DISP_1_KK": "1+kk", "DISP_1_1": "1+1",
    "DISP_2_KK": "2+kk", "DISP_2_1": "2+1",
    "DISP_3_KK": "3+kk", "DISP_3_1": "3+1",
    "DISP_4_KK": "4+kk", "DISP_4_1": "4+1",
    "DISP_5_KK": "5+kk", "DISP_5_1": "5+1",
}
_ESTATE_TO_CATEGORY = {"BYT": "byt", "DUM": "dum", "POZEMEK": "pozemek"}

# Typ nabídky (PRODEJ / PRONAJEM) se do dotazu doplňuje za %OFFER% – je to naše
# konstanta z config.py, ne uživatelský vstup.
_QUERY = """
query List($estateType: [EstateType], $landType: [LandType], $disposition: [Disposition],
           $priceFrom: Int, $priceTo: Int, $surfaceFrom: Int, $limit: Int, $offset: Int) {
  listAdverts(offerType: [%OFFER%], estateType: $estateType, landType: $landType,
              disposition: $disposition,
              priceFrom: $priceFrom, priceTo: $priceTo, surfaceFrom: $surfaceFrom,
              limit: $limit, offset: $offset, order: TIMEORDER_DESC) {
    totalCount
    list {
      id uri title price currency surface surfaceLand disposition estateType isNew
      gps { lat lng } address(locale: CS) mainImage { url(filter: RECORD_MAIN) }
    }
  }
}
"""


def search(search_cfg, settings, log):
    """Vrátí seznam normalizovaných inzerátů dané kategorie (celostátně)."""
    b = search_cfg["bezrealitky"]
    pronajem = search_cfg.get("deal") == "pronajem"
    dotaz = _QUERY.replace("%OFFER%", "PRONAJEM" if pronajem else "PRODEJ")
    variables = {
        "estateType": [b["estate_type"]],
        # druh pozemku (STAVEBNI, POLE, LES…); None = neomezovat
        "landType": b.get("land_types") or None,
        "disposition": b["dispositions"] or None,
        "priceFrom": search_cfg["price_from"],
        "priceTo": search_cfg["price_to"],
        "surfaceFrom": search_cfg.get("min_area_m2"),
        "limit": LIMIT,
        "offset": 0,
    }

    out = []
    offset = 0
    total = None
    while True:
        variables["offset"] = offset
        try:
            data = http.post_json(API, {"query": dotaz, "variables": variables})
        except RuntimeError as e:
            log(f"    [bezrealitky] chyba: {e}")
            break
        if "errors" in data and "data" not in data:
            log(f"    [bezrealitky] GraphQL chyba: {data['errors'][:1]}")
            break
        block = (data.get("data") or {}).get("listAdverts") or {}
        if total is None:
            total = block.get("totalCount", 0)
        rows = block.get("list") or []
        if not rows:
            break
        for r in rows:
            item = _normalize(r, pronajem)
            if item:
                out.append(item)
        offset += LIMIT
        if offset >= total or offset >= settings["max_per_query"]:
            break
        time.sleep(0.4)
    return out


def _normalize(r, pronajem=False):
    gps = r.get("gps") or {}
    lat = gps.get("lat")
    lon = gps.get("lng")

    estate = r.get("estateType")
    title = r.get("title") or ""
    area_m2, _land = parse_areas_from_name(title)
    if not area_m2 and r.get("surface"):
        area_m2 = int(r["surface"])
    land_m2 = int(r["surfaceLand"]) if r.get("surfaceLand") else None

    if estate == "POZEMEK":
        # u pozemku je "plocha" výměra pozemku
        area_m2 = land_m2 or area_m2
        land_m2 = None

    price = int(r["price"]) if r.get("price") else None
    disp = _DISP.get(r.get("disposition"))
    uri = r.get("uri")
    url = f"https://www.bezrealitky.cz/nemovitosti-byty-domy/{uri}" if uri else None

    img = (r.get("mainImage") or {}).get("url")

    return make_listing(
        source="bezrealitky",
        native_id=r.get("id"),
        deal="pronajem" if pronajem else "prodej",
        category=_ESTATE_TO_CATEGORY.get(estate, "byt"),
        title=title,
        price=price,
        area_m2=area_m2,
        land_area_m2=land_m2,
        disposition=disp,
        city=None,
        address=r.get("address"),
        lat=lat,
        lon=lon,
        url=url,
        image=img,
        price_per_m2=None,   # dopočítá se v make_listing z ceny a plochy
    )
