# -*- coding: utf-8 -*-
"""
Konfigurace hlídače nemovitostí.

Tento soubor můžeš klidně upravovat – jsou to jen běžné hodnoty.
Za '#' je komentář (počítač ho ignoruje).

Po úpravě GPS souřadnic si je můžeš ověřit tak, že je zadáš na https://www.google.com/maps
ve formátu:  50.7490, 15.0959
"""

# ---------------------------------------------------------------------------
# LOKALITY, které se hlídají.
#
# lat/lon        = GPS střed oblasti
# area_radius_km = jak je velká samotná oblast (poloměr od středu k jejímu okraji)
# radius_km      = OKRUH NAVÍC, tedy kolik kilometrů kolem oblasti ještě chceme
#
# Hledá se v součtu obou čísel: „Vratislavice + 1 km“ znamená celé Vratislavice
# a k tomu ještě kilometr okolo nich (2,0 + 1,0 = 3 km od středu).
# GPS jsou přibližné – klidně si je uprav podle přesného místa, které tě zajímá.
# ---------------------------------------------------------------------------
AREAS = [
    # Vratislavice se táhnou údolím, od středu ke krajům jsou to zhruba 2 km.
    {"name": "Vratislavice nad Nisou", "lat": 50.7490, "lon": 15.0959,
     "area_radius_km": 2.0, "radius_km": 1.0},
    {"name": "Vlašim", "lat": 49.7043, "lon": 14.9010,
     "area_radius_km": 2.5, "radius_km": 15.0},
    {"name": "Ruprechtice (Liberec)", "lat": 50.7880, "lon": 15.0680,
     "area_radius_km": 1.5, "radius_km": 1.2},
    # Masarykova třída je ulice, ne čtvrť – „oblast“ je tedy jen její délka.
    {"name": "Masarykova třída (Liberec)", "lat": 50.7720, "lon": 15.0700,
     "area_radius_km": 0.5, "radius_km": 0.5},
]

# ---------------------------------------------------------------------------
# CO se hledá (tři kategorie). Ceny jsou v korunách.
# ---------------------------------------------------------------------------
SEARCHES = [
    {
        "key": "dum",
        "label": "Dům se zahradou",
        "price_from": 100_000,
        "price_to": 12_000_000,
        "min_area_m2": None,          # u domu neomezujeme obytnou plochu
        # Sreality: 2 = Domy, sub 37 = Rodinný dům
        "sreality": {"category_main_cb": 2, "category_sub_cb": [37]},
        # Bezrealitky: DUM, bez omezení dispozice
        "bezrealitky": {"estate_type": "DUM", "dispositions": []},
    },
    {
        "key": "byt",
        "label": "Byt 4+1 / 4+kk (min. 80 m²)",
        "price_from": 100_000,
        "price_to": 12_000_000,
        "min_area_m2": 80,
        # Sreality: 1 = Byty, sub 8 = 4+kk, 9 = 4+1
        "sreality": {"category_main_cb": 1, "category_sub_cb": [8, 9]},
        "bezrealitky": {"estate_type": "BYT", "dispositions": ["DISP_4_KK", "DISP_4_1"]},
    },
    {
        "key": "pozemek",
        "label": "Pozemek",
        "price_from": 50_000,
        "price_to": 5_000_000,        # u pozemku strop 5 mil.
        "min_area_m2": None,
        # Sreality: 3 = Pozemky, všechny podtypy
        "sreality": {"category_main_cb": 3, "category_sub_cb": []},
        "bezrealitky": {"estate_type": "POZEMEK", "dispositions": []},
    },
]

# ---------------------------------------------------------------------------
# OBECNÁ NASTAVENÍ
# ---------------------------------------------------------------------------
SETTINGS = {
    # Které portály použít
    "use_sreality": True,
    "use_bezrealitky": True,

    # Pojistka proti tichému výpadku portálu: když se stáhne méně než tenhle
    # podíl toho, co je v evidenci (0.5 = polovina), nic se neuloží a běh skončí
    # chybou. Chrání před tím, aby se při nedostupném API označila celá nabídka
    # za zmizelou. Jednorázově se to dá obejít proměnnou REALITY_FORCE=1.
    "min_fresh_ratio": 0.5,

    # Pojistka proti nekonečnému stahování (max inzerátů na jeden dotaz).
    # Bezrealitky mají celostátně ~1500 domů i pozemků, proto raději vyšší strop,
    # ať se při prvním načtení nic nevynechá.
    "max_per_query": 2500,

    # E-mail: kam posílat upozornění.
    # Odesílá se JEN když přibyly nové nemovitosti.
    # Adresa ani přihlašovací údaje se NEberou odsud, ale z proměnných prostředí /
    # GitHub Secrets (MAIL_TO, SMTP_USER, SMTP_PASS) – viz README. Repozitář je
    # veřejný, adresu tu proto nechávám prázdnou, ať ji nesbírají spamboti.
    "email_to": "",
    "email_subject_prefix": "🏠 Nové nemovitosti",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 465,
}
