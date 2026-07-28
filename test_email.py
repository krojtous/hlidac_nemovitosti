# -*- coding: utf-8 -*-
"""
Zkušební e-mail – ověří, že odesílání funguje.

Na rozdíl od run.py pošle e-mail vždy, i když žádná nová nemovitost nepřibyla.
Použije se skutečný inzerát z evidence, takže je vidět i to, jak zpráva vypadá.

Spuštění na GitHubu:  Actions → „Test e-mailu“ → Run workflow
Spuštění doma (PowerShell):
    $env:SMTP_USER="tvuj@gmail.com"; $env:SMTP_PASS="heslo aplikace"
    $env:MAIL_TO="tvuj@gmail.com"; python test_email.py
"""

import os
import smtplib
import sys

import config
from reality import notify, store


def log(msg):
    print(msg, flush=True)


def vzorek():
    """Vrátí jeden inzerát z evidence; když je prázdná, vymyšlený náhradník."""
    for rec in store.load_listings().values():
        if not rec.get("removed_on"):
            return rec
    return {
        "title": "Zkušební inzerát (v evidenci zatím nic není)",
        "url": "https://www.sreality.cz/",
        "price": 4_200_000,
        "area_m2": 90,
        "disposition": "4+kk",
        "address": "Ukázková 1, Liberec",
        "matched_area": "Ruprechtice (Liberec)",
        "distance_km": 1.2,
        "source": "sreality",
    }


def main():
    chybi = [k for k in ("SMTP_USER", "SMTP_PASS") if not os.environ.get(k)]
    if not (os.environ.get("MAIL_TO") or config.SETTINGS.get("email_to")):
        chybi.append("MAIL_TO")
    if chybi:
        log("CHYBA: chybí " + ", ".join(chybi) + ".")
        log("Na GitHubu je doplň v Settings → Secrets and variables → Actions.")
        return 1

    log(f"Odesílatel: {os.environ['SMTP_USER']}")
    log(f"Příjemce:   {os.environ.get('MAIL_TO') or config.SETTINGS['email_to']}")
    log(f"Server:     {config.SETTINGS['smtp_host']}:{config.SETTINGS['smtp_port']}")

    nastaveni = dict(config.SETTINGS)
    nastaveni["email_subject_prefix"] = "🏠 ZKUŠEBNÍ e-mail hlídače"

    # Ukázková změna ceny, ať je v testu vidět i sekce pro oblíbené nemovitosti.
    vzor = vzorek()
    zmena = [{"listing": vzor, "old_price": (vzor.get("price") or 4_000_000),
              "new_price": int((vzor.get("price") or 4_000_000) * 0.95)}]

    try:
        notify.send_email([vzor], zmena, nastaveni, log)
    except smtplib.SMTPAuthenticationError as e:
        log(f"CHYBA přihlášení k SMTP: {e}")
        log("Skoro jistě je v SMTP_PASS běžné heslo k účtu místo hesla aplikace,")
        log("nebo v SMTP_USER chybí celá adresa včetně @gmail.com.")
        return 1
    except Exception as e:  # noqa: BLE001 – ať je v logu vidět, co přesně selhalo
        log(f"CHYBA při odesílání: {type(e).__name__}: {e}")
        return 1

    log("Hotovo – zkontroluj schránku (mrkni i do spamu).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
