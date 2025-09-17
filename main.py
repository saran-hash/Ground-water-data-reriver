import sqlite3
from fastapi import FastAPI, Query
import os
from dotenv import load_dotenv
# Import the hybrid SQL generator that uses both model and rules
from text2sql_hybrid import generate_sql, run_sql

load_dotenv()

app = FastAPI()

DB_PATH = os.getenv('SQLITE_DB_PATH', 'local_data.db')
SCHEMA_PATH = 'facts_assessment_schema.sql'

# Initialize SQLite DB and create table if not exists
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts_assessment';")
if not cursor.fetchone():
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
conn.close()

@app.post("/nl2sql")
def nl2sql(question: str, debug: bool = False):
    try:
        # Generate SQL using our hybrid approach (model with rule-based fallback)
        try:
            sql = generate_sql(question)
            raw_output = f"Generated SQL using hybrid approach (model with rule-based fallback): {sql}"
            
            # Collect debug info if requested
            if debug:
                from text2sql_local import generate_sql as model_only
                from text2sql_local_rules import generate_sql as rules_only
                
                try:
                    model_sql = model_only(question)
                    raw_output += f"\n\nModel only (before enhancements): {model_sql}"
                except Exception as e:
                    raw_output += f"\n\nModel failed: {str(e)}"
                    
                # Show rule-based output for comparison
                try:
                    rule_sql = rules_only(question)
                    raw_output += f"\n\nRule-based: {rule_sql}"
                except Exception as e:
                    raw_output += f"\n\nRule-based failed: {str(e)}"
                
        except Exception as e:
            return {"error": f"Failed to generate SQL: {str(e)}", 
                    "raw_output": str(e)}
            
        # Only allow SELECT queries
        if not sql.strip().lower().startswith("select"):
            return {"error": "Only SELECT queries are allowed.", "sql": sql, "raw_output": raw_output}
        
        # Run the SQL query
        result = run_sql(sql)
        
        if result["success"]:
            return {
                "sql": sql,
                "data": result["data"],
                "columns": result["columns"],
                "raw_output": raw_output
            }
        else:
            return {"error": f"SQL execution error: {result['error']}", "sql": sql, "raw_output": raw_output}
            
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "raw_output": str(e)}

@app.get("/query")
def run_query(sql: str = Query(..., description="SELECT-only SQL query")):
    if not sql.strip().lower().startswith("select"):
        return {"error": "Only SELECT queries are allowed."}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(sql)
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return {"data": rows}

@app.get("/")
def root():
    return {"message": "SQLite Facts Assessment API is running with hybrid PICARD+T5-small and rule-based NL → SQL conversion."}

if __name__ == "__main__":
    import os
    os.system('"C:/Users/SARANLAKSHMAN/OneDrive/Desktop/desktop/sih ground/.venv/Scripts/python.exe" -m streamlit run app_streamlit.py')
