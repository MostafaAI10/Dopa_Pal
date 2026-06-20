from datetime import datetime, timedelta

from app.services.ai.chunking import ChunkingEngine


def test_short_task_produces_single_block(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=5)
    result = engine.plan_sub_blocks(estimated_hours=1.0, deadline=deadline, reference_time=fixed_now)
    assert len(result.sub_blocks) == 1
    assert result.sub_blocks[0].duration_minutes == 60
    assert not result.was_compressed


def test_six_hour_task_splits_into_three_two_hour_blocks(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=10)
    result = engine.plan_sub_blocks(estimated_hours=6.0, deadline=deadline, reference_time=fixed_now)
    assert len(result.sub_blocks) == 3
    assert all(b.duration_minutes == 120 for b in result.sub_blocks)


def test_blocks_spread_across_window_not_clustered_at_deadline(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=14)
    result = engine.plan_sub_blocks(estimated_hours=6.0, deadline=deadline, reference_time=fixed_now)
    dates = [b.scheduled_date for b in result.sub_blocks]
    assert dates[0] == fixed_now.date()  # starts today, no delay
    assert dates == sorted(dates)        # strictly increasing
    assert dates[-1] < deadline.date()   # buffer before the actual deadline


def test_small_remainder_folds_into_last_block(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=10)
    # 2h15m total -> remainder (15 min) is below MIN_STANDALONE_REMAINDER_MINUTES
    result = engine.plan_sub_blocks(estimated_hours=2.25, deadline=deadline, reference_time=fixed_now)
    assert len(result.sub_blocks) == 1
    assert result.sub_blocks[0].duration_minutes == 135


def test_overdue_deadline_compresses_to_today(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now - timedelta(days=2)  # already past
    result = engine.plan_sub_blocks(estimated_hours=4.0, deadline=deadline, reference_time=fixed_now)
    assert result.was_compressed
    assert all(b.scheduled_date == fixed_now.date() for b in result.sub_blocks)


def test_custom_block_size_respected(fixed_now):
    engine = ChunkingEngine(block_minutes=45)
    deadline = fixed_now + timedelta(days=5)
    result = engine.plan_sub_blocks(estimated_hours=1.5, deadline=deadline, reference_time=fixed_now)
    assert all(b.duration_minutes <= 45 for b in result.sub_blocks)
