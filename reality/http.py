# -*- coding: utf-8 -*-
"""Malý pomocník pro HTTP dotazy (jen standardní knihovna Pythonu)."""

import json
import os
import ssl
import time
import urllib.error
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Nouzová brzda pro lokální testování: REALITY_INSECURE_SSL=1 vypne ověřování
# certifikátů úplně. Díky balíčku certifi (níže) by to už nemělo být potřeba.
_INSECURE = os.environ.get("REALITY_INSECURE_SSL") == "1"


def _build_ctx():
    """
    Připraví SSL kontext s aktuálním seznamem certifikačních autorit.

    Windows si drží jen ty autority, na které kdy narazil, takže Python tam
    často hlásí „certificate has expired“ i u serveru s platným certifikátem
    (to byl případ api.bezrealitky.cz). Balíček `certifi` nese aktuální seznam
    od Mozilly a aktualizuje se přes pip. Když nainstalovaný není, použije se
    systémové úložiště – na Linuxu (a tedy i v GitHub Actions) funguje dobře.
    """
    if _INSECURE:
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        return c
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


_CTX = _build_ctx()


def _ctx():
    return _CTX


def get_json(url, headers=None, retries=3, timeout=40):
    """GET požadavek vracející rozparsovaný JSON."""
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    return _request(url, data=None, headers=h, retries=retries, timeout=timeout)


def post_json(url, payload, headers=None, retries=3, timeout=40):
    """POST požadavek s JSON tělem, vrací rozparsovaný JSON."""
    h = {"User-Agent": USER_AGENT, "Accept": "application/json",
         "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    data = json.dumps(payload).encode("utf-8")
    return _request(url, data=data, headers=h, retries=retries, timeout=timeout)


def _request(url, data, headers, retries, timeout):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read()[:300]
            last_err = f"HTTP {e.code}: {body!r}"
            # 4xx se opakováním nespraví
            if 400 <= e.code < 500:
                break
        except Exception as e:  # timeout, síť, SSL...
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Požadavek selhal ({url[:80]}...): {last_err}")
