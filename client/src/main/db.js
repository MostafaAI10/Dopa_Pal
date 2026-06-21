import Database from 'better-sqlite3';
import path from 'path';
import { app } from 'electron';

// Store DB in the user's app data directory to persist between updates
const dbPath = path.join(app.getPath('userData'), 'dopapal.sqlite');
console.log(`[DB] Using database at: ${dbPath}`);
const db = new Database(dbPath, { verbose: console.log });

// Initialize database schema
db.pragma('journal_mode = WAL');

const initDB = () => {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      wake_time_pref TEXT DEFAULT '07:30:00'
    );

    CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      title TEXT NOT NULL,
      raw_source_text TEXT,
      source_type TEXT NOT NULL,
      deadline TEXT,
      estimated_hours REAL,
      interest_tag TEXT,
      status TEXT DEFAULT 'pending',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS sub_blocks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id INTEGER,
      sequence INTEGER NOT NULL,
      duration_minutes INTEGER NOT NULL,
      scheduled_date TEXT,
      status TEXT DEFAULT 'scheduled',
      FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );

    INSERT OR IGNORE INTO users (id, email, name) VALUES (1, 'default_user@dopapal.app', 'Default User');
  `);
};

initDB();

export default db;
