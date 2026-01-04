import os
import sys
from sqlalchemy import text

# Add backend directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def add_columns():
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Check and add body_fat to user_profiles
                print("Checking user_profiles table...")
                if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] or 'postgres' in app.config['SQLALCHEMY_DATABASE_URI']:
                    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='user_profiles' AND column_name='body_fat'"))
                    if not result.fetchone():
                        print("Adding body_fat column to user_profiles table (PostgreSQL)...")
                        conn.execute(text("ALTER TABLE user_profiles ADD COLUMN body_fat FLOAT"))
                        print("Column added successfully.")
                    else:
                        print("Column body_fat already exists in user_profiles table.")
                else:
                    result = conn.execute(text("PRAGMA table_info(user_profiles)"))
                    columns = [row[1] for row in result.fetchall()]
                    if 'body_fat' not in columns:
                        print("Adding body_fat column to user_profiles table (SQLite)...")
                        conn.execute(text("ALTER TABLE user_profiles ADD COLUMN body_fat FLOAT"))
                        print("Column added successfully.")
                    else:
                        print("Column body_fat already exists in user_profiles table.")

                # Check and add custom_goal and ai_advice to plans
                print("Checking plans table...")
                if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] or 'postgres' in app.config['SQLALCHEMY_DATABASE_URI']:
                    # custom_goal
                    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='plans' AND column_name='custom_goal'"))
                    if not result.fetchone():
                        print("Adding custom_goal column to plans table (PostgreSQL)...")
                        conn.execute(text("ALTER TABLE plans ADD COLUMN custom_goal VARCHAR(50)"))
                        print("Column added successfully.")
                    
                    # ai_advice
                    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='plans' AND column_name='ai_advice'"))
                    if not result.fetchone():
                        print("Adding ai_advice column to plans table (PostgreSQL)...")
                        conn.execute(text("ALTER TABLE plans ADD COLUMN ai_advice TEXT"))
                        print("Column added successfully.")
                else:
                    result = conn.execute(text("PRAGMA table_info(plans)"))
                    columns = [row[1] for row in result.fetchall()]
                    
                    if 'custom_goal' not in columns:
                        print("Adding custom_goal column to plans table (SQLite)...")
                        conn.execute(text("ALTER TABLE plans ADD COLUMN custom_goal VARCHAR(50)"))
                        print("Column added successfully.")
                    
                    if 'ai_advice' not in columns:
                        print("Adding ai_advice column to plans table (SQLite)...")
                        conn.execute(text("ALTER TABLE plans ADD COLUMN ai_advice TEXT"))
                        print("Column added successfully.")
                
                conn.commit()
                print("Database migration completed.")
                        
        except Exception as e:
            print(f"Error migrating database: {e}")

if __name__ == "__main__":
    add_columns()
