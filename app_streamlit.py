import streamlit as st
import requests
import pandas as pd

BACKEND_URL = "http://localhost:8000"

st.title("Groundwater Data NL → SQL Chat")
st.subheader("Using hybrid PICARD+T5-small and rule-based NL → SQL conversion")

question = st.text_input("Ask a question about groundwater data:")
debug_mode = st.checkbox("Show debugging info (model vs rule-based)")

if st.button("Submit") and question:
    with st.spinner("Generating SQL and fetching results..."):
        try:
            # Initialize resp variable before using it
            resp = None
            # Make the API request
            resp = requests.post(f"{BACKEND_URL}/nl2sql", params={
                "question": question,
                "debug": debug_mode
            })
            result = resp.json()
        except Exception as e:
            # Safe access to resp.text if resp is defined
            raw_response = getattr(resp, 'text', 'No response') if resp else 'No response'
            st.error(f"Error connecting to backend: {e}\nRaw response: {raw_response}")
            result = {}
        
        # Extract results
        sql = result.get("sql", "")
        data = result.get("data", [])
        error = result.get("error", None)
        raw_output = result.get("raw_output", "")
        
        # Display SQL query
        st.markdown("### Generated SQL Query:")
        st.code(sql, language="sql")
        
        # Display results or errors
        if error:
            st.error(f"Error: {error}")
        elif data:
            st.markdown("### Query Results:")
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            # Add download buttons
            st.download_button(
                label="Download as CSV",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='query_results.csv',
                mime='text/csv',
            )
        else:
            st.info("No results returned.")
            
        # Model output (for debugging)
        with st.expander("Model Debug Output"):
            st.markdown(f"**Raw Model Output:**\n```\n{raw_output}\n```")
