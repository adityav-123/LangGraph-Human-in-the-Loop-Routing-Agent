import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.database import SessionLocal, User
from backend.api.auth import get_password_hash

def seed_db():
    db = SessionLocal()
    
    users_to_seed = [
        {"username": "admin", "password": "password123", "role": "admin"},
        {"username": "legal_reviewer", "password": "password123", "role": "legal"},
        {"username": "hr_reviewer", "password": "password123", "role": "hr"},
        {"username": "finance_reviewer", "password": "password123", "role": "finance"},
        {"username": "operations_reviewer", "password": "password123", "role": "operations"},
        {"username": "compliance_reviewer", "password": "password123", "role": "compliance"},
        {"username": "medical_reviewer", "password": "password123", "role": "medical"},
    ]
    
    for u in users_to_seed:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            new_user = User(
                username=u["username"],
                hashed_password=get_password_hash(u["password"]),
                role=u["role"]
            )
            db.add(new_user)
            print(f"Created user: {u['username']} (role: {u['role']})")
        else:
            print(f"User {u['username']} already exists.")
            
    db.commit()
    db.close()
    print("Database seeded with users!")

if __name__ == "__main__":
    seed_db()
