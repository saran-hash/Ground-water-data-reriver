from fastapi import FastAPI, Query
import sqlite3
import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

app = FastAPI()

# Configuration
DB_PATH = os.getenv('SQLITE_DB_PATH', 'local_data.db')
TABLE_NAME = "facts_assessment"
MODEL_NAME = "mrm8488/t5-base-finetuned-wikiSQL"  # Publicly available text-to-SQL model
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Load model and tokenizer
print(f"Loading {MODEL_NAME} model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
print("Model loaded successfully!")

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (TABLE_NAME,))
    if not cursor.fetchone():
        schema_path = 'facts_assessment_schema.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    conn.close()

# Get database schema
def get_schema():
    """Read SQLite schema for groundwater database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get column information
    cursor.execute(f"PRAGMA table_info({TABLE_NAME});")
    schema_info = cursor.fetchall()
    
    # Get a few sample values to help the model understand the data
    cursor.execute(f"SELECT * FROM {TABLE_NAME} LIMIT 1;")
    sample = cursor.fetchone()
    
    # Get some state and district values as examples
    cursor.execute(f"SELECT DISTINCT STATE FROM {TABLE_NAME} LIMIT 5;")
    states = [row[0] for row in cursor.fetchall()]
    
    cursor.execute(f"SELECT DISTINCT DISTRICT FROM {TABLE_NAME} LIMIT 5;")
    districts = [row[0] for row in cursor.fetchall()]
    
    conn.close()

    # Format schema information
    columns = [col[1] for col in schema_info]  # column names
    
    # Create compact but informative schema string
    schema_str = f"Table: {TABLE_NAME}\nColumns: {', '.join(columns)}\n"
    schema_str += f"Example States: {', '.join(states)}\n"
    schema_str += f"Example Districts: {', '.join(districts)}"
    
    return schema_str

# Generate SQL from natural language
def generate_sql(question, max_length=128):
    """Generate SQL from natural language using the Spider T5 model"""
    schema = get_schema()
    
    # Create schema-aware prompt
    prompt = f"translate English to SQL given the schema:\n{schema}\nQuestion: {question}\nSQL:"
    
    # Generate SQL
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    with torch.no_grad():
        outputs = model.generate(
            **inputs, 
            max_length=max_length, 
            num_beams=5,
            early_stopping=True
        )
    
    # Decode and clean
    sql = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    return ensure_complete_sql(sql)

# Make sure SQL is complete and valid
def ensure_complete_sql(sql):
    """Fixes common issues in generated SQL"""
    sql = sql.strip()
    
    # Basic fixes
    if not sql.lower().startswith("select"):
        sql = f"SELECT * FROM {TABLE_NAME} LIMIT 10;"
    
    if "from" not in sql.lower():
        sql = sql.replace(";", "") + f" FROM {TABLE_NAME} LIMIT 10;"
    
    if TABLE_NAME.lower() not in sql.lower():
        sql = sql.lower().replace("from ", f"FROM {TABLE_NAME} ")
        
    if "limit" not in sql.lower():
        sql = sql.replace(";", "") + " LIMIT 10;"
        
    if not sql.endswith(";"):
        sql += ";"
        
    return sql

# Execute SQL safely
def execute_sql(sql):
    """Execute SQL and return results"""
    if not sql.lower().startswith("select"):
        return {"success": False, "error": "Only SELECT queries allowed"}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return {"success": True, "data": results, "columns": columns}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Initialize database on startup
init_db()

# API endpoints
@app.get("/")
def root():
    return {"message": "Groundwater NL to SQL API using Spider T5 model"}

@app.post("/nl2sql")
def nl2sql(question: str):
    """Convert natural language to SQL and execute"""
    try:
        # Generate SQL
        sql = generate_sql(question)
        
        # Execute SQL
        result = execute_sql(sql)
        
        if result["success"]:
            return {
                "sql": sql,
                "data": result["data"],
                "columns": result["columns"]
            }
        else:
            return {"error": result["error"], "sql": sql}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@app.get("/query")
def query(sql: str = Query(..., description="SQL query (SELECT only)")):
    """Execute raw SQL query"""
    result = execute_sql(sql)
    if result["success"]:
        return {"data": result["data"]}
    else:
        return {"error": result["error"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
