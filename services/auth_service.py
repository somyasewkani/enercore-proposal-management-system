"""
Enercore AI Solar Proposal Generator
services/auth_service.py

Authentication service verifying user credentials against users table
supporting hybrid SQLite and PostgreSQL database adapters.
"""

import os
import bcrypt
import sqlite3
from typing import Dict, Any, Optional
from database.connection import get_connection


def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verify user credentials against the users table.
    Returns the user row details as a dict on success, None on failure.
    """
    conn = None
    try:
        conn = get_connection()
        is_sqlite = isinstance(conn, sqlite3.Connection)
        cur = conn.cursor()
        
        query = "SELECT id, full_name, email, password, role FROM users WHERE email = ?;" if is_sqlite else "SELECT id, full_name, email, password, role FROM users WHERE email = %s;"
        cur.execute(query, (email,))
        row = cur.fetchone()
        
        if row is None:
            return None
            
        if is_sqlite:
            stored_hash = row["password"]
            user_id = row["id"]
            full_name = row["full_name"]
            user_email = row["email"]
            user_role = row["role"]
        else:
            if isinstance(row, dict):
                stored_hash = row["password"]
                user_id = row["id"]
                full_name = row["full_name"]
                user_email = row["email"]
                user_role = row["role"]
            else:
                user_id = row[0]
                full_name = row[1]
                user_email = row[2]
                stored_hash = row[3]
                user_role = row[4]
                
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode()
            
        if bcrypt.checkpw(password.encode(), stored_hash):
            return {
                "id": user_id,
                "full_name": full_name,
                "email": user_email,
                "role": user_role
            }
        return None
        
    except Exception as e:
        print(f"[auth_service] DB error during login: {e}")
        return None
    finally:
        if conn is not None:
            conn.close()
