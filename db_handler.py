import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "acronyms.db")
ACRONYM_FIELDS = ("meaning", "teams", "project", "notes", "additionalMeaning")

def init_db():
#Creates the acronym table if it doesn't exist
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acronyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acronym TEXT UNIQUE NOT NULL,
            meaning TEXT NOT NULL,
            teams TEXT,
            project TEXT,
            notes TEXT,
            additionalMeaning TEXT     
        )
    """)
    conn.commit()
    conn.close()

def lookup_acronym(acronym: str):
    """
    Look up an acronym in the database and return its details.
    
    Args:
        acronym (str): The acronym to search for (case-insensitive).
    
    Returns:
        dict: A dictionary with keys: meaning, teams, project, notes, additionalMeaning.
              Returns None if the acronym is not found.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # discover existing columns
        cursor.execute("PRAGMA table_info(acronyms)")
        cols = [r[1] for r in cursor.fetchall()]

        # map DB column names to the desired return keys
        col_map = {
            "meaning": "meaning",
            "teams": "teams",
            "project": "project",
            "notes": "notes",
            "additionalMeaning": "additionalMeaning",
        }

        # select only columns that actually exist in the DB, preserving order
        select_cols = [c for c in ACRONYM_FIELDS if c in cols]
        if not select_cols:
            return None

        sql = f"SELECT {', '.join(select_cols)} FROM acronyms WHERE acronym = ? COLLATE NOCASE"
        cursor.execute(sql, (acronym,))  
        row = cursor.fetchone()

    if not row:
        return None

    # map selected columns to normalized keys
    result = {}
    for idx, db_col in enumerate(select_cols):
        key = col_map.get(db_col, db_col)
        result[key] = row[idx] if row[idx] is not None else ""

    # ensure all expected keys exist in the result dict
    # (even if some columns are missing from the DB schema)
    for k in ACRONYM_FIELDS:
        result.setdefault(k, "")

    return result

def add_acronym(acronym: str, meaning: str):
    #Adds a new acronym to the database
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT OR IGNORE INTO acronyms (acronym, meaning, teams, project, notes, additionalMeaning) VALUES (?, ?, ?, ?, ?, ?)", (acronym.upper(), meaning, "", "", "", ""))
        conn.commit()
    except Exception as e:
        print(f"Error adding acronym: {e}")
    finally:
        conn.close()

