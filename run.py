from directory_scrapper import startScrap
from pkl_rebuild import recreate_seen_people_pickle

def gui():
    sentinel = True
    while sentinel == True:
        print("[1] Scrape (Windows)")
        print("[2] Scrape (Linux)")
        print("[3] Scrape Reversed (Windows)")
        print("[4] Scrape Reversed (Linux)")
        print("[5] Rebuild .pkl file from .csv")
        print("[6] Rebuild .pkl file from .csv (Reversed)")
        try:
            option = input("Enter: ")
            option = int(option)
        except:
            print("Invalid input, try again.")
            continue
        if option > 6 or option < 1:
            print("Invalid input, try again.")
        else:
            if option == 1:
                startScrap("Windows")
            elif option == 2:
                startScrap("Linux")
            elif option == 3:
                startScrap("Windows", 1)
            elif option == 4:
                startScrap("Linux", 1)
            elif option == 5:
                recreate_seen_people_pickle()
            elif option == 6:
                recreate_seen_people_pickle(1)
            sentinel = False

if __name__ == "__main__":
    gui()
    exit(1)