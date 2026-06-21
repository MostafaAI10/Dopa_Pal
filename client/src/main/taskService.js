import db from './db.js';

function createSubBlocks(taskId, estimatedHours) {
  // Simple scheduling algorithm: break the task into 30-minute sub-blocks
  const totalMinutes = Math.round((estimatedHours || 2.0) * 60);
  const blockDuration = 30;
  const numBlocks = Math.ceil(totalMinutes / blockDuration);
  
  const insertSubBlock = db.prepare(`
    INSERT INTO sub_blocks (task_id, sequence, duration_minutes) 
    VALUES (?, ?, ?)
  `);

  const transaction = db.transaction(() => {
    for (let i = 0; i < numBlocks; i++) {
      insertSubBlock.run(taskId, i + 1, blockDuration);
    }
  });
  
  transaction();
}

export function saveTask({ title, rawSourceText, sourceType, deadline, estimatedHours, interestTag }) {
  const userId = 1; // Default user from db.js
  
  const insertTask = db.prepare(`
    INSERT INTO tasks (user_id, title, raw_source_text, source_type, deadline, estimated_hours, interest_tag)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  
  const result = insertTask.run(
    userId, 
    title, 
    rawSourceText || '', 
    sourceType, 
    deadline ? new Date(deadline).toISOString() : null, 
    estimatedHours || 2.0, 
    interestTag || null
  );
  
  const taskId = result.lastInsertRowid;
  createSubBlocks(taskId, estimatedHours);
  
  return { id: taskId, title, status: 'pending' };
}
