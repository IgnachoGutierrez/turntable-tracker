import json
import os

DATA_FILE = "data/album_data.json"
THRESHOLD_HOURS = 300
WARNING_THRESHOLD = 280

def load_data():
    """Load album and playtime data from file."""
    if not os.path.exists(DATA_FILE):
        return {"albums": [], "listened": []}
    with open(DATA_FILE, "r") as file:
        return json.load(file)

def save_data(data):
    """Save album and playtime data to file."""
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

def add_album(data):
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
    album = {"name": name, "artist": artist, "duration": duration}
    data["albums"].append(album)
    save_data(data)
    print(f"Album '{name}' by {artist} added to library.")

def mark_listened(data):
    """Mark an album as listened."""
    if not data["albums"]:
        print("No albums available in the library. Add albums first.")
        return
    
    print("\nAvailable Albums:")
    for idx, album in enumerate(data["albums"], 1):
        print(f"{idx}. {album['name']} by {album['artist']} ({album['duration']} min)")
    
    try:
        if 0 <= choice < len(data["albums"]):
            album = data["albums"][choice]
            data["listened"].append(album)
            save_data(data)
        choice = int(input(f"Select an album to mark as listened (1 to {len(albums)}): ")) - 1
            print(f"Album '{album['name']}' by {album['artist']} marked as listened.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def calculate_total_hours(data):
    """Calculate total playtime in hours from listened albums."""
    return sum(album["duration"] for album in data["listened"]) / 60

def show_playtime(data):
    """Display total playtime and hours remaining."""
    total_hours = calculate_total_hours(data)
    remaining_hours = max(0, THRESHOLD_HOURS - total_hours)
    print(f"\nTotal playtime: {total_hours:.2f} hours")
    if total_hours >= THRESHOLD_HOURS:
        print("🔔 Replace your stylus! You've exceeded 300 hours.")
    elif total_hours >= WARNING_THRESHOLD:
        print("⚠️ Warning: Approaching 300 hours.")
    print(f"Hours remaining until 300: {remaining_hours:.2f}")

def reset_timer(data):
    """Reset playtime tracker."""
    confirm = input("Are you sure you want to reset the playtime tracker? (yes/no): ").lower()
    if confirm == "yes":
        data["listened"].clear()
        save_data(data)
        print("Playtime tracker reset.")

def main():
    """Main CLI menu."""
    data = load_data()
    while True:
        print("\nTurntable Tracker")
        print("1. Add Album to Library")
        print("2. Mark Album as Listened")
        print("3. Show Total Playtime")
        print("4. Reset Playtime Tracker")
        print("5. Exit")
        choice = input("Select an option: ")

        if choice == "1":
            add_album(data)
        elif choice == "2":
            mark_listened(data)
        elif choice == "3":
            show_playtime(data)
        elif choice == "4":
            reset_timer(data)
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
