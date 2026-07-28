# -*- coding: utf-8 -*-
"""Sestavení a odeslání e-mailu s novými nemovitostmi."""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _fmt_price(p):
    if not p:
        return "cena neuvedena"
    return f"{p:,.0f} Kč".replace(",", " ")


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
            f"{_fmt_price(old)} → {_fmt_price(new)}{rozdil}</div>"
            f"<div style='color:#888;font-size:13px;margin-top:2px'>"
            f"{it.get('address') or ''} · {it.get('source', '')}</div>"
        ))
    return parts


def build_email_html(new_list, price_changes, settings):
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
            src = it.get("source", "")
            parts.append(_card(
                f"<div style='font-weight:bold'>"
                f"<a href='{it.get('url')}' style='color:#0b5cad;text-decoration:none'>"
                f"{it.get('title') or 'Inzerát'}</a></div>"
                f"<div style='color:#333;margin-top:3px'>"
                f"{_fmt_price(it.get('price'))}{area_txt}{disp_txt}</div>"
                f"<div style='color:#888;font-size:13px;margin-top:2px'>"
                f"{it.get('address') or ''}{dist_txt} · {src}</div>"
            ))
    parts += _price_change_rows(price_changes)
    parts.append("<p style='color:#999;font-size:12px;margin-top:20px'>"
                 "Automatické upozornění hlídače nemovitostí.</p></div>")
    return "\n".join(parts)


def _subject(new_list, price_changes, settings):
    """Předmět podle toho, co se v e-mailu vlastně veze."""
    prefix = settings["email_subject_prefix"]
    if new_list and price_changes:
        return f"{prefix} ({len(new_list)}) + změna ceny ({len(price_changes)})"
    if new_list:
        return f"{prefix} ({len(new_list)})"
    return f"🏠 Změna ceny u oblíbených ({len(price_changes)})"


def send_email(new_list, price_changes, settings, log):
    """
    Pošle e-mail, když přibyly nové nemovitosti nebo se změnila cena
    u oblíbených. Přihlašovací údaje se berou z SMTP_USER a SMTP_PASS.
    """
    if not new_list and not price_changes:
        log("  E-mail se neposílá (žádné novinky ani změny cen u oblíbených).")
        return False

    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    to_addr = os.environ.get("MAIL_TO") or settings.get("email_to")

    if not (user and password and to_addr):
        log("  E-mail se neposílá (chybí SMTP_USER / SMTP_PASS / příjemce). "
            "Novinky jsou i tak v tabulce.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = _subject(new_list, price_changes, settings)
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(build_email_html(new_list, price_changes, settings),
                        "html", "utf-8"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings["smtp_host"], settings["smtp_port"], context=ctx) as server:
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
    log(f"  E-mail odeslán na {to_addr}.")
    return True
