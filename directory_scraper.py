from math import e
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import os
import sys
from itertools import product
from string import ascii_lowercase

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "directory_results.csv")
LAST_PREFIX_FILE = os.path.join(BASE_DIR, "last_prefix.txt")
EXPECTED_FIELDS = ["Name", "Email:", "Title", "Year", "Department:", "Major", "School", "Prefix", "Location", "Phone", "Mailstop"]
SEEN_PEOPLE = set() #to track unique entries
FROZEN_PEOPLE_SEEN = os.path.abspath("seen_people.pkl")
OPERATING_SYSTEM = ""

def get_driver(max_retries = 3): #creates the web driver
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # headless mode (new flag is more stable)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")    # sometimes needed on Linux
    chrome_options.add_argument("--window-size=1920,1080")  # optional, avoids rendering issues

    for attempt in range(max_retries):
        try:
            if (OPERATING_SYSTEM == "Linux"):
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            elif (OPERATING_SYSTEM == "Windows"):
                driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error initializing WebDriver: {e}")
            if attempt < max_retries:
                print(f"Retrying ({attempt + 1}/{max_retries})...")
                time.sleep(2)
            else:
                print(f"Failed to initialize WebDriver after {max_retries} attempts. Exiting.")
                close()

def scrape_directory(search_term, driver):
    url = f"https://www.utdallas.edu/directory/"
    people = [] 
    numPeople = 0

    try:
        print(f"{search_term}: 🔍 Searching...")
        driver.get(url)
        time.sleep(.5) #wait for the main content to load
    except TimeoutException:
        print(f"{search_term}: Page load timed out.")
        return []
    except Exception as e:
        print(f"{search_term}: Error loading page: {e}")
        return []

    #input into search box and submit
    try:
        time.sleep(.5)
        search_input = driver.find_element(By.NAME, "dirSearch") #find the search input box
        search_input.clear()
        search_input.send_keys(search_term) #enter the search term
        search_input.send_keys("\n") #submit the search
    except Exception as e:
        print(f"{search_term}: Error initiating search: {e}")
        pass

    #click the all button to make the other pages visible
    try: 
        all_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.allrecs")))
        all_button.click()
        print(f"{search_term}: Clicked 'All' button to show all results.\n")
    except:
        pass #may not be an all button if its one page or less

    for page_num in range(1,11): #there are at most 10 pages of results
        try:
            print(f"{search_term}: 📄 Processing page {page_num}...")
            page_div = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, f"page{page_num}")))
        except :
            break #there are no more pages
        entries = page_div.find_elements(By.XPATH, ".//*[contains(@class,'fullname') and contains(@class,'mt-3')]/ancestor::*[1]") #finds the students, have to do ancestor so it doesnt get stuck in page 1

        for entry in entries:
            person = {} #for individual people
            numPeople += 1
            try:
                name_element = entry.find_element(By.CSS_SELECTOR, ".fullname.mt-3") #full name and title are directly under a person's div <h2 class="fullname mt-3">name</h2>
                WebDriverWait(driver, 5).until(lambda d: name_element.text.strip() != "")

                print(f"{search_term}: Found entry for {name_element.text.strip()}")
                person["Name"] = name_element.text.strip()
                try:
                    person["Title"] = entry.find_element(By.TAG_NAME, "h3").text.strip() #<h3> title </h3>
                except:
                    person["Title"] = "" #most people don't have a title
                  
                #under an individual's div there is a div called "output row" that contains rows of information
                #<p> ... <p>  each row has different information (email, department, year, major, school, phone, mailstop, location)
                rows = entry.find_elements(By.XPATH, ".//div[contains(@class,'output') and contains(@class,'row')]") #finds output rows and stores the amount of <p> ... </p> inside
                for row in rows:
                    try: 
                        labels = row.find_elements(By.TAG_NAME, "b") #<b>Type of info</b>
                        for info in labels:
                            label = info.text.lstrip().replace(": ", "") #strip template for label
                            row_text = info.find_element(By.XPATH, "..").text.strip() #strip template for info
                            if row_text.startswith(label): #if the info element starts with the label, then it has the info we want
                                value = row_text[len(label):].strip(": ").strip() #removes the label and any leading/trailing spaces
                            else:
                                value = "" #no info available
                            if label in EXPECTED_FIELDS:
                                person[label] = value
                    except StaleElementReferenceException: #sometimes the page updates while we're reading it
                        time.sleep(.1)
                        continue
                    except Exception as e:
                        print(f"Error processing row for {search_term}: {e}")
                        pass

                # Create frozenset for duplicate checking, excluding 'Prefix'
                person_frozen = frozenset({k: person.get(k, "") for k in EXPECTED_FIELDS if k != "Prefix"}.items())
                
                # Check if already seen
                if person_frozen in SEEN_PEOPLE:
                    print(f"{search_term}: Duplicate entry for {person.get('Name', '')} found. Skipping.")
                    continue
                
                # Add to seen set
                SEEN_PEOPLE.add(person_frozen)
                
                # Add Prefix for CSV output only
                person["Prefix"] = search_term
                personWithInfo = {k: person.get(k, "") for k in EXPECTED_FIELDS}  # ensures all fields are present
                people.append(personWithInfo)

            except StaleElementReferenceException:
                time.sleep(.1)
                continue
            except Exception as e:
                print(f"Error processing entry for {search_term}: {e}")
                continue

    #Save seen people to file
    with open(FROZEN_PEOPLE_SEEN, "wb") as f:
        #saves the seen people to a file so we don't lose them if the script crashes, downside of saving outside of the main loop is if the script crashes before we save we lose data, but the tradeoff is worth it for performance
        pickle.dump(SEEN_PEOPLE, f)
    #save to CSV after each person to avoid data loss
    df = pd.DataFrame(people)
    write_header = not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0 #write header if file doesn't exist or is empty
    df.to_csv(OUTPUT_FILE, mode='a', header=write_header, index=False) #append to file
    
    #unique entries counter
    unique_entries = len(df)
    print(f"{search_term}: ✅ Found {numPeople} entries, {unique_entries} saved.")
    #update running total
    global total_unique_entries
    total_unique_entries += unique_entries
    print(f"{search_term}: 🌟 Total unique entries so far: {total_unique_entries}")

    #check if we hit the max entries for this prefix
    if numPeople >= 100:
        search_saturated(search_term, driver)
    else:
        print(f"{search_term}: ✅ Completed with {len(people)} entries.")
    return people

def search_saturated(search_term, driver):
    print(f"{search_term}: ⚠️ Reached maximum entries for this prefix. Adding deeper search terms.")
    #add more letters to the search term to refine it (you have to add space letters as well in case of common last names the search will read as last_name first_name with the space allowing you to get thru all the smiths and nguyens)
    added_terms = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
    added_spaced_terms = [" a", " b", " c", " d", " e", " f", " g", " h", " i", " j", " k", " l", " m", " n", " o", " p", " q", " r", " s", " t", " u", " v", " w", " x", " y", " z"]
    for term in added_terms:
        scrape_directory(search_term + term, driver) #recursively search with added terms
    if len(search_term) > 2 and " " not in search_term: #check if spaced characters are already in the search term, if they are not present, add them
        for spaced_term in added_spaced_terms:
            scrape_directory(search_term + spaced_term, driver)
    return

def close():
    if (OPERATING_SYSTEM == "Linux"):
        print("Shutting down EC2 instance...")
        os.system("sudo shutdown -h now")
    elif (OPERATING_SYSTEM == "Windows"):
        print("Exiting script...")
        exit(1)
    else:
        print("Unknown operating system. Please shut down manually if needed.")

def startScrap(OperatingSystem, Reversed = 0):
    try:
        #set globals
        global OPERATING_SYSTEM
        OPERATING_SYSTEM = OperatingSystem
        global total_unique_entries
        total_unique_entries = 0
        #adjust globals if reversed
        if Reversed == 1:
            global OUTPUT_FILE
            OUTPUT_FILE = os.path.join(BASE_DIR, "directory_results_reversed.csv")
            global LAST_PREFIX_FILE
            LAST_PREFIX_FILE = os.path.join(BASE_DIR, "last_prefix_reversed.txt")
            global FROZEN_PEOPLE_SEEN
            FROZEN_PEOPLE_SEEN = os.path.abspath("seen_people_reversed.pkl")
        #read last prefix from file if it exists
        last_prefix = ""
        if os.path.exists(LAST_PREFIX_FILE):
            with open(LAST_PREFIX_FILE, "r") as f:
                last_prefix = f.read().strip()
                print(f"Resuming from last prefix: {last_prefix}")
        if os.path.exists(FROZEN_PEOPLE_SEEN):
            with open(FROZEN_PEOPLE_SEEN, "rb") as f:
                global SEEN_PEOPLE
                SEEN_PEOPLE = pickle.load(f)
                print(f"Loaded {len(SEEN_PEOPLE)} previously seen entries.")
        #generate prefixes from aa to zz
        prefixes = [''.join(p) for p in product(ascii_lowercase, repeat=2)]
        #reverse prefixes if needed
        if Reversed == 1:
            prefixes = prefixes[::-1]
        #start scraping from the last prefix
        start_index = prefixes.index(last_prefix) if last_prefix in prefixes else 0
        for i, p in enumerate(prefixes): #for longer last_prefix, resume from first 2 letters
            if p >= last_prefix[:2]:
                start_index = i
                break
        driver = get_driver()
        for prefix in prefixes[start_index:]:
            print(f"Starting search for prefix: {prefix}")
            scrape_directory(prefix, driver)
            #save last prefix to file
            with open(LAST_PREFIX_FILE, "w") as f:
                f.write(prefix)
            print(f"Completed search for prefix: {prefix}")
    
        print(f"Scraping completed. Total unique entries found: {total_unique_entries}")
        #remove last prefix file as we're done
        if os.path.exists(LAST_PREFIX_FILE):
            os.remove(LAST_PREFIX_FILE)
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        close()

