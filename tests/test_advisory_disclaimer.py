from ml_model.advisor.response_service import AdvisoryResponseService


def test_advisory_has_disclaimer_when_expert_validation_is_pending():
    service = AdvisoryResponseService()

    response = service.get_advisory(
        "Blight",
        language="en",
        confidence=0.90,
    )

    data = response.to_dict()

    assert "validation" in data
    assert "disclaimer" in data
    assert data["validation"]["expert_validated"] is False
    assert data["disclaimer"]
    assert "expert validation" in data["disclaimer"].lower()


def test_advisory_has_amharic_disclaimer_when_expert_validation_is_pending():
    service = AdvisoryResponseService()

    response = service.get_advisory(
        "Blight",
        language="am",
        confidence=0.90,
    )

    data = response.to_dict()

    assert data["validation"]["expert_validated"] is False
    assert data["disclaimer"]
    assert any("ማረጋገጫ" in word for word in data["disclaimer"].split())


def test_advisory_has_no_disclaimer_after_expert_validation():
    service = AdvisoryResponseService()

    response = service.get_advisory(
        "Blight",
        language="en",
        confidence=0.90,
    )

    response.validation["expert_validated"] = True
    response.disclaimer = ""

    data = response.to_dict()

    assert data["validation"]["expert_validated"] is True
    assert data["disclaimer"] == ""
