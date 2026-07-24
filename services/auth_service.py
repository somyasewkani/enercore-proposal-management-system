import os
import bcrypt
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def login_user(email: str, password: str):
    """
    Verify credentials against the users table.
    Returns the user row as a dict on success, None on failure.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, full_name, email, password "
                "FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        stored_hash = row["password"]
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()

        if bcrypt.checkpw(password.encode(), stored_hash):
            return dict(row)
        return None

    except psycopg2.Error as e:
        print(f"[auth_service] DB error during login: {e}")
        return None
    finally:
        if conn is not None:
            conn.close()

