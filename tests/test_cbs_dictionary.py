"""Tests unitaires du référentiel CBS et de la politique anti-hallucination."""

from agentic.services.cbs_dictionary import CbsDictionaryService


def test_get_known_tables_amplitude_and_flexcube() -> None:
    amplitude_tables = CbsDictionaryService.get_known_tables("AMPLITUDE")
    assert "BKCPT" in amplitude_tables
    assert "BKTRA" in amplitude_tables
    assert "CLI" in amplitude_tables

    flexcube_tables = CbsDictionaryService.get_known_tables("FLEXCUBE")
    assert "STTM_CUSTOMER" in flexcube_tables
    assert "CSTM_FUNCTION_USER" in flexcube_tables


def test_validate_cbs_dependencies_rejects_hallucinated_tables() -> None:
    declared = [
        "Table BKCPT (comptes)",
        "Table BKMVT_INVENTEE (mouvements fictifs)",
    ]
    unknown = CbsDictionaryService.validate_cbs_dependencies(declared, "AMPLITUDE")

    assert len(unknown) == 1
    assert "BKMVT_INVENTEE" in unknown[0]


def test_tag_undocumented_assumptions() -> None:
    doc = ["Gestion des comptes BKCPT avec solde minimum de 5000 XOF."]
    assumptions = [
        "Le solde minimum du compte est de 5000 XOF.",
        "Le client doit être âgé de plus de 21 ans pour ouvrir un compte.",
    ]

    tagged = CbsDictionaryService.tag_undocumented_assumptions(assumptions, doc)

    # La règle documentée ne doit pas être altérée
    assert "[NON DOCUMENTÉ" not in tagged[0]
    # La règle non documentée doit être étiquetée
    assert "[NON DOCUMENTÉ - À VALIDER MÉTIER]" in tagged[1]
