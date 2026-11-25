import datetime
import random
from cs50 import SQL
from werkzeug.security import generate_password_hash
from helpers import compliance

db = SQL("sqlite:///project.db")


def seed_database():
    print("Cleaning old data...")
    db.execute("DELETE FROM missions_stemi")
    db.execute("DELETE FROM missions_stroke")
    db.execute("DELETE FROM missions_trauma")
    db.execute("DELETE FROM users")
    db.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ('missions_stemi', 'missions_stroke', 'missions_trauma', 'users')")

    # 1. Check if protocolls exist  (in case table is empty)
    protocols = {
        "stemi": 10,   # ESC Guideline: 10 minutes to ECG
        "stroke": 70,  # On_scene to CT (On scene time + transport + door-to-CT time)
        "trauma": 60   # On_scene to Trauma bay (Golden Hour of shock)
    }
    for name, target_time in protocols.items():
        existing = db.execute("SELECT id FROM protocolls WHERE name = ?", name)
        if not existing:
            db.execute("INSERT INTO protocolls (name, time) VALUES (?, ?)", name, target_time)

    # 2. Generating Demo-Users & Admin
    demo_users = [
        ("admin", "admin123", "Dispatch Center", 1),
        ("paramedic_max", "demo123", "Station North", 0),
        ("medic_anna", "demo123", "Station North", 0),
        ("emt_lukas", "demo123", "Station South", 0),
        ("doc_sarah", "demo123", "Air Rescue", 0),
    ]

    user_ids = []
    for username, password, work, is_admin in demo_users:
        db.execute(
            "INSERT INTO users (username, hash, work, is_admin) VALUES (?, ?, ?, ?)",
            username,
            generate_password_hash(password),
            work,
            is_admin
        )
        row = db.execute("SELECT id FROM users WHERE username = ?", username)
        user_ids.append(row[0]["id"])

    # 3. Generate random entries from the last 7 days
    mission_configs = [
        ("stemi", "missions_stemi", "ecg"),
        ("stroke", "missions_stroke", "ct"),
        ("trauma", "missions_trauma", "trauma"),
    ]

    today = datetime.date.today()

    for proto_name, table_name, second_col in mission_configs:
        proto_row = db.execute("SELECT id, time FROM protocolls WHERE name = ?", proto_name)
        proto_id = proto_row[0]["id"]
        target_minutes = proto_row[0]["time"]
        target_time_list = [{"time": target_minutes}]

        # generate 35 random missions per protocol
        for _ in range(35):
            days_ago = random.randint(0, 6)
            mission_date = (today - datetime.timedelta(days=days_ago)).isoformat()
            uid = random.choice(user_ids)

            # random start time between 00:00 and 23:30
            start_dt = datetime.datetime(2026, 1, 1, random.randint(0, 23), random.randint(0, 30))

            # realistic mission durations: 50% to 115% of targettime
            duration = random.randint(int(target_minutes * 0.5), int(target_minutes * 1.15))
            end_dt = start_dt + datetime.timedelta(minutes=duration)

            on_scene_str = start_dt.strftime("%H:%M")
            second_str = end_dt.strftime("%H:%M")
            is_compliant = compliance(on_scene_str, second_str, target_time_list)

            db.execute(
                f"INSERT INTO {table_name} (user_id, protocol_id, on_scene, {second_col}, compliance, date) VALUES (?, ?, ?, ?, ?, ?)",
                uid, proto_id, on_scene_str, second_str, is_compliant, mission_date
            )

    print("Database successfully seeded with demo users and random missions!")


if __name__ == "__main__":
    seed_database()
