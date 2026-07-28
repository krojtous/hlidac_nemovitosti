# -*- coding: utf-8 -*-
"""Sestavení a odeslání e-mailu s novými nemovitostmi."""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _fmt_price(p, rec=None):
    """Cena; u pronájmu se přidá „/měsíc“, ať se neplete s kupní cenou."""
    if not p:
        return "cena neuvedena"
    text = f"{p:,.0f} Kč".replace(",", " ")
    if rec and rec.get("deal") == "pronajem":
        text += "/měsíc"
    return text


def _card(inner):
    """Rámeček kolem jedné položky."""
    return ("<div style='border:1px solid #e2e2e2;border-radius:8px;padding:10px 12px;"
            "margin:8px 0'>" + inner + "</div>")


def _price_change_rows(changes):
    """Sekce e-mailu se zlevněním/zdražením u oblíbených nemovitostí."""
    if not changes:
        return []
    parts = [f"<h2 style='margin-top:26px'>Změna ceny u oblíbených ({len(changes)})</h2>"]
    for ch in changes:
        it = ch["listing"]
        old, new = ch.get("old_price"), ch.get("new_price")
        levneji = old and new and new < old
        # Šipka i barva: dolů/zeleně = zlevnilo, nahoru/červeně = zdražilo.
        sipka = "▼" if levneji else "▲"
        barva = "#1a7f37" if levneji else "#b42318"
        rozdil = ""
        if old and new:
            rozdil = f" ({sipka} {_fmt_price(abs(new - old))})"
        parts.append(_card(
            f"<div style='font-weight:bold'>"
            f"<a href='{it.get('url')}' style='color:#0b5cad;text-decoration:none'>"
            f"{it.get('title') or 'Inzerát'}</a></div>"
            f"<div style='color:{barva};margin-top:3px;font-weight:bold'>"
            f"{_fmt_price(old, it)} → {_fmt_price(new, it)}{rozdil}</div>"
            f"<div style='color:#888;font-size:13px;margin-top:2px'>"
            f"{it.get('address') or ''} · {it.get('source', '')}</div>"
        ))
    return parts


def _gone_rows(gone):
    """Sekce e-mailu s oblíbenými, které zmizely z nabídky (nejspíš prodané)."""
    if not gone:
        return []
    parts = [f"<h2 style='margin-top:26px'>Oblíbené zmizely z nabídky ({len(gone)})</h2>"]
    for it in gone:
        parts.append(_card(
            f"<div style='font-weight:bold'>"
            f"<a href='{it.get('url')}' style='color:#0b5cad;text-decoration:none'>"
            f"{it.get('title') or 'Inzerát'}</a></div>"
            f"<div style='color:#333;margin-top:3px'>"
            f"poslední cena {_fmt_price(it.get('price'), it)}</div>"
            f"<div style='color:#888;font-size:13px;margin-top:2px'>"
            f"{it.get('address') or ''} · {it.get('source', '')} · "
            f"v nabídce od {it.get('first_seen') or '?'}</div>"
        ))
    parts.append("<p style='color:#888;font-size:12px'>"
                 "Inzerát z portálu zmizel – bývá to prodej, ale někdy jen "
                 "přepis nabídky. Odkaz proto nechávám funkční.</p>")
    return parts


def build_email_html(new_list, price_changes, gone, settings):
    """Vytvoří HTML tělo e-mailu: novinky podle lokality + změny cen u oblíbených."""
    by_area = {}
    for it in new_list:
        by_area.setdefault(it.get("matched_area") or "—", []).append(it)

    parts = ["<div style='font-family:Arial,Helvetica,sans-serif;color:#1a1a1a'>"]
    if new_list:
        parts.append(f"<h2>Nové nemovitosti ({len(new_list)})</h2>")
    for area, items in sorted(by_area.items()):
        parts.append(f"<h3 style='margin:18px 0 6px'>{area} "
                     f"<span style='color:#888;font-weight:normal'>({len(items)})</span></h3>")
        for it in items:
            dist = it.get("distance_km")
            dist_txt = f" · {dist:.1f} km od středu" if isinstance(dist, (int, float)) else ""
            area_txt = f" · {it['area_m2']} m²" if it.get("area_m2") else ""
            disp_txt = f" · {it['disposition']}" if it.get("disposition") else ""
            if it.get("deal") == "pronajem":
                disp_txt += " · pronájem"
            src = it.get("source", "")
            parts.append(_card(
                f"<div style='font-weight:bold'>"
                f"<a href='{it.get('url')}' style='color:#0b5cad;text-decoration:none'>"
                f"{it.get('title') or 'Inzerát'}</a></div>"
                f"<div style='color:#333;margin-top:3px'>"
                f"{_fmt_price(it.get('price'), it)}{area_txt}{disp_txt}</div>"
                f"<div style='color:#888;font-size:13px;margin-top:2px'>"
                f"{it.get('address') or ''}{dist_txt} · {src}</div>"
            ))
    parts += _price_change_rows(price_changes)
    parts += _gone_rows(gone)
    parts.append("<p style='color:#999;font-size:12px;margin-top:20px'>"
                 "Automatické upozornění hlídače nemovitostí.</p></div>")
    return "\n".join(parts)


def _sklonuj(n, jedna, dve_ctyri, pet_vic):
    """Český tvar podle počtu: 1 nová, 2 nové, 5 nových."""
    if n == 1:
        return jedna
    if 2 <= n <= 4:
        return dve_ctyri
    return pet_vic


def _subject(new_list, price_changes, gone, settings):
    """Předmět podle toho, co se v e-mailu vlastně veze."""
    if new_list and not price_changes and not gone:
        return f"{settings['email_subject_prefix']} ({len(new_list)})"
    casti = []
    if new_list:
        n = len(new_list)
        casti.append(f"{n} {_sklonuj(n, 'nová', 'nové', 'nových')}")
    if price_changes:
        n = len(price_changes)
        casti.append(f"{_sklonuj(n, 'změna', 'změny', 'změn')} ceny u {n}")
    if gone:
        n = len(gone)
        casti.append(f"{n} {_sklonuj(n, 'zmizela', 'zmizely', 'zmizelo')} z nabídky")
    return "🏠 Hlídač nemovitostí – " + ", ".join(casti)


def send_email(new_list, price_changes, gone, settings, log):
    """
    Pošle e-mail, když přibyly nové nemovitosti nebo se u oblíbených změnila
    cena či zmizely z nabídky. Údaje se berou z SMTP_USER a SMTP_PASS.
    """
    if not new_list and not price_changes and not gone:
        log("  E-mail se neposílá (žádné novinky ani změny u oblíbených).")
        return False

    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("MAIL_TO") or settings.get("email_to")

    if not (user and password and to_addr):
        log("  E-mail se neposílá (chybí SMTP_USER / SMTP_PASS / příjemce). "
            "Novinky jsou i tak v tabulce.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = _subject(new_list, price_changes, gone, settings)
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(build_email_html(new_list, price_changes, gone, settings),
                        "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings["smtp_host"], settings["smtp_port"], context=ctx) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
    log(f"  E-mail odeslán na {to_addr}.")
    return True
