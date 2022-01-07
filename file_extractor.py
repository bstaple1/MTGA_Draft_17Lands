import getopt
import sys
import os
import time
import re
import json
import urllib.request
import datetime
from datetime import date
from urllib.parse import quote as urlencode
#TYPE_CARD_RATING  = "0"
#TYPE_COLOR_RATING = "1"
#TYPE_TROPHY_DECKS = "2"

#https://www.17lands.com/card_ratings/data?expansion=MID&format=PremierDraft&colors=W&start_date=2021-01-01&end_date=2021-09-27&colors=WUB

#output_suffix_type_dict = {
#    TYPE_CARD_RATING  : "_Card_Rating.json",
#    TYPE_COLOR_RATING : "_Color_Rating.json",
#    TYPE_TROPHY_DECKS : "_Trophy.json",
#}
def ExtractTypes(type_line):
    types = []
    if "Creature" in type_line:
        types.append("Creature")
        
    if "Planeswalker" in type_line:
        types.append("Planeswalker")
        
    if "Land" in type_line:
        types.append("Land")
        
    if "Instant" in type_line:
        types.append("Instant")
        
    if "Sorcery" in type_line:
        types.append("Sorcery")
       
    if "Enchantment" in type_line:
        types.append("Enchantment")
        
    if "Artifact" in type_line:
        types.append("Artifact")

    return types
       
class DataPlatform:
    def __init__(self, version):
        self.set = ""
        self.draft = ""
        self.session = ""
        self.start_date = ""
        self.end_date = ""
        self.id = id
        self.card_ratings = {}
        self.combined_data = {}
        self.card_list = []
        #self.driver_path = os.getcwd() + '\geckodriver.exe'
        #self.driver = webdriver.Firefox(executable_path = self.driver_path)
        self.combined_data["meta"] = {"collection_date" : str(datetime.datetime.now())}
        self.combined_data["meta"]["version"] = version
        self.deck_colors = ["All Decks", "W","U","B","R","G","WU","WB","WR","WG","UB","UR","UG","BR","BG","RG","WUB","WUR","WUG","WBR","WBG","WRG","UBR","UBG","URG","BRG"]
        
    #def __del__(self):
    #    self.driver.quit() # clean up driver when we are cleaned up
    def Set(self, set):
        self.set = set.upper()
        
    def DraftType(self, draft_type):
        self.draft = draft_type
        
    def StartDate(self, start_date):
        self.start_date = start_date
        self.combined_data["meta"]["start_date"] = self.start_date
        
    def EndDate(self, end_date):
        self.end_date = end_date
        self.combined_data["meta"]["end_date"] = self.end_date
        
    def ID(self, id):
        self.id = id

    def SessionCardData(self):
        try:
            arena_id = int(self.id)
            #https://api.scryfall.com/cards/search?order=set&q=e%3AKHM
            url = "https://api.scryfall.com/cards/search?order=set&q=e" + urlencode(':', safe='') + "%s" % (self.set)
            print(url)
            url_data = urllib.request.urlopen(url).read()
            
            set_json_data = json.loads(url_data)
            #print(set_json_data)
            arena_id = self.ProcessCardData(set_json_data["data"], arena_id)
            
            while set_json_data["has_more"] == True:
                url = set_json_data["next_page"]
                url_data = urllib.request.urlopen(url).read()
                set_json_data = json.loads(url_data)
                arena_id = self.ProcessCardData(set_json_data["data"], arena_id)
                
            print(len(self.card_list))
                
        except Exception as error:
            print("SessionCardData Error: %s" % error)
        
    def SessionCardRating(self, root, progress, initial_progress):
        current_progress = 0
        result = False
        for color in self.deck_colors:
            retry = 5
            result = False
            while retry:
                
                try:
                    url = "https://www.17lands.com/card_ratings/data?expansion=%s&format=%s&start_date=%s&end_date=%s" % (self.set, self.draft, self.start_date, self.end_date)
                    
                    if color != "All Decks":
                        url += "&colors=" + color
                        
                    print(url)
                    url_data = urllib.request.urlopen(url).read()
                    
                    set_json_data = json.loads(url_data)
                
                    if self.RetrieveCardRatingsUrl(color, set_json_data):
                        result = True
                        break
                    else:
                        retry -= 1
                    
                    time.sleep(5)
                
                except Exception as error:
                    print("SessionCardRating Error: %s" % error)
                    time.sleep(15)
                    
            if result:
                current_progress += 3
                progress['value'] = current_progress + initial_progress
                root.update()
            else:
                break
            time.sleep(2)
            
        self.combined_data["card_ratings"] = {}
        print("List Length %d" % len(self.card_list))
        for card in self.card_list:
            self.ProcessCardRatings(card)
            
        return result 
        
    def SessionSets(self):
        sets = {}
        try:
            url = "https://api.scryfall.com/sets"
            url_data = urllib.request.urlopen(url).read()
            
            set_json_data = json.loads(url_data)
            sets = self.ProcessSetData(sets, set_json_data["data"])
            while set_json_data["has_more"] == True:
                url = set_json_data["next_page"]
                url_data = urllib.request.urlopen(url).read()
                set_json_data = json.loads(url_data)
                sets = self.ProcessSetData(sets, set_json_data["data"])
                
                
        except Exception as error:
            print("SessionCardData Error: %s" % error)
        return sets   
    def SessionColorRatings(self):
        try:
            import selenium
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select
        
            url = "https://www.17lands.com/color_ratings"
            driver_path = os.getcwd() + '\geckodriver.exe'
            driver = webdriver.Firefox(executable_path = driver_path)
            driver.get(url)
            checkbox_attribute = driver.find_element_by_xpath("//*[@class='ui checked checkbox card-performance-checkbox']")
            checkbox_attribute.click()
            
            #Set the draft set
            element = WebDriverWait(driver, 900).until(
                EC.presence_of_element_located((By.ID, "expansion"))
            )
            
            if len(self.set):
                Select(element).select_by_value(self.set)
                print("Set: %s" % self.set)
            
            #Set the start date
            #start_date_attribute = self.driver.find_element_by_id("start_date_1")
            #if len(start_date):
            #    start_date_attribute.clear()
            #    start_date_attribute.send_keys(start_date)
            #
            #print("Start Date: %s" % start_date_attribute.get_attribute("value"))
            #
            ##Set the end date
            #end_date_attribute = self.driver.find_element_by_id("end_date_1")
            #if len(end_date):
            #    end_date_attribute.clear()
            #    end_date_attribute.send_keys(end_date)
            #    
            #print("End Date: %s" % end_date_attribute.get_attribute("value")) 
                
            #self.combined_data["meta"]["date_range"] = "%s -> %s" % (start_date_attribute.get_attribute("value"), end_date_attribute.get_attribute("value"))   
                
            time.sleep(5)
            
            self.RetrieveColorRatings(driver)
                
        except Exception as error:
            print(error)        
            
    def RetrieveCardRatingsUrl(self, colors, cards):  
        result = True
        for card in cards:
            try:
                print("Name: %s" % card["name"])
                print("Color: %s" % colors)
                print("GIHWR: %s" % card["ever_drawn_win_rate"])
                print("EDWC: %s" % card["ever_drawn_game_count"])
                print("ALSA: %s" % card["avg_seen"])
                print("IWD: %s" % card["drawn_improvement_win_rate"])
                card_name = card["name"]
                gihwr = card["ever_drawn_win_rate"]
                iwd = card["drawn_improvement_win_rate"]
                alsa = card["avg_seen"]
                drawn_count = card["ever_drawn_game_count"]
                
                gihwr = gihwr if gihwr != None else "0.0"
                
                gihwr = float(gihwr) * 100 if int(card["ever_drawn_game_count"]) > 200 else 0.0
                gihwr = round(gihwr, 2)
                iwd = round(float(card["drawn_improvement_win_rate"]) * 100, 2)
                alsa = round(float(card["avg_seen"]), 2)
                try:
                    self.card_ratings[card_name].append({colors : {"gihwr" : gihwr, "iwd" : iwd, "alsa" : alsa}})
                except Exception as error:
                    self.card_ratings[card_name] = []
                    self.card_ratings[card_name].append({colors : {"gihwr" : gihwr, "iwd" : iwd, "alsa" : alsa}}) 
                self.card_ratings[card_name]
            except Exception as error:
                print("RetrieveCardRatingsUrl Error: %s" % error)
                result = False
                
        #Add in basic lands
        lands = ["Mountain","Swamp","Plains","Forest","Island"]
        for land in lands:
            self.card_ratings[land] = []
            self.card_ratings[land].append({colors : {"gihwr" : 0, "iwd" : 0, "alsa" : 0}})
        return result
        
    def RetrieveColorRatings(self, driver):
        color_ratings_dict = {
            "Mono-White"     : "W",
            "Mono-Blue"      : "U",
            "Mono-Black"     : "B",
            "Mono-Red"       : "R",
            "Mono-Green"     : "G",
            "(WU)"           : "WU",
            "(UB)"           : "UB",
            "(BR)"           : "BR",
            "(RG)"           : "RG",
            "(GW)"           : "GW",
            "(WB)"           : "WB",
            "(BG)"           : "BG",
            "(GU)"           : "GU",
            "(UR)"           : "UR",
            "(RW)"           : "RW",
            "(WUR)"          : "WUR",
            "(UBG)"          : "UBG",
            "(BRW)"          : "BRW",
            "(RGU)"          : "RGU",
            "(GWB)"          : "GWB",
            "(WUB)"          : "WUB",
            "(UBR)"          : "UBR",
            "(BRG)"          : "BRG",
            "(RGW)"          : "RGW",
            "(GWU)"          : "GWU",
        }
        
        try:
            import selenium
            from selenium import webdriver
            from selenium.webdriver.common.by import By
        
            table_class = driver.find_element_by_xpath("//*[@class='ui celled inverted selectable unstackable compact table color-performance']")
            print(table_class)
            tbody = table_class.find_element_by_tag_name('tbody')
            table_rows = tbody.find_elements(By.TAG_NAME, "tr")
            
            print("table_rows: %u" % len(table_rows))
            
            self.combined_data["color_ratings"] = {}

            for row in table_rows:
                if row.get_attribute("class") == "color-individual":
                    table_columns = row.find_elements(By.TAG_NAME, "td")
                    #print("table_columns: %u" % len(table_columns))
                    colors = table_columns[0].text
                    print("colors: %s" % colors)
                    print(table_columns[3].text)
                    winrate = re.sub("[^0-9^.]", "", table_columns[3].text)
                    print("winrate: %s" % str(winrate))
                    games = int(table_columns[2].text)
                    
                    color_label = [x for x in color_ratings_dict.keys() if x in colors]
                    if len(color_label) and games > 5000:   
                        processed_colors = color_ratings_dict[color_label[0]]
                        
                        if processed_colors not in self.combined_data["color_ratings"].keys():
                            self.combined_data["color_ratings"][processed_colors] = winrate
            
            driver.quit()
                            #print("Colors: %s, winrate: %f" % (processed_colors, winrate))
            #print(self.card_ratings)    
            
            
            
        except Exception as error:
            print("RetrieveColorRatings Error: %s" % error)
            driver.quit()
          
    def ProcessCardData (self, data, arena_id):

        for card_data in data:
            try:
                card = {}
        
                card["cmc"] = card_data["cmc"]
                card["name"] = card_data["name"]
                card["color_identity"] = card_data["color_identity"]
                card["types"] = ExtractTypes(card_data["type_line"])
                card["image"] = []
                
                if arena_id == 0:
                    card["arena_id"] = card_data["arena_id"]
                elif "card_faces" in card_data.keys():
                    card["arena_id"] = arena_id
                    arena_id += 2
                else:
                    card["arena_id"] = arena_id
                    arena_id += 1
                try:
                    if "card_faces" in card_data.keys():
                        card["mana_cost"] = card_data["card_faces"][0]["mana_cost"]
                        card["image"].append(card_data["card_faces"][0]["image_uris"]["normal"])
                        card["image"].append(card_data["card_faces"][1]["image_uris"]["normal"])
                        
                    else:
                        card["mana_cost"] = card_data["mana_cost"]
                        card["image"] = [card_data["image_uris"]["normal"]]
                except Exception as error:
                    print(error)
                    card["mana_cost"] = "0"
                    card["image"] = []
                print("%s, %s" % (card["name"], card["mana_cost"]))
                self.card_list.append(card)
                
                
            except Exception as error:
                print("ProcessCardData Error: %s" % error)
        #print("combined_data: %s" % str(combined_data))
        return arena_id

        
    def ProcessCardRatings (self, card):
        try:
            card_id = card["arena_id"]
            image = card["image"] 
            card_name = card["name"]
            card_colors = card["color_identity"]
            converted_mana_cost = card["cmc"]
            card_types = card["types"]
            mana_cost = card["mana_cost"]
            #Add logic for retrieving dual faced card info from the ratings  file
            card_sides = card_name.split(" // ") 
            matching_cards = [x for x in self.card_ratings.keys() if x in card_sides]
            print("Card Sides: %s" % str(card_sides))
            #print("Ratings Keys: %s" % str(self.card_ratings.keys()))
            if(matching_cards):
                ratings_card_name = matching_cards[0]
                deck_colors = self.card_ratings[ratings_card_name]
                if card_id not in self.combined_data["card_ratings"].keys():
                    self.combined_data["card_ratings"][card_id] = {}
                    self.combined_data["card_ratings"][card_id]["name"] = card_name
                
                self.combined_data["card_ratings"][card_id]["colors"] = card_colors
                self.combined_data["card_ratings"][card_id]["cmc"] = converted_mana_cost
                self.combined_data["card_ratings"][card_id]["types"] = card_types
                self.combined_data["card_ratings"][card_id]["mana_cost"] = mana_cost
                self.combined_data["card_ratings"][card_id]["image"] = image
                self.combined_data["card_ratings"][card_id]["deck_colors"] = {}
                
                for deck_color in deck_colors:
                    for key, value in deck_color.items():
                        self.combined_data["card_ratings"][card_id]["deck_colors"][key] = {"gihwr" :  value["gihwr"], 
                                                                                           "alsa" : value["alsa"],
                                                                                           "iwd" : value["iwd"]}
            else:
                print("No match for %s" % card['name']) 
            
        except Exception as error:
            print(error)
            print("skipping %s" % card['name'])
            
        #print("combined_data: %s" % str(combined_data))
        return
        
    def ProcessSetData (self, sets, data):
        counter = 0
        for set in data:
            try:
                set_name = set["name"]
                set_code = set["code"]
                
                if (len(set_code) == 3) and (set["set_type"] == "expansion"):
                    sets[set_name] = set_code
                    counter += 1
                    
                    # Only retrieve the last 10 sets
                    if counter >= 10:
                        break
            except Exception as error:
                print("ProcessSetData Error: %s" % error)
        
        return sets
    def ExportData(self):
        print(self.set)
        try:
            output_file = self.set + "_" + self.draft + "_Data.json"

            with open(output_file, 'w') as f:
                json.dump(self.combined_data, f)
        except Exception as error:
            print("ExportData Error: %s" % error)