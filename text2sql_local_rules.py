import sqlite3
import os
import re

# Configuration
DB_PATH = os.getenv('SQLITE_DB_PATH', 'local_data.db')
TABLE_NAME = "facts_assessment"

class RuleBasedSQLGenerator:
    """
    Simple rule-based SQL generator for groundwater data questions.
    No model downloads needed, works right away.
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.table_name = TABLE_NAME
        self.schema = self._get_schema()
        # Map correct column names for states and districts
        self.state_column = '"STATE - 1_level_1"'
        self.district_column = '"DISTRICT - 2_level_1"'
        self.states = self._get_distinct_values(self.state_column)
        self.districts = self._get_distinct_values(self.district_column)
        
    def _get_schema(self):
        """Get table schema information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({self.table_name});")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        return columns
        
    def _get_distinct_values(self, column_name):
        """Get distinct values for a column"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT DISTINCT {column_name} FROM {self.table_name} LIMIT 20;")
            values = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()
            return values
        except Exception as e:
            conn.close()
            print(f"Error getting distinct values for {column_name}: {str(e)}")
            return []
        
    def generate_sql(self, question):
        """Generate SQL based on the question using rules"""
        original_question = question
        question = question.upper()
        
        # Default query if we can't match anything specific
        default_query = f'SELECT * FROM {self.table_name} LIMIT 10;'
        
        # Detect if this is an availability-related question
        availability_keywords = ["AVAILABLE", "AVAILABILITY", "REMAINING", "LEFT", "USABLE", "UNUSED", "FUTURE USE"]
        is_availability_question = any(keyword in question for keyword in availability_keywords)
        
        # Check for state mentions
        state_match = None
        for state in self.states:
            if state and state.upper() in question:
                state_match = state
                break
                
        # Check for district mentions
        district_match = None
        for district in self.districts:
            if district and district.upper() in question:
                district_match = district
                break
                
        # Look for groundwater-related columns
        groundwater_columns = [
            f'"{col}"' for col in self.schema 
            if "GROUND WATER" in col.upper() or "GROUNDWATER" in col.upper()
        ]
        
        # Look for rainfall-related columns
        rainfall_columns = [
            f'"{col}"' for col in self.schema
            if "RAINFALL" in col.upper()
        ]
        
        # Use the query intent analyzer to determine the type of groundwater data needed
        query_intent = analyze_query_intent(question)
        
        # Check for pattern matches
        if "RAINFALL" in question:
            selected_columns = rainfall_columns
        elif query_intent == "availability" or is_availability_question:
            # Specifically look for availability-related columns
            availability_columns = [
                f'"{col}"' for col in self.schema 
                if "AVAILABILITY" in col.upper() or "AVAILABLE" in col.upper() or "NET ANNUAL" in col.upper() 
                or "FUTURE USE" in col.upper() or "EXTRACTABLE" in col.upper()
            ]
            
            # Add identifying columns and limit to avoid overwhelming results
            selected_columns = [
                '"STATE - 1_level_1"',
                '"DISTRICT - 2_level_1"',
                '"Net Annual Ground Water Availability for Future Use (ham) - Total"',
                '"Annual Extractable Ground water Resource (ham) - Total"'
            ]
        elif "WATER LEVEL" in question or "GROUND WATER" in question or "GROUNDWATER" in question:
            # Select groundwater columns based on the specific intent
            if query_intent == "recharge":
                recharge_columns = [
                    f'"{col}"' for col in self.schema 
                    if "RECHARGE" in col.upper() and "TOTAL" in col.upper()
                ]
                selected_columns = [
                    '"STATE - 1_level_1"',
                    '"DISTRICT - 2_level_1"',
                    '"Annual Ground water Recharge (ham) - Total"'
                ]
            elif query_intent == "extraction":
                extraction_columns = [
                    f'"{col}"' for col in self.schema 
                    if "EXTRACTION" in col.upper() and "TOTAL" in col.upper()
                ]
                selected_columns = [
                    '"STATE - 1_level_1"',
                    '"DISTRICT - 2_level_1"',
                    '"Ground Water Extraction for all uses (ha.m) - Total"',
                    '"Stage of Ground Water Extraction (%) - Total"'
                ]
            else:
                # Default to some basic groundwater columns
                if len(groundwater_columns) > 4:
                    # Limit to a few columns to avoid overwhelming results
                    selected_columns = groundwater_columns[:4]
                else:
                    selected_columns = groundwater_columns
        else:
            # For generic queries, pick some representative columns
            selected_columns = [
                '"STATE - 1_level_1"',
                '"DISTRICT - 2_level_1"',
                '"Rainfall (mm) - Total"',
                '"Annual Ground water Recharge (ham) - Total"',
                '"Stage of Ground Water Extraction (%) - Total"'
            ]
            
        # Add basic identifying columns if not already included
        state_district_included = False
        for col in selected_columns:
            if "STATE" in col.upper() or "DISTRICT" in col.upper():
                state_district_included = True
                break
                
        if not state_district_included:
            select_clause = f'SELECT {self.state_column}, {self.district_column}, {", ".join([f"{col}" for col in selected_columns])}'
        else:
            select_clause = f'SELECT {", ".join([f"{col}" for col in selected_columns])}'
            
        # Build WHERE clause based on location
        where_conditions = []
        if state_match:
            where_conditions.append(f'{self.state_column} = \'{state_match}\'')
        if district_match:
            where_conditions.append(f'{self.district_column} = \'{district_match}\'')
            
        # Construct final query
        if where_conditions:
            query = f"{select_clause} FROM {self.table_name} WHERE {' AND '.join(where_conditions)} LIMIT 10;"
        else:
            query = f"{select_clause} FROM {self.table_name} LIMIT 10;"
            
        return query

# Initialize the generator
sql_generator = RuleBasedSQLGenerator(DB_PATH)

def generate_sql(question):
    """Generate SQL from natural language question"""
    return sql_generator.generate_sql(question)

def ensure_complete_sql(sql):
    """Make sure SQL is valid (already valid in our case)"""
    return sql

def run_sql(sql):
    """Run SQL and return results"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return {"success": True, "data": rows, "columns": columns}
    except Exception as e:
        return {"success": False, "error": str(e)}
        
# Add specialized analysis for complex queries
def analyze_query_intent(question):
    """Analyze the query intent to better handle ambiguous terms"""
    question = question.upper()
    
    # Create mapping of concepts to columns
    intent_mappings = {
        "availability": ["NET ANNUAL", "AVAILABILITY", "AVAILABLE", "EXTRACTABLE", "FUTURE USE"],
        "recharge": ["RECHARGE", "REPLENISHMENT", "INFLOW"],
        "extraction": ["EXTRACTION", "USAGE", "CONSUMPTION", "UTILISATION", "UTILIZATION"],
        "levels": ["LEVEL", "DEPTH", "HEIGHT"]
    }
    
    # Check for direct intent signals
    for intent, keywords in intent_mappings.items():
        for keyword in keywords:
            if keyword in question:
                return intent
                
    # Handle ambiguous cases with water "level" or "amount" which could mean availability
    ambiguous_terms = ["WATER LEVEL", "LEVEL OF WATER", "AMOUNT OF WATER", "HOW MUCH WATER"]
    availability_context = ["AVAILABLE", "REMAINING", "LEFT", "USABLE", "FUTURE", "UNUSED"]
    
    has_ambiguous = any(term in question for term in ambiguous_terms)
    has_availability_context = any(context in question for context in availability_context)
    
    if has_ambiguous and has_availability_context:
        return "availability"
        
    # Special handling for common patterns
    if "HOW MUCH" in question and "WATER" in question:
        return "availability"
        
    # Default intent for groundwater questions
    return "recharge"

# Example usage
if __name__ == "__main__":
    questions = [
        "Show me groundwater levels in Coimbatore Tamil Nadu",
        "What is the available groundwater in Tamil Nadu?",
        "How much groundwater is available for future use in Coimbatore?",
        "Tell me about groundwater availability in Chennai",
        "What's the water level in Coimbatore?",
        "How much usable groundwater is there in Karnataka?"
    ]
    
    for question in questions:
        intent = analyze_query_intent(question)
        sql = generate_sql(question)
        print(f"Question: {question}")
        print(f"Detected Intent: {intent}")
        print(f"Generated SQL: {sql}")
        
        # Execute the query
        result = run_sql(sql)
        if result["success"]:
            print(f"Found {len(result['data'])} rows")
            # Print first row for verification
            if result["data"]:
                print("First row:")
                for col, val in list(result["data"][0].items())[:5]:  # Show first 5 columns
                    print(f"  {col}: {val}")
        else:
            print(f"Error: {result['error']}")
        print("-" * 80)