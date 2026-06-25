-- Seed 5 test tasks with sub-blocks

-- Create default user (skip if exists)
INSERT INTO users (email, name, language, wake_time_pref)
VALUES ('default_user@dopapal.app', 'Default User', 'en', '07:30:00')
ON CONFLICT (email) DO NOTHING;

-- Get user id
DO $$
DECLARE
  uid INT;
  t1 INT; t2 INT; t3 INT; t4 INT; t5 INT;
  today DATE := CURRENT_DATE;
BEGIN
  SELECT id INTO uid FROM users WHERE email = 'default_user@dopapal.app';

  -- Skip if tasks already exist
  IF EXISTS (SELECT 1 FROM tasks WHERE user_id = uid) THEN
    RAISE NOTICE 'Tasks already exist, skipping seed.';
    RETURN;
  END IF;

  -- Task 1: Build REST API for user auth
  INSERT INTO tasks (user_id, title, source_type, deadline, estimated_hours, interest_tag, pinch_score, status)
  VALUES (uid, 'Build REST API for user auth', 'manual', NOW() + INTERVAL '1 day', 4.0, 'architecture', 85.0, 'pending')
  RETURNING id INTO t1;

  INSERT INTO sub_blocks (task_id, sequence, title, duration_minutes, scheduled_date, status) VALUES
    (t1, 1, 'Design token-based auth flow',          60,  today,              'pending'),
    (t1, 2, 'Implement signup/login endpoints',       90,  today,              'pending'),
    (t1, 3, 'Add JWT middleware and guards',          45,  today + INTERVAL '1 day', 'pending'),
    (t1, 4, 'Write integration tests',                60,  today + INTERVAL '1 day', 'pending');

  -- Task 2: Refactor dashboard component structure
  INSERT INTO tasks (user_id, title, source_type, deadline, estimated_hours, interest_tag, pinch_score, status)
  VALUES (uid, 'Refactor dashboard component structure', 'manual', NOW() + INTERVAL '2 days', 3.0, 'architecture', 70.0, 'pending')
  RETURNING id INTO t2;

  INSERT INTO sub_blocks (task_id, sequence, title, duration_minutes, scheduled_date, status) VALUES
    (t2, 1, 'Extract reusable card components',       45,  today,              'pending'),
    (t2, 2, 'Move state logic to custom hooks',       60,  today + INTERVAL '1 day', 'pending'),
    (t2, 3, 'Update Storybook stories',               30,  today + INTERVAL '2 days', 'pending');

  -- Task 3: Write unit tests for reward service
  INSERT INTO tasks (user_id, title, source_type, deadline, estimated_hours, interest_tag, pinch_score, status)
  VALUES (uid, 'Write unit tests for reward service', 'manual', NOW() + INTERVAL '3 days', 2.0, 'cybersecurity', 55.0, 'pending')
  RETURNING id INTO t3;

  INSERT INTO sub_blocks (task_id, sequence, title, duration_minutes, scheduled_date, status) VALUES
    (t3, 1, 'Test interest vault fact selection',     30,  today,              'pending'),
    (t3, 2, 'Test theme unlock logic',                30,  today,              'pending'),
    (t3, 3, 'Test completion milestone edge cases',   45,  today + INTERVAL '1 day', 'pending');

  -- Task 4: Deploy staging environment on Fly.io
  INSERT INTO tasks (user_id, title, source_type, deadline, estimated_hours, interest_tag, pinch_score, status)
  VALUES (uid, 'Deploy staging environment on Fly.io', 'voice', NOW() + INTERVAL '4 days', 1.5, NULL, 40.0, 'pending')
  RETURNING id INTO t4;

  INSERT INTO sub_blocks (task_id, sequence, title, duration_minutes, scheduled_date, status) VALUES
    (t4, 1, 'Configure Dockerfile and fly.toml',      30,  today + INTERVAL '2 days', 'pending'),
    (t4, 2, 'Set up SQLite persistence volume',       20,  today + INTERVAL '2 days', 'pending'),
    (t4, 3, 'Verify health checks pass',              15,  today + INTERVAL '3 days', 'pending');

  -- Task 5: Research WebSocket scaling patterns
  INSERT INTO tasks (user_id, title, source_type, deadline, estimated_hours, interest_tag, pinch_score, status)
  VALUES (uid, 'Research WebSocket scaling patterns', 'ai', NOW() + INTERVAL '5 days', 2.5, 'architecture', 60.0, 'pending')
  RETURNING id INTO t5;

  INSERT INTO sub_blocks (task_id, sequence, title, duration_minutes, scheduled_date, status) VALUES
    (t5, 1, 'Read Redis pub/sub vs NATS comparison',  40,  today + INTERVAL '1 day', 'pending'),
    (t5, 2, 'Prototype horizontal scaling with sticky sessions', 60, today + INTERVAL '2 days', 'pending'),
    (t5, 3, 'Document findings and recommendations',  30,  today + INTERVAL '3 days', 'pending');

  RAISE NOTICE 'Seeded 5 tasks (16 sub-blocks) for user %', uid;
END $$;
