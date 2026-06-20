from app.services.ai.parsers.interest_tagger import tag_interest


def test_tags_architecture_keyword():
    result = tag_interest("Complete the system specification document")
    assert result.tag == "architecture"
    assert result.confidence > 0


def test_tags_cybersecurity_keyword():
    result = tag_interest("Review the firewall rules and patch the vulnerability")
    assert result.tag == "cybersecurity"


def test_tags_language_learning_keyword():
    result = tag_interest("Refactor German vocabulary array definitions")
    # Contains both "refactor" (programming-adjacent, not in keyword list)
    # and "german"/"vocabulary" (language_learning) - should pick the
    # taxonomy with the most hits.
    assert result.tag == "language_learning"


def test_no_match_returns_none():
    result = tag_interest("Take out the trash")
    assert result.tag is None
    assert result.confidence == 0.0


def test_more_keyword_hits_wins_tiebreak():
    # "model" + "training" + "dataset" -> 3 ai_ml hits should beat a
    # single incidental hit from another category.
    result = tag_interest("Train the model on the new dataset")
    assert result.tag == "ai_ml"
