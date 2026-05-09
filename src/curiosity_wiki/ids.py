"""ID-Generator für Curiosity-Objekte.

Format-Konventionen (siehe ARD §6):

- ``src_<YYYYMMDD>_<HHMMSS>_<RAND4>`` — Sources
- ``page_<ULID>``                      — Pages
- ``clm_<ULID>``                       — Claims
- ``prop_<YYYYMMDD>_<HHMMSS>_<topic>`` — Proposals
- ``run_<YYYYMMDD>_<HHMMSS>_<RAND4>``  — Runs
- ``job_<ULID>``                       — Jobs

ULIDs sind monoton sortierbar nach Zeit. Wir verwenden eine vereinfachte
ULID-Implementierung ohne externe Dependency, die Crockford-Base32 nutzt
und mit Standard-Bibliothek auskommt.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

# Crockford Base32 alphabet (no I, L, O, U)
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford(value: int, length: int) -> str:
    """Encode integer als Crockford-Base32, links mit '0' aufgefüllt."""
    out: list[str] = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def generate_ulid() -> str:
    """26-Zeichen-ULID (10 Zeichen Zeit + 16 Zeichen Random).

    Genug Entropie für einzelne Person/Maschine; keine externe Dependency.
    """
    timestamp_ms = int(time.time() * 1000)
    random_bytes = os.urandom(10)
    random_int = int.from_bytes(random_bytes, byteorder="big")

    time_part = _encode_crockford(timestamp_ms, 10)
    rand_part = _encode_crockford(random_int, 16)
    return time_part + rand_part


def _short_random(length: int = 4) -> str:
    """Kurzer Crockford-Suffix (4 Zeichen = 20 bit)."""
    n = int.from_bytes(os.urandom(3), byteorder="big") & ((1 << (5 * length)) - 1)
    return _encode_crockford(n, length)


def _now_iso_compact() -> str:
    """Kompakte Zeitangabe: YYYYMMDD_HHMMSS in UTC."""
    return datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")


def generate_source_id() -> str:
    """``src_<YYYYMMDD>_<HHMMSS>_<RAND4>``."""
    return f"src_{_now_iso_compact()}_{_short_random(4)}"


def generate_page_id() -> str:
    """``page_<ULID>``."""
    return f"page_{generate_ulid()}"


def generate_claim_id() -> str:
    """``clm_<ULID>``."""
    return f"clm_{generate_ulid()}"


def generate_proposal_id(topic: str = "") -> str:
    """``prop_<YYYYMMDD>_<HHMMSS>_<RAND4>[_<topic>]``.

    Random-Suffix ist immer dabei — zwei Aufrufe in derselben Sekunde kollidieren nicht.
    Topic-Slug wird optional angehängt.
    """
    rand = _short_random(4)
    safe = "".join(ch if ch.isalnum() else "_" for ch in topic)[:32]
    if safe:
        return f"prop_{_now_iso_compact()}_{rand}_{safe}"
    return f"prop_{_now_iso_compact()}_{rand}"


def generate_run_id() -> str:
    """``run_<YYYYMMDD>_<HHMMSS>_<RAND4>``."""
    return f"run_{_now_iso_compact()}_{_short_random(4)}"


def generate_job_id() -> str:
    """``job_<ULID>``."""
    return f"job_{generate_ulid()}"
