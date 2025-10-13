import pandas as pd
import pickle
import os
import sys

# --- Configuration (Must match your original script) ---
# Assuming the CSV is in the same directory, or you can adjust this path.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "directory_results.csv")
# The path where the reconstructed pickle file will be saved.
FROZEN_PEOPLE_SEEN = os.path.abspath("seen_people.pkl")

# Fields used for the unique identifier (all EXPECTED_FIELDS *except* 'Prefix')
UNIQUE_FIELDS = [
    "Name", "Email:", "Title", "Year", "Department:", "Major", 
    "School", "Location", "Phone", "Mailstop"
]

def recreate_seen_people_pickle(Reversed = 0):
    if Reversed == 1: #if reversed edit globals
        global OUTPUT_FILE
        OUTPUT_FILE = os.path.join(BASE_DIR, "directory_results_reversed.csv")
        global FROZEN_PEOPLE_SEEN
        FROZEN_PEOPLE_SEEN = os.path.abspath("seen_people_reversed.pkl")

    """
    Reads the existing CSV file, extracts the unique identifier for each entry,
    and recreates the SEEN_PEOPLE set in the 'seen_people.pkl' file.
    
    CRITICAL FIX: When pandas reads an empty cell, it often uses NaN (a float), 
    but the original scraping script uses an empty string ("") for missing fields 
    in the frozenset. We must replace all NaN values with "" to ensure the 
    reconstructed frozensets match the originals, preventing duplicates.
    """
    if not os.path.exists(OUTPUT_FILE):
        print(f"Error: CSV file not found at '{OUTPUT_FILE}'")
        print("Please ensure the CSV is present and the file path is correct.")
        sys.exit(1)

    print(f"1. Reading data from '{OUTPUT_FILE}'...")
    
    try:
        # Load the CSV. We explicitly read the columns we care about.
        df = pd.read_csv(OUTPUT_FILE, usecols=lambda col: col in UNIQUE_FIELDS + ["Prefix"])
    except ValueError as e:
        print(f"Error reading CSV columns: {e}")
        print("Please check if your CSV contains all the expected fields.")
        sys.exit(1)
        
    print(f"   Successfully loaded {len(df)} rows.")

    # --- FIX: Convert NaN to empty string for matching ---
    # NaN values (which pandas uses for empty cells) must be converted to 
    # the empty string "" to correctly match the frozenset format used by the scraper.
    df.fillna('', inplace=True) 

    # We also ensure all relevant fields are explicitly converted to string 
    # and stripped, matching the string processing that happens during scraping 
    # before the frozenset is created.
    for field in UNIQUE_FIELDS:
        # We use .astype(str) to handle cases where a column might have been inferred as numeric
        # and then apply strip() to clean up whitespace.
        df[field] = df[field].astype(str).str.strip()

    # Initialize the set that will hold the unique person identifiers
    seen_people_set = set()
    
    print("2. Processing rows and generating unique identifiers...")
    
    # Iterate over the DataFrame rows
    for index, row in df.iterrows():
        # Create a dictionary for the current person using only the UNIQUE_FIELDS
        # Since we've pre-cleaned the DataFrame (fillna and str.strip), 
        # the values here should correctly reflect the scraped data structure (empty string for missing).
        person_data = {field: row[field] for field in UNIQUE_FIELDS}
        
        # Convert the dictionary's items to a frozenset, which is what your
        # original scraping script stores in SEEN_PEOPLE.
        person_frozen = frozenset(person_data.items())
        
        # Add the unique identifier to the set
        seen_people_set.add(person_frozen)
        
    print(f"   Reconstructed set contains {len(seen_people_set)} unique entries.")

    # Save the reconstructed set to the pickle file
    print(f"3. Saving reconstructed set to '{FROZEN_PEOPLE_SEEN}'...")
    with open(FROZEN_PEOPLE_SEEN, "wb") as f:
        pickle.dump(seen_people_set, f)
        
    print("✅ Success! The 'seen_people.pkl' file has been recreated.")
    print("You can now run your main scraping script to resume searching.")