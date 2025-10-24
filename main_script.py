import pandas as pd
import subprocess
import json
import csv
import os

# Input and output files
input_csv = "trailer_urls_list.csv"
output_csv = "generated_data.csv"

# Read trailer URLs
df = pd.read_csv(input_csv)
urls = df['trailer_url'].tolist()

# Prepare CSV header
csv_columns = set()
all_rows = []

for url in urls:
    print(f"\nProcessing trailer: {url}")
    
    # Run main.py for the given trailer
    process = subprocess.Popen(
        ["python", "main.py", "--trailer", url, "--output", "temp_output.json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Print logs in real-time
    for line in process.stdout:
        print(line, end="")
    
    process.wait()
    
    # Read JSON output and flatten top-level keys
    if os.path.exists("temp_output.json"):
        with open("temp_output.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        flat_row = {}
        for k, v in data.items():
            if isinstance(v, dict):
                for subk, subv in v.items():
                    flat_row[f"{k}_{subk}"] = subv
            else:
                flat_row[k] = v
        
        all_rows.append(flat_row)
        csv_columns.update(flat_row.keys())
        
        # Delete temp file
        os.remove("temp_output.json")
    else:
        print("Warning: temp_output.json not found for", url)

# Write final CSV
csv_columns = list(csv_columns)
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"\nAll data collected in {output_csv}")
