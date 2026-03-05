import sqlite3
import pandas as pd

# connect to the correct database
conn = sqlite3.connect("backend/database.db")

query = """
SELECT activity_name,
       category,
       duration,
       date,
       mood,
       prediction
FROM activities
"""

df = pd.read_sql_query(query, conn)

df.to_csv("activities_export.csv", index=False)

conn.close()

print("Data exported successfully")