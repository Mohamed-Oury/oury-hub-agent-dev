"""Référentiel canonique des dictionnaires de données Core Banking (Amplitude & FLEXCUBE).

Règles de gouvernance bancaire :
1. Aucune table inventée n'est tolérée dans une spécification technique.
2. Toute règle métier déduite sans référence documentaire explicite doit porter le tag :
   [NON DOCUMENTÉ - À VALIDER MÉTIER]
"""

from typing import Any

# Référentiel des tables canoniques Amplitude CBS (Informix / SQL)
AMPLITUDE_TABLES: dict[str, dict[str, Any]] = {
    "BKCPT": {
        "description": "Comptes de la clientèle et soldes comptables",
        "primary_key": ["age", "dev", "ncp", "clc"],
        "columns": ["age", "dev", "ncp", "clc", "cli", "cha", "sin", "sdi"],
        "module": "Comptes",
    },
    "BKTRA": {
        "description": "Mouvements et écritures comptables transactionnelles",
        "primary_key": ["age", "eve", "ope"],
        "columns": ["age", "eve", "ope", "dva", "mon", "dev", "sen", "lib"],
        "module": "Comptabilité",
    },
    "BKCOM": {
        "description": "Commissions, frais et barèmes tarifaires bancaires",
        "primary_key": ["com"],
        "columns": ["com", "lib", "tau", "min", "max", "dev"],
        "module": "Tarification",
    },
    "BKDEVI": {
        "description": "Table des devises et cotations de change",
        "primary_key": ["dev"],
        "columns": ["dev", "lib", "dec", "uni"],
        "module": "Paramétrage Général",
    },
    "CLI": {
        "description": "Référentiel des clients et personnes physiques / morales",
        "primary_key": ["cli"],
        "columns": ["cli", "nom", "pre", "cat", "seg", "sta"],
        "module": "Clientèle",
    },
}

# Référentiel des tables canoniques Oracle FLEXCUBE
FLEXCUBE_TABLES: dict[str, dict[str, Any]] = {
    "STTM_CUSTOMER": {
        "description": "Customer Master Table (Données générales client)",
        "primary_key": ["CUSTOMER_NO"],
        "columns": ["CUSTOMER_NO", "CUSTOMER_NAME1", "CUSTOMER_TYPE", "FROZEN", "DECEASED"],
        "module": "Core Customer",
    },
    "CSTM_FUNCTION_USER": {
        "description": "Habilitations et droits utilisateurs sur les fonctions",
        "primary_key": ["USER_ID", "FUNCTION_ID"],
        "columns": ["USER_ID", "FUNCTION_ID", "AUTH_STAT"],
        "module": "Security Management System (SMS)",
    },
    "ACVW_ALL_ACCOUNTS": {
        "description": "Vue unifiée des comptes et balances en temps réel",
        "primary_key": ["BRANCH_CODE", "CUST_AC_NO"],
        "columns": ["BRANCH_CODE", "CUST_AC_NO", "CCY", "ACY_CURR_BALANCE", "ACY_AVL_BAL"],
        "module": "Casa Accounts",
    },
    "CSTB_CONTRACT": {
        "description": "Master des contrats et opérations financières",
        "primary_key": ["CONTRACT_REF_NO"],
        "columns": ["CONTRACT_REF_NO", "PRODUCT_CODE", "MODULE", "BOOKING_DATE"],
        "module": "Contract Processing",
    },
}


class CbsDictionaryService:
    """Service de consultation et validation des dépendances Core Banking."""

    @classmethod
    def get_known_tables(cls, cbs_type: str = "AMPLITUDE") -> dict[str, dict[str, Any]]:
        """Renvoie le catalogue officiel de tables pour le CBS spécifié."""
        if cbs_type.upper() == "FLEXCUBE":
            return FLEXCUBE_TABLES
        return AMPLITUDE_TABLES

    @classmethod
    def validate_cbs_dependencies(
        cls, declared_dependencies: list[str], cbs_type: str = "AMPLITUDE"
    ) -> list[str]:
        """Détecte toute table non reconnue par le référentiel officiel."""
        known = {k.upper() for k in cls.get_known_tables(cbs_type).keys()}
        unknown: list[str] = []

        for dep in declared_dependencies:
            # Extraction du code de table (ex: "Table BKCPT (comptes)" -> "BKCPT")
            words = dep.upper().replace("TABLE", "").replace("(", " ").replace(")", " ").split()
            table_candidates = [w for w in words if w in known]
            if not table_candidates:
                # Si aucun mot ne correspond à une table connue mais que la dépendance mentionne une table
                if "TABLE" in dep.upper():
                    unknown.append(dep)
        return unknown

    @classmethod
    def tag_undocumented_assumptions(
        cls, assumptions: list[str], documented_references: list[str]
    ) -> list[str]:
        """Appose le marqueur [NON DOCUMENTÉ - À VALIDER MÉTIER] sur toute hypothèse non référencée."""
        doc_upper = " ".join(documented_references).upper()
        tagged: list[str] = []

        for assumption in assumptions:
            words = assumption.upper().split()
            # Si aucun mot clé significatif de l'hypothèse n'est présent dans la doc fournie
            matching = [w for w in words if len(w) > 4 and w in doc_upper]
            if not matching and "[NON DOCUMENTÉ" not in assumption:
                tagged.append(f"{assumption} [NON DOCUMENTÉ - À VALIDER MÉTIER]")
            else:
                tagged.append(assumption)
        return tagged
