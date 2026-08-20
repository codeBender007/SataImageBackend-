# from database.database import engine, Base, sessionLocal
from database.db import engine , Base , sessionLocal
from models.userModels import User
from datetime import datetime, timezone

def create_initial_admin():
    # 1. Tables create karein agar abhi tak nahi bani hain
    Base.metadata.create_all(bind=engine)

    # 2. Database Session start karein
    db = sessionLocal()

    try:
        # Admin Details
        admin_username = "admin"
        admin_email = "admin@example.com"
        admin_emp_id = "EMP001"

        # 3. Check karein ki user pehle se exist karta hai ya nahi
        existing_user = db.query(User).filter(
            (User.username == admin_username) | (User.email == admin_email)
        ).first()

        if existing_user:
            print(f"⚠️ Admin user '{admin_username}' pehle se database me exist karta hai.")
            return

        # 4. Naya Admin User object banayein
        new_admin = User(
            employee_id=admin_emp_id,
            full_name="System Administrator",
            username=admin_username,
            email=admin_email,
            password="adminpassword123",  # Apne hisab se password change kar lein
            role="admin",
            designation="Super Admin",
            department="IT",
            status="Active",
            created_at=datetime.now(timezone.utc)
        )

        # 5. DB me insert aur commit karein
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        print("========================================")
        print("✅ Admin User Successfully Created!")
        print(f"👉 Username: {admin_username}")
        print(f"👉 Password: adminpassword123")
        print(f"👉 Employee ID: {admin_emp_id}")
        print(f"👉 Role: {new_admin.role}")
        print("========================================")

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin()