import os
import sys

import db
from import_json import JSON_FILE

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
        print("5. Exit")
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
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
