import os
import sqlite3

DB_FILE = "data/turntable.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS artists (
    artist_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS albums (
    album_id         INTEGER PRIMARY KEY,
    name             TEXT NOT NULL,
    artist_id        INTEGER NOT NULL REFERENCES artists(artist_id),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
    UNIQUE (name, artist_id)
);

CREATE TABLE IF NOT EXISTS stylus (
    stylus_id INTEGER PRIMARY KEY,
    since     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS listened_albums (
    listened_album_id INTEGER PRIMARY KEY,
    album_id          INTEGER NOT NULL REFERENCES albums(album_id),
    stylus_id         INTEGER NOT NULL REFERENCES stylus(stylus_id),
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_listened_albums_stylus ON listened_albums(stylus_id);
"""

def get_connection():
    """Open the database, creating the file and schema if needed."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite leaves this off by default
    conn.executescript(SCHEMA)
    return conn

def _get_or_create_artist(conn, name):
    """Return the artist's ID, inserting the artist if it doesn't exist."""
    conn.execute("INSERT OR IGNORE INTO artists (name) VALUES (?)", (name,))
    return conn.execute("SELECT artist_id FROM artists WHERE name = ?", (name,)).fetchone()["artist_id"]

def get_or_create_album(conn, name, artist_name, duration_seconds):
    """Return the album's ID, inserting the album (and artist) if it doesn't exist."""
    artist_id = _get_or_create_artist(conn, artist_name)
    conn.execute(
        "INSERT OR IGNORE INTO albums (name, artist_id, duration_seconds) VALUES (?, ?, ?)",
        (name, artist_id, duration_seconds),
    )
    return conn.execute(
        "SELECT album_id FROM albums WHERE name = ? AND artist_id = ?", (name, artist_id)
    ).fetchone()["album_id"]

def add_album(conn, name, artist_name, duration_minutes):
    """Add an album to the library."""
    with conn:
        get_or_create_album(conn, name.strip(), artist_name.strip(), round(duration_minutes * 60))

def list_albums(conn):
    """Return all albums with their artist name, ordered by artist then album."""
    return conn.execute("""
        SELECT al.album_id, al.name, ar.name AS artist, al.duration_seconds
        FROM albums al JOIN artists ar USING (artist_id)
        ORDER BY ar.name, al.name
    """).fetchall()

def current_stylus_id(conn):
    """Return the most recently installed stylus, creating the first one on a fresh database."""
    row = conn.execute("SELECT stylus_id FROM stylus ORDER BY stylus_id DESC LIMIT 1").fetchone()
    if row:
        return row["stylus_id"]
    with conn:
        return conn.execute("INSERT INTO stylus DEFAULT VALUES").lastrowid

def mark_listened(conn, album_id):
    """Record a listen of the album on the current stylus."""
    stylus_id = current_stylus_id(conn)
    with conn:
        conn.execute(
            "INSERT INTO listened_albums (album_id, stylus_id) VALUES (?, ?)",
            (album_id, stylus_id),
        )

def replace_stylus(conn):
    """Install a new stylus; playtime counts from zero again."""
    with conn:
        conn.execute("INSERT INTO stylus DEFAULT VALUES")

def current_stylus_hours(conn):
    """Return the total hours played on the current stylus."""
    row = conn.execute("""
        SELECT COALESCE(SUM(al.duration_seconds), 0) AS seconds
        FROM listened_albums la JOIN albums al USING (album_id)
        WHERE la.stylus_id = ?
    """, (current_stylus_id(conn),)).fetchone()
    return row["seconds"] / 3600
