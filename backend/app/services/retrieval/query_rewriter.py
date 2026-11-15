import re
from typing import Optional

_ENTERPRISE_ABBREVIATIONS = {
    # Organizational, HR, Policies & Work
    "sop": "Standard Operating Procedure SOP",
    "sops": "Standard Operating Procedures SOP",
    "hr": "Human Resources HR",
    "pto": "Paid Time Off PTO leave vacation",
    "sla": "Service Level Agreement SLA",
    "nda": "Non-Disclosure Agreement NDA",
    "wfh": "Work From Home remote working policy",
    "okr": "Objectives and Key Results OKR",
    "kpi": "Key Performance Indicator KPI",
    "erp": "Enterprise Resource Planning ERP",
    "crm": "Customer Relationship Management CRM",
    # IT & Infrastructure
    "o365": "Office 365 Microsoft 365",
    "m365": "Microsoft 365",
    "ad": "Active Directory",
    "mfa": "Multi-Factor Authentication MFA",
    "2fa": "Two-Factor Authentication 2FA MFA",
    "sso": "Single Sign-On SSO",
    "rdp": "Remote Desktop Protocol RDP",
    "dns": "Domain Name System DNS",
    "dhcp": "Dynamic Host Configuration Protocol DHCP",
    "bsod": "Blue Screen of Death BSOD stop code",
    "ost": "Outlook OST offline data file",
    "pst": "Outlook PST data file",
    "pw": "password",
    "pwd": "password",
    "vpn": "Virtual Private Network VPN",
}


def rewrite_query(
    query: str,
    recent_user_turns: Optional[list[str]] = None,
    enabled: bool = True,
) -> str:
    """
    Safely rewrite conversational or acronym-heavy enterprise queries to improve retrieval recall
    while strictly preserving the user's original intent and exact codes.
    """
    cleaned = " ".join(query.strip().split())
    if not enabled or not cleaned:
        return cleaned

    expanded_terms: list[str] = []
    tokens = re.findall(r"[A-Za-z0-9_.-]+", cleaned)
    seen_lower = {t.lower() for t in tokens}

    for token in tokens:
        lower = token.lower()
        if lower in _ENTERPRISE_ABBREVIATIONS:
            expansion = _ENTERPRISE_ABBREVIATIONS[lower]
            for word in expansion.split():
                if word.lower() not in seen_lower:
                    expanded_terms.append(word)
                    seen_lower.add(word.lower())

    # If the user asks a short follow-up like "how do I reset it?" append topic keywords from prior turn
    context_prefix = ""
    if recent_user_turns and len(cleaned.split()) <= 8:
        follow_up_pronouns = {"it", "this", "that", "they", "them", "same"}
        if any(tok.lower() in follow_up_pronouns for tok in tokens):
            prev = " ".join(recent_user_turns[-1].strip().split())
            if prev and prev.lower() != cleaned.lower():
                context_prefix = f"{prev[:160]} — "

    rewritten = f"{context_prefix}{cleaned}"
    if expanded_terms:
        rewritten = f"{rewritten} ({' '.join(expanded_terms)})"
    return rewritten

