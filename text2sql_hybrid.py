import sqlite3
import os
import re
from text2sql_local import generate_sql as model_generate_sql
from text2sql_local_rules import RuleBasedSQLGenerator, run_sql

# Configuration
DB_PATH = os.getenv('SQLITE_DB_PATH', 'local_data.db')
TABLE_NAME = "facts_assessment"

# Initialize the rule-based generator
rule_generator = RuleBasedSQLGenerator(DB_PATH)

def hybrid_generate_sql(question):
    """
    Hybrid approach that uses PICARD + T5-small model with rule-based fallback
    
    Args:
        question: Natural language question
        
    Returns:
        Generated SQL query
    """
    print(f"\n--- Processing question: {question}")
    
    # First, extract any location information to help improve SQL generation
    question_upper = question.upper()
    locations = {
        'TAMIL NADU': '"STATE - 1_level_1" = \'TAMIL NADU\'',
        'TAMILNADU': '"STATE - 1_level_1" = \'TAMIL NADU\'',
        'CHENNAI': '"DISTRICT - 2_level_1" = \'CHENNAI\'',
        'COIMBATORE': '"DISTRICT - 2_level_1" = \'COIMBATORE\'',
    }
    
    # First attempt: Use the PICARD + T5-small model
    try:
        print("Using model-based SQL generation...")
        model_sql = model_generate_sql(question)
        print(f"Model generated SQL: {model_sql}")
        
        # Apply enhancements to fix column names and other issues
        enhanced_sql = enhance_sql(model_sql, "", question)
        print(f"Enhanced model SQL: {enhanced_sql}")
        
        # Validate the enhanced SQL query
        if is_valid_sql(enhanced_sql):
            print("Enhanced model SQL validation: PASSED ✓")
            return enhanced_sql
        else:
            print("Enhanced model SQL validation: FAILED ✗, attempting additional fixes")
            
            # Try with additional fixes if validation fails
            additional_fixes = apply_additional_fixes(enhanced_sql)
            if is_valid_sql(additional_fixes):
                print("Additional fixes validation: PASSED ✓")
                return additional_fixes
            else:
                print("Additional fixes validation: FAILED ✗")
                
                # FALL BACK TO RULE-BASED if model approach fails validation
                print("Falling back to rule-based SQL generation...")
                rule_sql = rule_generator.generate_sql(question)
                print(f"Rule-based generated SQL: {rule_sql}")
                return rule_sql
            
    except Exception as e:
        print(f"Error with model-based generation: {str(e)}")
        
        # Fall back to rule-based if there's any exception with the model
        print("Falling back to rule-based SQL generation due to exception...")
        rule_sql = rule_generator.generate_sql(question)
        print(f"Rule-based generated SQL: {rule_sql}")
        return rule_sql
        
# Add a new function for additional fixes
def apply_additional_fixes(sql):
    """Apply additional fixes to SQL when initial validation fails"""
    # Fix column names again with more aggressive replacement
    sql = sql.replace("STATE", '"STATE - 1_level_1"')
    sql = sql.replace("DISTRICT", '"DISTRICT - 2_level_1"')
    
    # Fix common errors with quotes
    sql = sql.replace('""', '"')  # Double quotes
    sql = sql.replace("''", "'")  # Double single quotes
    
    # Ensure proper WHERE clause format
    if "WHERE" in sql.upper() and "=" not in sql:
        sql = sql.split("WHERE")[0] + " LIMIT 10;"
    
    # Always add LIMIT if missing
    if "LIMIT" not in sql.upper():
        if sql.endswith(";"):
            sql = sql[:-1] + " LIMIT 10;"
        else:
            sql = sql + " LIMIT 10;"
    
    return sql

def is_valid_sql(sql):
    """Check if SQL is valid by trying to run it"""
    try:
        # Simple validation
        if not sql or len(sql) < 10:
            print("SQL too short or empty")
            return False
            
        if not sql.strip().lower().startswith("select"):
            print("SQL doesn't start with SELECT")
            return False
        
        # Check for common column name issues
        required_quotes = ["STATE", "DISTRICT", "Ground Water", "Rainfall"]
        for column in required_quotes:
            # Check if column appears without quotes (as a standalone word)
            if re.search(r'(?<!\w|")' + re.escape(column) + r'(?!\w|")', sql):
                print(f"Found unquoted column name: {column}")
                return False
                
        # Check if state and district columns are properly quoted
        if "STATE - 1_level_1" in sql and '"STATE - 1_level_1"' not in sql:
            print("STATE column not properly quoted")
            return False
            
        if "DISTRICT - 2_level_1" in sql and '"DISTRICT - 2_level_1"' not in sql:
            print("DISTRICT column not properly quoted") 
            return False
            
        # More thorough validation by running the query
        conn = sqlite3.connect(DB_PATH)
        conn.execute(sql)
        conn.close()
        print("SQL validated successfully")
        return True
    except Exception as e:
        print(f"SQL validation error: {str(e)}")
        return False
        
def enhance_sql(model_sql, rule_sql, question):
    """Combine the best parts of model SQL and rule SQL"""
    # First fix common column name issues (this is critical)
    column_mappings = {
        "STATE": '"STATE - 1_level_1"',
        "DISTRICT": '"DISTRICT - 2_level_1"',
        "state": '"STATE - 1_level_1"',
        "district": '"DISTRICT - 2_level_1"',
        "State": '"STATE - 1_level_1"',
        "District": '"DISTRICT - 2_level_1"',
        "Ground Water": '"Ground Water Recharge (ham) - Total"',
        "Rainfall": '"Rainfall (mm) - Total"',
    }
    
    # Apply mappings
    for incorrect, correct in column_mappings.items():
        # Only replace if it's a standalone column name (not part of another string)
        model_sql = re.sub(r'(?<!\w)' + re.escape(incorrect) + r'(?!\w)', correct, model_sql)
    
    # If model SQL is missing proper column quoting, take it from rule-based
    if '"' not in model_sql and '"' in rule_sql:
        # Extract column names from rule-based query
        rule_columns = re.findall(r'"[^"]+"', rule_sql)
        
        # Check if the model query contains unquoted versions of these columns
        for quoted_col in rule_columns:
            unquoted_col = quoted_col.strip('"')
            if unquoted_col in model_sql:
                model_sql = model_sql.replace(unquoted_col, quoted_col)
    
    # If model SQL is missing proper table name, fix it
    if "facts_assessment" not in model_sql.lower():
        model_sql = model_sql.replace("FROM ", f"FROM {TABLE_NAME} ")
    
    # If model SQL doesn't have a LIMIT clause, add one
    if "limit" not in model_sql.lower():
        # If there's a semicolon at the end, insert before it
        if model_sql.strip().endswith(";"):
            model_sql = model_sql[:-1] + " LIMIT 10;"
        else:
            model_sql = model_sql + " LIMIT 10;"
            
    # Ensure SQL ends with semicolon
    if not model_sql.strip().endswith(";"):
        model_sql = model_sql + ";"
    
    # Fix improper use of double quotes for string literals (should be single quotes)
    model_sql = re.sub(r'=\s*"([^"]*)"', r"= '\1'", model_sql)
            
    return model_sql

def generate_sql(question):
    """Main entry point function for NL -> SQL conversion"""
    return hybrid_generate_sql(question)

# Reuse the run_sql function from the rule-based module
# It's already imported above

if __name__ == "__main__":
    # Test the hybrid approach
    questions = [
        "Show me groundwater data for Tamil Nadu",
        "What is the annual groundwater recharge in Coimbatore?",
        "Which district has the highest rainfall in Maharashtra?",
        "Show me water levels in Chennai"
    ]
    
    for q in questions:
        sql = generate_sql(q)
        print(f"\nQuestion: {q}")
        print(f"SQL: {sql}")
        
        # Test execution
        result = run_sql(sql)
        if result["success"]:
            print(f"Query executed successfully. Found {len(result['data'])} rows.")
        else:
            print(f"Query execution failed: {result['error']}")
        print("-" * 80)