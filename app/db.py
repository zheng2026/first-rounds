"""SQLite (stdlib) schema + helpers."""
import os
import sqlite3
import datetime as dt

from . import ROOT

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, note_date TEXT, text TEXT, kind TEXT DEFAULT 'call',
  answers_question_id INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS extractions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, note_id INTEGER, model TEXT, variant TEXT,
  output_json TEXT, raw_text TEXT, error TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS entries(
  id INTEGER PRIMARY KEY AUTOINCREMENT, note_id INTEGER, problem TEXT, date TEXT, date_precision TEXT,
  sort_key TEXT, what TEXT, source TEXT, department TEXT, test TEXT, test_where TEXT, result TEXT,
  med_name TEXT, med_event TEXT, med_date TEXT, med_dose TEXT, med_rule TEXT, med_reason TEXT,
  helps_json TEXT, worsens_json TEXT);
CREATE TABLE IF NOT EXISTS questions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, note_id INTEGER, text TEXT, answered_at TEXT, answer_note_id INTEGER);
CREATE TABLE IF NOT EXISTS todos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, note_id INTEGER, kind TEXT, text TEXT, detail TEXT,
  done_at TEXT, created_at TEXT, entry_id INTEGER);
CREATE TABLE IF NOT EXISTS current_medicines(
  id INTEGER PRIMARY KEY AUTOINCREMENT, note_id INTEGER, text TEXT);
CREATE TABLE IF NOT EXISTS ask_doctor(
  id INTEGER PRIMARY KEY AUTOINCREMENT, note_id INTEGER, problem TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS cards(
  id INTEGER PRIMARY KEY AUTOINCREMENT, problem TEXT, source_hash TEXT, en_json TEXT, zh_json TEXT,
  zh_error TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS ix_cards_hash ON cards(source_hash);
CREATE INDEX IF NOT EXISTS ix_entries_note ON entries(note_id);
CREATE INDEX IF NOT EXISTS ix_todos_note ON todos(note_id);
CREATE INDEX IF NOT EXISTS ix_questions_note ON questions(note_id);
"""


def db_path():
    p = os.environ.get("FR_DB") or os.path.join("data", "firstrounds.sqlite")
    if not os.path.isabs(p):
        p = os.path.join(ROOT, p)
    return p


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    c = sqlite3.connect(db_path(), timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.dirname(db_path()), exist_ok=True)
    c = connect()
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
        c.commit()
    finally:
        c.close()
