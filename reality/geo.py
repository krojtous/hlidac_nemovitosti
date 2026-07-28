# -*- coding: utf-8 -*-
"""Geografické výpočty – vzdálenost mezi dvěma GPS body."""

from math import radians, sin, cos, asin, sqrt


def haversine_km(lat1, lon1, lat2, lon2):
    """Vzdálenost dvou GPS bodů na Zemi v kilometrech."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0  # poloměr Země v km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def area_radius_km(area):
    """Poloměr samotné oblasti (jak je velká). Chybí-li, bereme ji jako bod."""
    return float(area.get("area_radius_km") or 0.0)


def reach_km(area):
    """
    Celkový dosah oblasti = velikost oblasti + okruh navíc.

    Okruh (radius_km) se počítá NAD RÁMEC oblasti, ne od jejího středu:
    'Vratislavice + 1 km' tedy znamená celé Vratislavice a k tomu 1 km okolo nich.
    """
    return area_radius_km(area) + float(area.get("radius_km") or 0.0)


def nearest_area(lat, lon, areas):
    """
    Vrátí (area, distance_km) lokality, do jejíhož dosahu bod spadá.
    distance_km je vzdálenost od středu oblasti.
    Když bod nespadá do žádné, vrátí (None, None).

    Při překryvu vyhrává oblast, k jejímuž OKRAJI je bod blíž – bod uvnitř
    malé obce tak nepřebije větší lokalita, jejíž střed je náhodou blíž.
    """
    best = None
    best_dist = None
    best_edge = None
    for area in areas:
        d = haversine_km(lat, lon, area["lat"], area["lon"])
        if d is None or d > reach_km(area):
            continue
        edge = max(0.0, d - area_radius_km(area))  # 0 = přímo v oblasti
        if best_edge is None or edge < best_edge:
            best = area
            best_dist = d
            best_edge = edge
    return best, best_dist
