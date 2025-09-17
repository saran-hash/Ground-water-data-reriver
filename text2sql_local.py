from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import os

# Define model and cache paths
MODEL_NAME = "tscholak/3vnuv1vf"  # PICARD + T5-small
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Function to load model and tokenizer (will download if not cached)
def load_model_and_tokenizer():
    print(f"Loading PICARD + T5-small model from {MODEL_NAME}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
        print("Model loaded successfully!")
        return model, tokenizer
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        raise

# Initialize model and tokenizer at module level (will be loaded on first import)
try:
    print("Initializing Text2SQL model...")
    model, tokenizer = None, None  # Will be loaded on first call to generate_sql
    print("Model initialization prepared.")
except Exception as e:
    print(f"Error during initialization: {str(e)}")
    model, tokenizer = None, None

def generate_sql(question, table_info=None, max_length=256):
    """
    Generate SQL from natural language question
    
    Args:
        question: The natural language question
        table_info: Optional schema information about the database
        max_length: Maximum length of generated SQL
        
    Returns:
        Generated SQL query
    """
    global model, tokenizer
    
    # Load model and tokenizer if not already loaded
    if model is None or tokenizer is None:
        model, tokenizer = load_model_and_tokenizer()
    
    # Prepare input with explicit instruction and examples to generate a SELECT query
    examples = """
Examples:
Question: What is the water level in Coimbatore?
SQL: SELECT * FROM facts_assessment WHERE "DISTRICT - 2_level_1" = 'COIMBATORE' LIMIT 10;

Question: Show me groundwater data from Tamil Nadu
SQL: SELECT * FROM facts_assessment WHERE "STATE - 1_level_1" = 'TAMIL NADU' LIMIT 10;

Question: What is the groundwater level in Tamil Nadu?
SQL: SELECT "STATE - 1_level_1", "DISTRICT - 2_level_1", "Ground Water Recharge (ham) - Total" FROM facts_assessment WHERE "STATE - 1_level_1" = 'TAMIL NADU' LIMIT 15;

Question: Show me groundwater levels in Coimbatore Tamil Nadu
SQL: SELECT "STATE - 1_level_1", "DISTRICT - 2_level_1", "Ground Water Recharge (ham) - Total", "Annual Ground water Recharge (ham) - Total" FROM facts_assessment WHERE "DISTRICT - 2_level_1" = 'COIMBATORE' AND "STATE - 1_level_1" = 'TAMIL NADU' LIMIT 10;
    """
    
    # Create a more strict schema-aware prompt
    prompt = f"""
You are an expert SQL generator. Generate a SQL query for: "{question}"

IMPORTANT: You must use the EXACT column names as they appear in the database schema:
- The state column is "STATE - 1_level_1" (must be in double quotes)
- The district column is "DISTRICT - 2_level_1" (must be in double quotes)
- Ground water columns include "Ground Water Recharge (ham) - Total", "Annual Ground water Recharge (ham) - Total" (all in quotes)
- Rainfall columns include "Rainfall (mm) - Total" (in quotes)

{examples}

Rules:
- Always use EXACT column names with double quotes
- Start with SELECT, include FROM facts_assessment
- Always use proper quoting for column names
- Do not invent column names that don't exist in the schema
- End properly with LIMIT and semicolon
- Use uppercase for location values like 'TAMIL NADU' and 'CHENNAI'

SQL: 
"""
    
    # Use a longer max_length to ensure complete queries
    input_text = prompt
    
    # Tokenize
    inputs = tokenizer(input_text, return_tensors="pt", padding=True)
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_length=max_length,
            num_beams=5,
            early_stopping=True
        )
    
    # Decode
    sql = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Clean up the output if needed
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    return sql