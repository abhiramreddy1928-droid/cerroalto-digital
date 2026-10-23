import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).parent / "Employee.csv"

employee_df = pd.read_csv(CSV_PATH)

print("CSV path:", CSV_PATH)
print("Total rows:", len(employee_df))
print("Columns:", employee_df.columns.tolist())

# Display all employee records
print(employee_df.to_string())