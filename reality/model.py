# -*- coding: utf-8 -*-
"""Společné schéma inzerátu a pomocné funkce pro normalizaci."""

import re


def make_listing(source, native_id, category, title, price, area_m2, land_area_m2,
                 disposition, city, address, lat, lon, url, image, price_per_m2,
                 image_thumb=None):
    """Vytvoří jednotný záznam inzerátu (obyčejný slovník kvůli ukládání do JSON)."""
    # Kč/m² portál často neuvádí – dopočítáme ho z ceny a plochy.
    # (U pozemku je „plocha“ výměra pozemku, takže vyjde cena za m² pozemku.)
    if not price_per_m2 and price and area_m2:
        price_per_m2 = int(round(price / area_m2))
    return {
        "id": f"{source}:{native_id}",
        "source": source,               # "sreality" / "bezrealitky"
        "category": category,           # "dum" / "byt" / "pozemek"
        "title": title,
        "price": price,                 # Kč, int nebo None
        "area_m2": area_m2,             # užitná/obytná plocha (u pozemku výměra pozemku)
        "land_area_m2": land_area_m2,   # plocha pozemku u domu, pokud je uvedena
        "disposition": disposition,     # "4+1", "4+kk", ... nebo None
        "city": city,
        "address": address,
        "lat": lat,
        "lon": lon,
        "url": url,
        "image": image,                 # větší náhled
        "image_thumb": image_thumb or image,   # malý náhled do tabulky
        "price_per_m2": price_per_m2,
    }


# V českých názvech bývá tisícový oddělovač tečka nebo mezera: "4.244 m²", "1 949 m²".
# Do čísla proto pouštíme i tečku, obyčejnou i pevnou mezeru.
_NUM = "\\d[\\d\\s. ]*"
_M2_RE = re.compile("(" + _NUM + ")\\s*m(?:²|2)", re.IGNORECASE)
_LAND_RE = re.compile("pozemek\\s+(" + _NUM + ")\\s*m", re.IGNORECASE)


def parse_areas_from_name(name):
    """
    Z názvu jako 'Prodej rodinného domu 120 m², pozemek 333 m²'
    vytáhne (obytná_plocha, plocha_pozemku). Co nenajde, vrátí None.
    """
    if not name:
        return None, None
    area = None
    land = None
    m = _M2_RE.search(name)
    if m:
        area = _to_int(m.group(1))
    lm = _LAND_RE.search(name)
    if lm:
        land = _to_int(lm.group(1))
    return area, land


def _to_int(s):
    """Převede '4.244' / '1 949' / '1\\xa0949' na 4244 / 1949."""
    if s is None:
        return None
    cleaned = re.sub("[\\s. ]", "", str(s))
    try:
        return int(cleaned)
    except (ValueError, TypeError):
        return None
