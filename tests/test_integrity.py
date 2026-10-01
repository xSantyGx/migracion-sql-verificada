import shutil
import pytest
from migrator.config import Settings
from migrator.db import Engines
from migrator.integrity import (
    check_integrity,
    IntegrityViolation,
    validate_proposal,
    UnsafeProposal,
)


def test_protected_test_cases_cannot_be_changed(tmp_path):
    directory = tmp_path / "benchmark"
    shutil.copytree(Settings().benchmark, directory)
    check_integrity(directory)
    with (directory / "procedures.json").open("a") as file:
        file.write(" ")
    with pytest.raises(IntegrityViolation):
        check_integrity(directory)


@pytest.mark.parametrize(
    "code",
    [
        "DELETE FROM domain.policies;",
        "CREATE FUNCTION migration.get_policy() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$; DROP TABLE domain.policies;",
        "CREATE FUNCTION domain.evil() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$;",
        "CREATE FUNCTION migration.get_policy() RETURNS int LANGUAGE sql SECURITY DEFINER AS $$ SELECT 1 $$;",
        "CREATE FUNCTION migration.get_policy() RETURNS int LANGUAGE C AS 'evil';",
    ],
)
def test_sql_proposals_do_not_escape_installation_contract(code):
    spec = Engines(Settings()).specs()[0]
    with pytest.raises(UnsafeProposal):
        validate_proposal(code, spec)


def test_syntax_error_is_not_labeled_as_cheating():
    validate_proposal("CREATE FUNCTION broken invalid syntax", Engines(Settings()).specs()[0])
