"""Module de sécurité bancaire et anonymisation PCI-DSS.

Règles PCI-DSS :
1. Masquage des numéros de carte (PAN) : seuls les 6 premiers et 4 derniers chiffres peuvent être visibles.
   Format standardisé : 4111 11** **** 1234
2. Suppression totale des blocs PIN (DE52) et CVV/CVC.
3. Nettoyage des données confidentielles avant transmission vers des LLM Cloud.
"""

import re
from typing import Any


class PciDssSanitizer:
    """Sanitizer pour la conformité et confidentialité des trames et données monétiques."""

    # Regex pour détecter les numéros de carte (PAN) de 13 à 19 chiffres (avec ou sans espaces / tirets)
    PAN_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    # Regex spécifique pour le Data Element ISO 8583 DE2
    DE2_REGEX = re.compile(r"(DE2\s*[:=]\s*)([0-9]{13,19})", re.IGNORECASE)

    # Regex pour le PIN Block (DE52)
    DE52_REGEX = re.compile(
        r"(DE52\s*[:=]\s*)([0-9A-Fa-f]{16}|[^\s,;\n]+)", re.IGNORECASE
    )

    # Regex pour CVV / CVC (3 ou 4 chiffres isolés précédés d'un mot-clé)
    CVV_REGEX = re.compile(r"\b(CVV2?|CVC2?|CID)\s*[:=]\s*([0-9]{3,4})\b", re.IGNORECASE)

    @classmethod
    def mask_pan(cls, text: str) -> str:
        """Masque tous les numéros de carte (PAN) trouvés dans un texte selon la norme PCI-DSS."""
        if not text:
            return text

        # 1. Traitement prioritaire du champ DE2 ISO 8583
        def _replace_de2(match: re.Match[str]) -> str:
            prefix = match.group(1)
            raw_pan = match.group(2)
            return f"{prefix}{cls._format_masked_pan(raw_pan)}"

        result = cls.DE2_REGEX.sub(_replace_de2, text)

        # 2. Traitement général des séquences de chiffres correspondant à un PAN
        def _replace_pan(match: re.Match[str]) -> str:
            raw_str = match.group(0)
            digits_only = re.sub(r"\D", "", raw_str)
            if 13 <= len(digits_only) <= 19:
                # Vérification de pertinence (évite de masquer des STANs ou horodatages courts)
                return cls._format_masked_pan(digits_only)
            return raw_str

        return cls.PAN_REGEX.sub(_replace_pan, result)

    @staticmethod
    def _format_masked_pan(pan: str) -> str:
        """Formate un PAN au standard PCI-DSS : 6 premiers + étoiles + 4 derniers."""
        pan_clean = re.sub(r"\D", "", pan)
        if len(pan_clean) < 10:
            return "************"
        prefix = pan_clean[:6]
        suffix = pan_clean[-4:]
        middle_stars = "*" * (len(pan_clean) - 10)
        # Format par blocs lisibles pour le monéticien : 4111 11** **** 1234
        masked = f"{prefix}{middle_stars}{suffix}"
        if len(masked) == 16:
            return f"{masked[:4]} {masked[4:8]} {masked[8:12]} {masked[12:]}"
        return masked

    @classmethod
    def scrub_sensitive_iso_fields(cls, text: str) -> str:
        """Supprime ou caviarde les données ultra-sensibles : PIN blocks DE52 et CVV."""
        if not text:
            return text

        # Remplacement du DE52 (PIN block)
        scrubbed = cls.DE52_REGEX.sub(r"\1[PIN_BLOCK_REDACTED_PCI_DSS]", text)

        # Remplacement du CVV / CVC
        scrubbed = cls.CVV_REGEX.sub(r"\1=[REDACTED]", scrubbed)

        return scrubbed

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Applique l'ensemble des règles de sanitization sur une chaîne de texte."""
        if not text:
            return text
        no_pin = cls.scrub_sensitive_iso_fields(text)
        return cls.mask_pan(no_pin)

    @classmethod
    def sanitize_payload(cls, data: Any) -> Any:
        """Sanitise récursivement dictionnaires, listes et chaînes d'un payload."""
        if isinstance(data, str):
            return cls.sanitize_text(data)
        if isinstance(data, dict):
            return {k: cls.sanitize_payload(v) for k, v in data.items()}
        if isinstance(data, list):
            return [cls.sanitize_payload(v) for v in data]
        return data
