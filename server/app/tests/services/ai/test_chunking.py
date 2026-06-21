from datetime import datetime, timedelta

from app.services.ai.chunking import ChunkingEngine


def test_short_task_produces_single_block(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=5)
    # 1.0 hours = 60 mins -> should split into two blocks of 30 mins each
    result = engine.plan_sub_blocks(estimated_hours=1.0, deadline=deadline, reference_time=fixed_now)
    assert len(result.sub_blocks) == 2
    assert result.sub_blocks[0].duration_minutes == 30
    assert result.sub_blocks[1].duration_minutes == 30
    assert not result.was_compressed


def test_six_hour_task_splits_into_multiple_blocks(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=10)
    # 6.0 hours = 360 mins -> 360/45 = 8 blocks of 45 mins
    result = engine.plan_sub_blocks(estimated_hours=6.0, deadline=deadline, reference_time=fixed_now)
    assert len(result.sub_blocks) == 8
    assert all(b.duration_minutes == 45 for b in result.sub_blocks)


def test_blocks_spread_across_window_not_clustered_at_deadline(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=14)
    result = engine.plan_sub_blocks(estimated_hours=6.0, deadline=deadline, reference_time=fixed_now)
    dates = [b.scheduled_date for b in result.sub_blocks]
    assert dates[0] == fixed_now.date()  # starts today, no delay
    assert dates == sorted(dates)        # strictly increasing
    assert dates[-1] < deadline.date()   # buffer before the actual deadline


def test_complex_task_produces_shorter_blocks(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now + timedelta(days=10)
    # 1 hour = 60 mins. With complex title, should split into shorter blocks
    # 60 mins / ~33 target = 2 blocks of 30
    # Let's use 100 minutes instead
    # 100 mins -> complex -> target ~25 mins -> 4 blocks of 25
    result = engine.plan_sub_blocks(
        estimated_hours=1.6667, # ~100 minutes
        deadline=deadline, 
        reference_time=fixed_now,
        title="Design system architecture implementation plan",
        interest_tag="engineering"
    )
    assert len(result.sub_blocks) == 4
    assert all(24 <= b.duration_minutes <= 26 for b in result.sub_blocks)


def test_overdue_deadline_compresses_to_today(fixed_now):
    engine = ChunkingEngine()
    deadline = fixed_now - timedelta(days=2)  # already past
    # 4.0 hours = 240 mins -> ceil(240/45) = 6 blocks of 40 mins
    result = engine.plan_sub_blocks(estimated_hours=4.0, deadline=deadline, reference_time=fixed_now)
    assert result.was_compressed
    assert len(result.sub_blocks) == 6
    assert all(b.scheduled_date == fixed_now.date() for b in result.sub_blocks)


def test_custom_block_size_respected(fixed_now):
    engine = ChunkingEngine(block_minutes=30)
    deadline = fixed_now + timedelta(days=5)
    # 1.5 hours = 90 mins -> 90 / 30 = 3 blocks of 30 mins
    result = engine.plan_sub_blocks(estimated_hours=1.5, deadline=deadline, reference_time=fixed_now)
    assert len(result.sub_blocks) == 3
    assert all(b.duration_minutes <= 30 for b in result.sub_blocks)
