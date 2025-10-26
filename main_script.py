import pandas as pd
import subprocess
import json
import csv
import os

#we need to load the qwen model which will correctly identify the model

# Input and output files
input_csv = "trailer_urls_list.csv"
output_csv = "generated_data.csv"

# Load the trailer list
df = pd.read_csv(input_csv)

# Ensure 'status' column exists
if 'status' not in df.columns:
    df['status'] = False

# Identify pending trailers (status != True)
pending_trailers = df[df['status'] != True]['trailer_url'].tolist()

# Check if output CSV already exists
file_exists = os.path.exists(output_csv)

print(f"Total trailers to process: {len(pending_trailers)}")

# Open the output CSV in append mode
with open(output_csv, "a", newline="", encoding="utf-8") as csvfile:
    writer = None

    for url in pending_trailers:
        print(f"\n🎬 Processing trailer: {url}")
        
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
            
            # Flatten nested dictionary
            flat_row = {}
            for k, v in data.items():
                if isinstance(v, dict):
                    for subk, subv in v.items():
                        flat_row[f"{k}_{subk}"] = subv
                else:
                    flat_row[k] = v
            
            # Create writer if not yet created
            if writer is None:
                fieldnames = list(flat_row.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                file_exists = True
            
            # Write the row
            writer.writerow(flat_row)
            csvfile.flush()  # Save immediately
            
            # Mark this URL as processed
            df.loc[df['trailer_url'] == url, 'status'] = True
            df.to_csv(input_csv, index=False)
            
            # Clean up temp file
            os.remove("temp_output.json")
            print(f"✅ Data for {url} saved to {output_csv} and status updated.")
        
        else:
            print(f"⚠️ Warning: temp_output.json not found for {url}")

print(f"\n🎉 All data appended successfully to {output_csv}")
