# Groundwater Data Natural Language to SQL System

> **Development Branch**: This is the `dev` branch with the latest features and improvements.

An end-to-end system that enables natural language queries on groundwater data, converts them to SQL, and returns results in a user-friendly interface.

## Features

- **Natural Language to SQL Conversion**: Ask questions in plain English about groundwater data
- **Hybrid Approach**: Combines machine learning models with rule-based validation for robust SQL generation
- **Chat-Style Interface**: User-friendly Streamlit frontend with results display
- **Local Operation**: Everything runs locally, no external API dependencies
- **SELECT-Only Queries**: Security built-in with read-only database access

## Architecture

- **Backend**: FastAPI server (main.py) that handles NL to SQL conversion and database queries
- **Frontend**: Streamlit application (app_streamlit.py) providing chat interface
- **Database**: SQLite database with groundwater facts and assessment data
- **NL to SQL Engine**: Hybrid system using PICARD + T5-small model with rule-based fallback

## Components

1. **text2sql_local.py**: Implements the PICARD + T5-small model for NL to SQL conversion
2. **text2sql_local_rules.py**: Rule-based SQL generator for fallback and validation
3. **text2sql_hybrid.py**: Combines both approaches for robust SQL generation
4. **main.py**: FastAPI backend with endpoints for NL to SQL conversion and direct SQL queries
5. **app_streamlit.py**: Streamlit frontend with chat interface and results display

## Installation

1. Create a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```
   python init_db.py
   ```
   
   Note: This step requires the `cleaned_groundwater_data_final.csv` file to be present in your project directory.

4. Run the application:
   ```
   python main.py
   ```
   
   Or start components separately:
   ```
   uvicorn main:app --reload
   streamlit run app_streamlit.py
   ```

## Usage

1. Start the application
2. Navigate to http://localhost:8502 in your browser
3. Ask questions about groundwater data in plain English
4. View the generated SQL and results

## Example Queries

- "Show me groundwater levels in Tamil Nadu"
- "What is the annual groundwater recharge in Coimbatore?"
- "Which district has the highest rainfall in Maharashtra?"
- "Show me water levels in Chennai"

## Technologies Used

- FastAPI for backend API
- Streamlit for frontend UI
- SQLite for local database
- PICARD + T5-small for NL to SQL model
- Python for implementation