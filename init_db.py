"""
Database initialization script.
This script creates the SQLite database and imports data from CSV.
Only run this if you don't have the local_data.db file.
"""

import os
import sqlite3
import pandas as pd

# Configuration
DB_PATH = 'local_data.db'
SCHEMA_PATH = 'facts_assessment_schema.sql'
CSV_PATH = 'cleaned_groundwater_data_final.csv'

def init_db():
    """Initialize SQLite database with schema and data"""
    print(f"Initializing database at {DB_PATH}...")
    
    # Create database with schema
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()
            
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(schema_sql)
        conn.commit()
        print(f"Schema created from {SCHEMA_PATH}")
    else:
        print(f"Warning: Schema file {SCHEMA_PATH} not found.")
        conn = sqlite3.connect(DB_PATH)
    
    # Import data if CSV exists
    if os.path.exists(CSV_PATH):
        print(f"Importing data from {CSV_PATH}...")
        try:
            df = pd.read_csv(CSV_PATH)
            df.to_sql('facts_assessment', conn, if_exists='replace', index=False)
            print(f"Imported {len(df)} rows into facts_assessment table")
        except Exception as e:
            print(f"Error importing data: {str(e)}")
    else:
        print(f"Warning: Data file {CSV_PATH} not found.")
    
    conn.close()
    print("Database initialization complete!")

if __name__ == "__main__":
    init_db()