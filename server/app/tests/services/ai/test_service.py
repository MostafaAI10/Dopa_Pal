from datetime import timedelta

from app.services.ai.schemas import PinchInput, SourceType
from app.services.ai.service import AIService, IngestOptions


def test_ingest_returns_full_payload_matching_api_contract(fixed_now):
    service = AIService(IngestOptions(use_llm=False))
    raw = "Need to complete the system specification document by next Friday night, should take about 6 hours total."

    result = service.ingest(raw, SourceType.HIGHLIGHT, now=fixed_now)

    assert result.title == "Complete the system specification document"
    assert result.estimated_hours == 6.0
    assert len(result.sub_blocks) == 3
    assert result.sub_blocks[0].sequence == 1
    assert 0.0 <= result.pinch_score <= 100.0


def test_ingest_without_llm_never_touches_ollama(fixed_now, mocker):
    service = AIService(IngestOptions(use_llm=False))
    spy = mocker.patch("app.services.ai.service.OllamaClient")
    service.ingest("write the report by friday", SourceType.MANUAL, now=fixed_now)
    spy.assert_not_called()


def test_score_for_bubble_ranks_candidates(fixed_now):
    service = AIService()
    urgent = PinchInput(
        deadline=fixed_now + timedelta(hours=3), created_at=fixed_now,
        interest_tag=None, estimated_hours=1.0, raw_source_text="finish urgent fix",
    )
    distant = PinchInput(
        deadline=fixed_now + timedelta(days=60), created_at=fixed_now,
        interest_tag=None, estimated_hours=1.0, raw_source_text="someday maybe task",
    )
    ranked = service.score_for_bubble({1: distant, 2: urgent}, state_score=80.0, now=fixed_now)
    assert ranked[0][0] == 2


def test_ingest_is_deterministic_for_same_input(fixed_now):
    service = AIService()
    raw = "Refactor the auth module by next Friday, about 4 hours"
    first = service.ingest(raw, SourceType.MANUAL, now=fixed_now)
    second = service.ingest(raw, SourceType.MANUAL, now=fixed_now)
    assert first.title == second.title
    assert first.deadline == second.deadline
    assert first.sub_blocks == second.sub_blocks
