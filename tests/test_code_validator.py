"""Tests unitaires du validateur et linter de code bancaire (Genero .per, Informix-4GL, Flexcube)."""

from agentic.services.code_validator import CodeValidator


def test_validate_genero_per_valid() -> None:
    valid_per = """
    SCHEMA bancaire
    LAYOUT (TEXT="Gestion des Virements")
    GRID
    {
    Compte Source:   [f001      ]
    Montant:         [f002      ]
    }
    END
    END
    ATTRIBUTES
    f001 = formonly.cpte_src, NOENTRY;
    f002 = formonly.montant;
    END
    INSTRUCTIONS
    DELIMITERS " "
    END
    """
    report = CodeValidator.validate_genero_per(valid_per)
    assert report["valid"] is True
    assert len(report["errors"]) == 0


def test_validate_genero_per_missing_attributes() -> None:
    invalid_per = """
    LAYOUT
    GRID
    {
    Compte: [f001]
    }
    END
    END
    """
    report = CodeValidator.validate_genero_per(invalid_per)
    assert report["valid"] is False
    assert any("ATTRIBUTES" in err for err in report["errors"])


def test_validate_informix_4gl_transaction_work() -> None:
    valid_4gl = """
    FUNCTION process_virement(p_cpte, p_mnt)
        DEFINE p_cpte CHAR(20), p_mnt DECIMAL(15,2)

        BEGIN WORK
        UPDATE bkcpt SET solde = solde - p_mnt WHERE num_cpte = p_cpte
        IF status != 0 THEN
            ROLLBACK WORK
            RETURN FALSE
        END IF
        COMMIT WORK
        RETURN TRUE
    END FUNCTION
    """
    report = CodeValidator.validate_informix_4gl(valid_4gl)
    assert report["valid"] is True
    assert len(report["errors"]) == 0


def test_validate_informix_4gl_orphan_transaction() -> None:
    invalid_4gl = """
    FUNCTION process_virement()
        BEGIN WORK
        UPDATE bkcpt SET solde = 0
        # Pas de COMMIT WORK ni de ROLLBACK WORK
    END FUNCTION
    """
    report = CodeValidator.validate_informix_4gl(invalid_4gl)
    assert report["valid"] is False
    assert any("transactionnelle" in err.lower() for err in report["errors"])


def test_validate_flexcube_plsql_package() -> None:
    valid_plsql = """
    CREATE OR REPLACE PACKAGE BODY CUSPKS_VIREMENT_CUSTOM AS
        FUNCTION fn_process RETURN BOOLEAN IS
        BEGIN
            RETURN TRUE;
        EXCEPTION
            WHEN OTHERS THEN
                RETURN FALSE;
        END fn_process;
    END CUSPKS_VIREMENT_CUSTOM;
    """
    report = CodeValidator.validate_flexcube_plsql(valid_plsql)
    assert report["valid"] is True
    assert len(report["errors"]) == 0
