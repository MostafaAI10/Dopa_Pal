import pytest

from app.services.ai.ingestion import IngestionPipeline
from app.services.ai.schemas import SourceType


def test_readme_example_matches_expected_shape(fixed_now):
    pipeline = IngestionPipeline(reference_time=fixed_now)
    raw = "Need to complete the system specification document by next Friday night, should take about 6 hours total."

    result = pipeline.parse(raw, SourceType.HIGHLIGHT)

    assert result.title == "Complete the system specification document"
    assert result.estimated_hours == 6.0
    assert result.interest_tag == "architecture"
    assert result.deadline.weekday() == 4
    assert result.source_type == SourceType.HIGHLIGHT


def test_empty_text_raises():
    pipeline = IngestionPipeline()
    with pytest.raises(ValueError):
        pipeline.parse("   ", SourceType.MANUAL)


def test_accepts_string_source_type(fixed_now):
    pipeline = IngestionPipeline(reference_time=fixed_now)
    result = pipeline.parse("Call the dentist", "voice")
    assert result.source_type == SourceType.VOICE


def test_no_parseable_signal_still_produces_valid_task(fixed_now):
    pipeline = IngestionPipeline(reference_time=fixed_now)
    result = pipeline.parse("organize my desk", SourceType.MANUAL)
    # Never raises, never blocks — falls back to defaults per Design Rule #2
    assert result.deadline is not None
    assert result.estimated_hours > 0


def test_llm_disabled_by_default_never_calls_client(fixed_now, mocker):
    mock_client = mocker.Mock()
    pipeline = IngestionPipeline(reference_time=fixed_now, llm_client=mock_client, use_llm=False)
    pipeline.parse("Write the report by Friday", SourceType.MANUAL)
    mock_client.enrich_task.assert_not_called()


def test_llm_enrichment_overrides_title_when_enabled(fixed_now, mocker):
    mock_client = mocker.Mock()
    mock_client.enrich_task.return_value = {"refined_title": "Draft the Q3 report", "difficulty": "high"}
    pipeline = IngestionPipeline(reference_time=fixed_now, llm_client=mock_client, use_llm=True)

    result = pipeline.parse("write report by friday", SourceType.MANUAL)

    mock_client.enrich_task.assert_called_once()
    assert result.title == "Draft the Q3 report"


def test_llm_failure_falls_back_to_deterministic_title(fixed_now, mocker):
    from app.services.ai.llm.nvidia_client import NvidiaUnavailableError
    
    mock_client = mocker.MagicMock()
    mock_client.enrich_task.side_effect = NvidiaUnavailableError("connection refused")
    pipeline = IngestionPipeline(reference_time=fixed_now, llm_client=mock_client, use_llm=True)

    result = pipeline.parse("write the report by friday", SourceType.MANUAL)

    assert result.title  # da deterministic title still produced, no exception bubbled up
