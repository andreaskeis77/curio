"""Source-Policy-Heuristik (ADR-0006).

Domain-basierte Defaults für ``access``, ``copyright_risk``,
``reliability``. Kein verbindliches Urteil — der User kann via
CLI-Flag jeden Wert überschreiben.
"""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import urlparse

from curiosity_wiki.sources.models import (
    AccessType,
    CopyrightRisk,
    Reliability,
    SourcePolicy,
)

# Domains, die wir als verlässlich/öffentlich kennen
OFFICIAL_DOMAINS = {
    "whc.unesco.org",
    "unesco.org",
    "europa.eu",
    "destatis.de",
    "bfs.admin.ch",
    "data.gov",
    "api.github.com",
}

EXPERT_DOMAINS = {
    "arxiv.org",
    "scholar.google.com",
    "doi.org",
    "ncbi.nlm.nih.gov",
}

JOURNALISTIC_DOMAINS = {
    "wikipedia.org",
    "en.wikipedia.org",
    "de.wikipedia.org",
}

# Bekannte Paywall-Domains — nur Link, kein Volltext
PAYWALL_DOMAINS = {
    "nytimes.com",
    "wsj.com",
    "ft.com",
    "economist.com",
    "spiegel.de",
    "zeit.de",
    "sueddeutsche.de",
}


def _normalize_host(host: str) -> str:
    host = host.lower()
    return host.removeprefix("www.")


def guess_source_policy(url: str | None) -> SourcePolicy:
    """Liefert eine Default-Policy. Bei ``None`` (Notiz, lokale Datei): own_note."""
    if not url:
        return SourcePolicy(
            access=AccessType.OWN_NOTE,
            copyright_risk=CopyrightRisk.LOW,
            reliability=Reliability.PERSONAL,
            llm_allowed=True,
            notes=["no URL — assumed personal note"],
        )

    parsed = urlparse(url)
    host = _normalize_host(parsed.netloc)

    base = SourcePolicy()
    if not host:
        return base

    # Paywall hat Vorrang vor Domain-Reliability
    for domain in PAYWALL_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return SourcePolicy(
                access=AccessType.PAYWALLED,
                copyright_risk=CopyrightRisk.HIGH,
                reliability=Reliability.JOURNALISTIC,
                llm_allowed=False,
                license_note="Nur Link + eigene Notizen; kein Volltext-Speichern.",
                notes=[f"paywall heuristic matched: {host}"],
            )

    for domain in OFFICIAL_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return replace(
                base,
                reliability=Reliability.OFFICIAL,
                copyright_risk=CopyrightRisk.LOW,
                notes=[f"official domain matched: {host}"],
            )

    for domain in EXPERT_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return replace(
                base,
                reliability=Reliability.EXPERT,
                copyright_risk=CopyrightRisk.MEDIUM,
                notes=[f"expert domain matched: {host}"],
            )

    for domain in JOURNALISTIC_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return replace(
                base,
                reliability=Reliability.JOURNALISTIC,
                copyright_risk=CopyrightRisk.MEDIUM,
                notes=[f"journalistic domain matched: {host}"],
            )

    return SourcePolicy(
        access=AccessType.PUBLIC,
        copyright_risk=CopyrightRisk.MEDIUM,
        reliability=Reliability.UNKNOWN,
        llm_allowed=True,
        notes=[f"no domain rule for {host}; defaulting to public/medium/unknown"],
    )
