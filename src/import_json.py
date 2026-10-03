"""One-time import of data/album_data.json into data/turntable.db."""
import argparse
import json
import os
import sys
from datetime import date

import db

JSON_FILE = "data/album_data.json"


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}, expected YYYY-MM-DD")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stylus-since",
        type=parse_date,
        required=True,
        metavar="YYYY-MM-DD",
        help="date the current stylus was installed",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.exists(JSON_FILE):
        sys.exit(f"Nothing to import: {JSON_FILE} not found.")

    conn = db.get_connection()
    if conn.execute("SELECT EXISTS (SELECT 1 FROM albums)").fetchone()[0]:
        sys.exit("Database already has albums; refusing to import twice.")

    with open(JSON_FILE) as file:
        data = json.load(file)

    with conn:  # all-or-nothing
        album_ids = {}
        # Listened entries are copies of album dicts, so import them too in
        # case an album was played but later edited out of the library.
        for album in data["albums"] + data["listened"]:
            key = (album["name"].strip(), album["artist"].strip())
            if key not in album_ids:
                album_ids[key] = db.get_or_create_album(conn, *key, round(album["duration"] * 60))

        # The JSON tracker was cleared on every stylus reset, so all
        # remaining listens belong to the stylus currently mounted.
        stylus_id = conn.execute(
            "INSERT INTO stylus (since) VALUES (?)", (f"{args.stylus_since} 00:00:00",)
        ).lastrowid
        conn.executemany(
            "INSERT INTO listened_albums (album_id, stylus_id) VALUES (?, ?)",
            [(album_ids[(a["name"].strip(), a["artist"].strip())], stylus_id) for a in data["listened"]],
        )

    os.rename(JSON_FILE, JSON_FILE + ".imported")
    print(f"Imported {len(album_ids)} albums and {len(data['listened'])} listens.")


if __name__ == "__main__":
    main()
