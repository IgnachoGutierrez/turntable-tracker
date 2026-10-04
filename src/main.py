import os
import sys
from datetime import datetime, timezone

import db
from import_json import JSON_FILE
import json
import anthropic

THRESHOLD_HOURS = 300
WARNING_THRESHOLD = 280

def add_album(conn):
    """Add a new album to the library."""
    name = input("Enter album name: ")
    artist = input("Enter artist name: ")
    try:
        duration = float(input("Enter album duration in minutes: "))
    except ValueError:
        print("Invalid duration. Please enter a number.")
        return
    if duration <= 0:
        print("Invalid duration. Please enter a positive number.")
        return
    db.add_album(conn, name, artist, duration)
    print(f"Album '{name}' by {artist} added to library.")

def mark_listened(conn):
    """Mark an album as listened."""
    albums = db.list_albums(conn)
    if not albums:
        print("No albums available in the library. Add albums first.")
        return

    print("\nAvailable Albums:")
    for idx, album in enumerate(albums, 1):
        print(f"{idx}. {album['name']} by {album['artist']} ({album['duration_seconds'] / 60:g} min)")

    try:
        choice = int(input(f"Select an album to mark as listened (1 to {len(albums)}): ")) - 1
        if 0 <= choice < len(albums):
            album = albums[choice]
            db.mark_listened(conn, album["album_id"])
            print(f"Album '{album['name']}' by {album['artist']} marked as listened.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def show_playtime(conn):
    """Display total playtime and hours remaining."""
    total_hours = db.current_stylus_hours(conn)
    remaining_hours = max(0, THRESHOLD_HOURS - total_hours)
    print(f"\nTotal playtime: {total_hours:.2f} hours")
    if total_hours >= THRESHOLD_HOURS:
        print("🔔 Replace your stylus! You've exceeded 300 hours.")
    elif total_hours >= WARNING_THRESHOLD:
        print("⚠️ Warning: Approaching 300 hours.")
    print(f"Hours remaining until 300: {remaining_hours:.2f}")

def replace_stylus(conn):
    """Install a new stylus, restarting the playtime count."""
    confirm = input("Are you sure you want to replace the stylus? (yes/no): ").lower()
    if confirm == "yes":
        db.replace_stylus(conn)
        print("New stylus installed. Playtime tracker reset.")


def resolve_vinyl_names_with_claude(truncated_names: list[str], catalog: list[dict]) -> dict:
    """Use Claude to match truncated vinyl names against the catalog.

    Returns a dict mapping each input name to the matched catalog album dict,
    or None if no confident match was found.
    """
    catalog_text = "\n".join(
        f'- "{a["name"]}" by {a["artist"]}' for a in catalog
    )
    names_text = "\n".join(f"{i+1}. {name}" for i, name in enumerate(truncated_names))

    prompt = f"""You are helping match truncated or informal vinyl record names to their correct
    entries in a music catalog.

    CATALOG (exact names and artists):
    {catalog_text}

    TRUNCATED NAMES TO MATCH:
    {names_text}

    For each truncated name, find the best matching album in the catalog above.
    Return a JSON object with a "matches" array. Each element must have:
    - "input": the original truncated name exactly as given
    - "match": the exact album name from the catalog, or null if no confident match exists

    Only match against albums that are in the catalog. Do not invent entries."""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        output_config={"format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "input": {"type": "string"},
                                "match": {"type": ["string", "null"]},
                            },
                            "required": ["input", "match"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["matches"],
                "additionalProperties": False,
            },
        }},
        messages=[{"role": "user", "content": prompt}],
    )

    text_block = next((b for b in response.content if b.type == "text"), None)
    if not text_block:
        return {}

    catalog_by_name = {a["name"]: a for a in catalog}
    result = json.loads(text_block.text)
    return {
        item["input"]: catalog_by_name[item["match"]]
        for item in result["matches"]
        if item["match"] and item["match"] in catalog_by_name
    }

def bulk_import_listened(conn):
    """Bulk import listened albums from a text file."""
    filename = input("Enter the text file name (e.g., bulk_vinyl.txt): ")
    
    if not os.path.exists(filename):
        print(f"File '{filename}' not found.")
        return

    with open(filename, 'r') as f:
        # Read lines, strip whitespace, and ignore empty lines
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # Create a lookup dictionary for case-insensitive matching
    albums = db.list_albums(conn)
    library_lookup = {album["name"].lower(): album for album in albums}

    matched = []
    not_found = []

    for name in lines:
        lower_name = name.lower()
        if lower_name in library_lookup:
            matched.append(library_lookup[lower_name])
        else:
            not_found.append(name)

    # Try to resolve unmatched names using Claude
    if not_found:
        print(f"\n🤖 {len(not_found)} name(s) not found by exact match — asking Claude...")
        try:
            resolved = resolve_vinyl_names_with_claude(not_found, albums)
        except anthropic.APIError as e:
            print(f"  Could not reach Claude ({e}); skipping fuzzy matching.")
            resolved = {}
        still_missing = []
        for name in not_found:
            album = resolved.get(name)
            if album:
                matched.append(album)
                print(f"  ✓ \"{name}\" → \"{album['name']}\" by {album['artist']}")
            else:
                still_missing.append(name)
        not_found = still_missing

    if matched:
        db.mark_listened_many(conn, [album["album_id"] for album in matched])
        print(f"\n✅ Successfully marked {len(matched)} albums as listened.")

    if not_found:
        print("\n⚠️ The following albums were skipped (not found in library):")
        for missing in not_found:
            print(f"  - {missing}")
        print("Please add them to the library first (Option 1) before tracking them.")

def time_ago(created_at):
    """Format a UTC timestamp from the database as a relative time, e.g. '2 hours ago'."""
    dt = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - dt).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if seconds < 172800:
        return "yesterday"
    local = dt.astimezone()
    return f"{local:%b} {local.day}"

def show_recent_listened(conn):
    """Display the 20 most recently listened albums."""
    recent = db.list_recent_listens(conn)
    if not recent:
        print("\nNo albums listened to yet.")
        return

    CYAN, RESET = "\033[96m", "\033[0m"

    print("\nLast 20 listened albums:")
    for i, album in enumerate(recent, 1):
        print(f"{i:>2}. {album['name']} by {CYAN}{album['artist']}{RESET} ({time_ago(album['created_at'])})")

def main():
    """Main CLI menu."""
    if os.path.exists(JSON_FILE):
        sys.exit(f"Found {JSON_FILE}. Run 'python3 src/import_json.py --stylus-since YYYY-MM-DD' first to move it into the database.")

    conn = db.get_connection()
    while True:
        print("\nTurntable Tracker")
        print("1. Add Album to Library")
        print("2. Mark Album as Listened")
        print("3. Show Total Playtime")
        print("4. Replace Stylus")
        print("5. Bulk Import Listened Albums")
        print("6. Recent Listens")
        print("7. Exit")
        choice = input("Select an option: ")

        if choice == "1":
            add_album(conn)
        elif choice == "2":
            mark_listened(conn)
        elif choice == "3":
            show_playtime(conn)
        elif choice == "4":
            replace_stylus(conn)
        elif choice == "5":
            bulk_import_listened(conn)
        elif choice == "6":
            show_recent_listened(conn)
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
