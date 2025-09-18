#!/usr/bin/env python
# Test script for groundwater availability queries

from text2sql_local_rules import generate_sql, analyze_query_intent, run_sql

def test_query(question):
    """Test a query and print the results"""
    print(f"\nQuestion: {question}")
    
    # Get the query intent
    intent = analyze_query_intent(question)
    print(f"Detected Intent: {intent}")
    
    # Generate SQL
    sql = generate_sql(question)
    print(f"Generated SQL: {sql}")
    
    # Execute SQL
    try:
        result = run_sql(sql)
        if result["success"]:
            print(f"Query executed successfully. Found {len(result['data'])} results.")
            
            # Print column names 
            if result["columns"]:
                print("\nColumns returned:")
                print(", ".join(result["columns"]))
                
            # Print first row as sample
            if result["data"]:
                print("\nSample data (first row):")
                row = result["data"][0]
                for col, val in row.items():
                    if "AVAILABILITY" in col.upper() or "AVAILABLE" in col.upper() or "EXTRACTABLE" in col.upper():
                        print(f"  {col}: {val}")
        else:
            print(f"Error: {result['error']}")
    except Exception as e:
        print(f"Exception: {str(e)}")

# Test queries focused on groundwater availability
availability_queries = [
    "What is the available groundwater in Tamil Nadu?",
    "How much groundwater is available for future use in Coimbatore?",
    "Tell me about groundwater availability in Chennai",
    "What's the groundwater level in Tamil Nadu?",
    "How much usable groundwater is there in Karnataka?",
    "Show me the net annual groundwater availability",
    "What are the groundwater resources available for extraction?",
]

# Run the tests
for query in availability_queries:
    test_query(query)
    print("-" * 80)

print("\nTest completed!")