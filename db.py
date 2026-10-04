import sqlite3
from contextlib import contextmanager

@contextmanager
def connect(path):
    c=sqlite3.connect(path,timeout=15); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try: yield c; c.commit()
    except Exception: c.rollback(); raise
    finally: c.close()

def initialize(path):
    with connect(path) as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE,password TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS recipes(id TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,recipe_id TEXT REFERENCES recipes(id),notes TEXT DEFAULT '',PRIMARY KEY(user_id,recipe_id));
        CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,recipe_id TEXT NOT NULL REFERENCES recipes(id),day TEXT NOT NULL,slot TEXT NOT NULL,batches TEXT NOT NULL,UNIQUE(user_id,day,slot));
        CREATE TABLE IF NOT EXISTS shopping(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,name TEXT NOT NULL,measure TEXT DEFAULT '',origin TEXT DEFAULT '',done INTEGER DEFAULT 0,source_key TEXT,UNIQUE(user_id,source_key));
        CREATE TABLE IF NOT EXISTS limits(bucket TEXT PRIMARY KEY,started INTEGER,count INTEGER);
        ''')
