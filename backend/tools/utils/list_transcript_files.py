import os
import glob
import time

def list_files_by_pattern(pattern):
    files = glob.glob(pattern)
    for file_path in files:
        mtime = time.ctime(os.path.getmtime(file_path))
        print(f"{file_path} - {mtime}")
    
    if not files:
        print(f"No files found matching: {pattern}")

# List all directories
print("=== Data directories ===")
for d in os.listdir("data"):
    print(f"data/{d}")

# Check each folder for the sample transcript
transcript_id = "ff_sample_12345"
print(f"\n=== Looking for files related to {transcript_id} ===")

# Check transcript file
list_files_by_pattern(f"data/transcripts/{transcript_id}.json")

# Check chunks
list_files_by_pattern(f"data/chunks/{transcript_id}/*.json")

# Check embeddings
list_files_by_pattern(f"data/embeddings/{transcript_id}/*.json")

# Check trades
list_files_by_pattern(f"data/trades/{transcript_id}/*.json")

print("\nDone!") 