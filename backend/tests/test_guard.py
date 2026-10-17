from app.services.guard import validate_grounding


def test_numbers_must_be_grounded():
    ok, problems = validate_grounding("Inflation rose to 12.5%", ["Prices rose to 12.5% this year."])
    assert ok, problems


def test_unknown_number_flagged():
    ok, problems = validate_grounding("Inflation rose to 99%", ["Prices rose modestly."])
    assert not ok
    assert any("99" in p for p in problems)


def test_entities_grounded():
    ok, _ = validate_grounding("Pakistan welcomed the decision", ["Pakistan welcomed the decision."])
    assert ok


def test_unknown_mid_sentence_entity_flagged():
    ok, problems = validate_grounding(
        "Officials met Reuters editors", ["Officials met local editors."]
    )
    assert not ok
    assert any("Reuters" in p for p in problems)
