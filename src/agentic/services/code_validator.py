"""Validateur syntaxique et linter local pour Informix-4GL, Genero .per et Oracle FLEXCUBE PL/SQL."""

import re
from typing import Any


class CodeValidator:
    """Valide la conformité syntaxique et les règles de gestion bancaire du code généré."""

    @classmethod
    def validate_genero_per(cls, per_code: str | None) -> dict[str, Any]:
        """Vérifie la structure et la conformité d'un masque d'écran Genero .per."""
        if not per_code or not per_code.strip():
            return {
                "valid": False,
                "language": "Genero .per",
                "errors": ["Le fichier d'écran .per est vide ou absent."],
                "warnings": [],
            }

        errors: list[str] = []
        warnings: list[str] = []
        code_upper = per_code.upper()

        # 1. Vérification des sections obligatoires
        has_layout_or_screen = "LAYOUT" in code_upper or "SCREEN" in code_upper
        has_attributes = "ATTRIBUTES" in code_upper
        has_instructions = "INSTRUCTIONS" in code_upper
        has_grid_or_tables = "GRID" in code_upper or "TABLES" in code_upper

        if not has_layout_or_screen:
            errors.append("Section obligatoire manquante : LAYOUT ou SCREEN")
        if not has_attributes:
            errors.append("Section obligatoire manquante : ATTRIBUTES")
        if not has_grid_or_tables:
            warnings.append("Aucune section GRID ou TABLES explicite détectée dans l'écran.")
        if not has_instructions:
            warnings.append("Section INSTRUCTIONS recommandée pour la navigation clavier / actions.")

        # 2. Vérification de l'équilibre des accolades
        open_braces = per_code.count("{")
        close_braces = per_code.count("}")
        if open_braces != close_braces:
            errors.append(
                f"Déséquilibre d'accolades dans le fichier .per : {open_braces} ouvrantes vs {close_braces} fermantes."
            )

        # 3. Vérification des délimiteurs de champs [ ]
        open_brackets = per_code.count("[")
        close_brackets = per_code.count("]")
        if open_brackets != close_brackets:
            errors.append(
                f"Déséquilibre de crochets de champ [ ] : {open_brackets} ouvrants vs {close_brackets} fermants."
            )

        return {
            "valid": len(errors) == 0,
            "language": "Genero .per",
            "errors": errors,
            "warnings": warnings,
            "checked_rules": [
                "Présence section LAYOUT/SCREEN",
                "Présence section ATTRIBUTES",
                "Équilibre des délimiteurs { } et [ ]",
            ],
        }

    @classmethod
    def validate_informix_4gl(cls, code_4gl: str | None) -> dict[str, Any]:
        """Vérifie la syntaxe 4GL et le respect de la transaction unique bancaire."""
        if not code_4gl or not code_4gl.strip():
            return {
                "valid": False,
                "language": "Informix-4GL",
                "errors": ["Le code source 4GL est vide ou absent."],
                "warnings": [],
            }

        errors: list[str] = []
        warnings: list[str] = []
        # Nettoyage des commentaires pour éviter les faux positifs
        code_without_comments = re.sub(r"(#|--).*", "", code_4gl)
        code_upper = code_without_comments.upper()

        # 1. Vérification de la présence d'un point d'entrée ou de fonctions
        has_main = bool(re.search(r"\bMAIN\b", code_upper))
        has_function = bool(re.search(r"\bFUNCTION\b", code_upper))
        if not (has_main or has_function):
            errors.append("Aucun bloc MAIN ou FUNCTION défini dans le code 4GL.")

        # Vérification fermeture des blocs FUNCTION
        func_open_count = len(re.findall(r"\bFUNCTION\s+[a-zA-Z0-9_]+\b", code_upper))
        func_close_count = len(re.findall(r"\bEND\s+FUNCTION\b", code_upper))
        if func_open_count != func_close_count:
            errors.append(
                f"Déséquilibre de blocs FUNCTION : {func_open_count} déclarées vs {func_close_count} 'END FUNCTION'."
            )

        # 2. Règle bancaire critique : Contrôle de transaction unique
        begin_work_count = len(re.findall(r"\bBEGIN\s+WORK\b", code_upper))
        commit_work_count = len(re.findall(r"\bCOMMIT\s+WORK\b", code_upper))
        rollback_work_count = len(re.findall(r"\bROLLBACK\s+WORK\b", code_upper))

        if begin_work_count > 0:
            if commit_work_count == 0 and rollback_work_count == 0:
                errors.append(
                    "Violation transactionnelle bancaire : 'BEGIN WORK' présent sans aucun 'COMMIT WORK' ou 'ROLLBACK WORK'."
                )
            elif begin_work_count > (commit_work_count + rollback_work_count):
                warnings.append(
                    "Nombre de 'BEGIN WORK' supérieur aux commits/rollbacks détectés. Risque de transaction suspendue."
                )

        # 3. Vérification des blocs conditionnels IF...END IF
        if_open = len(re.findall(r"(?<!END\s)\bIF\b", code_upper))
        end_if = len(re.findall(r"\bEND\s+IF\b", code_upper))
        if if_open != end_if:
            errors.append(
                f"Déséquilibre conditionnel : {if_open} bloc(s) IF vs {end_if} 'END IF'."
            )

        return {
            "valid": len(errors) == 0,
            "language": "Informix-4GL",
            "errors": errors,
            "warnings": warnings,
            "checked_rules": [
                "Présence MAIN ou FUNCTION",
                "Fermeture des fonctions END FUNCTION",
                "Contrôle de transaction unique BEGIN WORK / COMMIT WORK",
                "Équilibre des blocs IF...END IF",
            ],
        }

    @classmethod
    def validate_flexcube_plsql(cls, plsql_code: str | None) -> dict[str, Any]:
        """Vérifie la syntaxe Oracle PL/SQL pour les modules FLEXCUBE."""
        if not plsql_code or not plsql_code.strip():
            return {
                "valid": False,
                "language": "Oracle PL/SQL Flexcube",
                "errors": ["Le script PL/SQL est vide ou absent."],
                "warnings": [],
            }

        errors: list[str] = []
        warnings: list[str] = []
        code_upper = plsql_code.upper()

        # Vérification création de package
        has_package = "PACKAGE" in code_upper
        if not has_package:
            warnings.append("Aucun mot-clé PACKAGE détecté (script autonome ou DDL).")

        # Vérification gestion des exceptions
        has_exception_handling = "EXCEPTION" in code_upper
        if not has_exception_handling:
            warnings.append(
                "Recommandation bancaire Flexcube : Absence de bloc EXCEPTION détecté dans le package."
            )

        return {
            "valid": len(errors) == 0,
            "language": "Oracle PL/SQL Flexcube",
            "errors": errors,
            "warnings": warnings,
            "checked_rules": [
                "Structure PACKAGE PL/SQL",
                "Présence de blocs de gestion d'exception",
            ],
        }
