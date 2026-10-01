from migrator.verifier import training_feedback


def test_reserved_evidence_never_enters_repair_context():
    verification = {
        "compiled": True,
        "installation_error": None,
        "semantic_differences": [],
        "status": "different",
        "cheating_events": [],
        "cases": [
            {
                "id": "visible",
                "args": [1],
                "reserved": False,
                "equal": False,
                "differences": [],
                "source": {"raw_error": None},
                "target": {"raw_error": "type error"},
            },
            {
                "id": "SECRET_HOLDOUT",
                "args": ["SECRET_INPUT"],
                "reserved": True,
                "equal": False,
                "differences": [{"source": "SECRET_VALUE"}],
                "source": {"raw_error": None},
                "target": {"raw_error": None},
            },
        ],
    }
    feedback = training_feedback(verification)
    assert "SECRET" not in str(feedback)
    assert feedback["cases"][0]["target_error"] == "type error"
