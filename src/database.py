import os
import psycopg2
from psycopg2.extras import execute_values

# Environment variable configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'code_rag')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')

def get_connection():
  return psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS
  )

def push_to_db(df):
  conn = get_connection()
  cursor = conn.cursor()
  
  # Enable pg_trgm extension for trigram search
  cursor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

  # Create table if it doesn't exist
  cursor.execute('''
  CREATE TABLE IF NOT EXISTS components (
    id SERIAL PRIMARY KEY,
    file_path TEXT, 
    component_type TEXT,
    name TEXT,
    code TEXT,
    code_vector tsvector generated always as (to_tsvector('english', code)) stored,
    UNIQUE(file_path, component_type, name)
  )
  ''')
  
  # Create GIN index for trigram search
  cursor.execute('''
  CREATE INDEX IF NOT EXISTS idx_components_code_trigram 
  ON components USING GIN (code gin_trgm_ops)
  ''')
  
  # Insert data from DataFrame
  data = [(row['file_path'], row['component_type'], row['name'], row['code']) 
          for _, row in df.iterrows()]
  
  execute_values(cursor, '''
    INSERT INTO components (file_path, component_type, name, code) 
    VALUES %s
    ON CONFLICT(file_path, component_type, name) 
    DO UPDATE SET code = EXCLUDED.code
  ''', data)

  # Create component-specific views
  cursor.execute('''
  CREATE OR REPLACE VIEW function_indices AS
  SELECT id, file_path, name, code FROM components 
  WHERE component_type = 'function'
  ''')

  cursor.execute('''
  CREATE OR REPLACE VIEW class_indices AS
  SELECT id, file_path, name, code FROM components 
  WHERE component_type = 'class'
  ''')

  cursor.execute('''
  CREATE OR REPLACE VIEW param_indices AS
  SELECT id, file_path, name, code FROM components 
  WHERE component_type = 'params'
  ''')

  # Commit and close
  conn.commit()
  print(f"Saved {len(df)} components to PostgreSQL database")
  conn.close()

