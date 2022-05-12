import getopt
import sys
import os
import time
import re
import json
import urllib.request
import datetime
import ssl
from enum import Enum
import log_scanner as LS
from datetime import date
from urllib.parse import quote as urlencode

#https://www.17lands.com/card_ratings/data?expansion=MID&format=PremierDraft&colors=W&start_date=2021-01-01&end_date=2021-09-27&colors=WUB

LOCAL_DATA_FOLDER_PATH_PC = "/Wizards of the Coast/MTGA/MTGA_Data/Downloads/Data/"
LOCAL_DATA_FOLDER_PATH_MAC = "/Library/Application Support/com.wizards.mtga/Downloads/Data/"

LOCAL_DATA_DIRECTORY_PREFIX_PC = "Program Files"
LOCAL_DATA_DIRECTORY_PREFIX_MAC = "Users/"

LOCAL_DATA_FILE_PREFIX_CARDS = "Data_cards_"
LOCAL_DATA_FILE_PREFIX_TEXT = "Data_loc_"

local_data_folder_path_dict = {
    "PC" : LOCAL_DATA_FOLDER_PATH_PC,
    "MAC" : LOCAL_DATA_FOLDER_PATH_MAC,
}

class Result(Enum):
    VALID = 0
    ERROR_MISSING_FILE = 1
    ERROR_UNREADABLE_FILE = 2
    
def RetrieveLocalArenaData(operating_system, card_data, card_set):
    result_string = "Arena IDs Unavailable"
    result = False
    
    while(1):
        try:       
            #Identify the locations of local arena files
            arena_cards_location = LocalFileLocation(operating_system, LOCAL_DATA_FILE_PREFIX_CARDS)
            
            if len(arena_cards_location) == 0:
                break
            
            arena_text_location = LocalFileLocation(operating_system, LOCAL_DATA_FILE_PREFIX_TEXT)
            
            if len(arena_text_location) == 0:
                break
                
            #Retrieve the arena IDs without card names
            result, arena_data = RetrieveLocalArenaId(arena_cards_location, card_set)
            
            if result == False:
                break
                
            #Retrieve the card names for each arena ID
            result = RetrieveLocalCardName(arena_text_location, arena_data, card_data)
            
        except Exception as error:
            print("RetrieveLocalArenaData Error: %s" % error)
        break
    return result, result_string
 
def LocalFileLocation(operating_system, file_prefix):
    file_location = ""
    try:
        computer_root = os.path.abspath(os.sep)
        
        for root, dirs, files in os.walk(computer_root):
            path = root
            try:
                if operating_system == "MAC":
                    path += LOCAL_DATA_DIRECTORY_PREFIX_MAC
                    folders = os.listdir(path)
                else:
                    folders = [folder_name for folder_name in os.listdir(path) if folder_name.startswith(LOCAL_DATA_DIRECTORY_PREFIX_PC)]
                folder_path = local_data_folder_path_dict[operating_system]
                for folder in folders:
                    file_path = path + folder + folder_path
                    
                    try:
                        if os.path.exists(file_path):
                            file = [filename for filename in os.listdir(file_path) if filename.startswith(file_prefix)][0]
                            
                            file_location = file_path + file
                            return file_location

                    except Exception as error:
                        print(error)
                        
            except Exception as error:
                print(error)
                    
    except Exception as error:
        print(error)
                    
    return file_location
    
def RetrieveLocalArenaId(file_location, card_set):
    arena_data = {}
    result = False
    try:
        with open(file_location, 'r', encoding="utf8") as json_file:
            json_data = json.loads(json_file.read())
            
            for card in json_data:
                if card["set"] == card_set:
                    if "isSecondaryCard" not in card: #Skip alternate art cards
                        group_id = card["grpid"]
                        title_id = card["titleId"]
                        
                        arena_data[title_id] = group_id
                        result = True
    
    except Exception as error:
        print("RetrieveLocalArenaId Error: %s" % error)
        
    return result, arena_data
    
def RetrieveLocalCardName(file_location, arena_data, scryfall_data):
    result = True
    processed_data = {}
    try:
        #Retrieve the title (card name) for each of the collected arena IDs
        with open(file_location, 'r', encoding="utf8") as json_file:
            json_data = json.loads(json_file.read())
            
            for group in json_data:
                if group["isoCode"] == "en-US":
                    keys = group["keys"]
                    
                    for key in keys:
                        try:
                            if key["id"] in arena_data:
                                if "raw" in key:
                                    processed_data[key["raw"]] = arena_data[key["id"]]
                                else:
                                    processed_data[key["text"]] = arena_data[key["id"]]
                        except Exception as error:
                            print(error)
                       
       
        #Add the arena IDs to the scryfall data set
        for card in scryfall_data:
            card_name = card["name"].split(" // ") [0]
            card["arena_id"] = processed_data[card_name]    
        
    except Exception as error:
        print("RetrieveLocalCardName Error: %s" % error)
        result = False
    
    return result

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
    
def DateCheck(date):
    result = True
    try:
        parts = date.split("-")
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = 0
        
        if datetime.datetime(year=year,month=month,day=day,hour=hour) > datetime.datetime.now():
            result = False
            
    except Exception as error:
        result = False
    return result
    
def FileIntegrityCheck(filename):
    result = Result.VALID
    json_data = {}
    while(1):
        #Check 1) File is present
        try:
            with open(filename, 'r') as json_file:
                json_data = json_file.read()
        except Exception as error:
            result = Result.ERROR_MISSING_FILE
            break
            
        #Check 2) File contains required elements
        try:
            json_data = json.loads(json_data)
            
            #Check 2A) Meta data is present
            version = json_data["meta"]["version"]
            if version == 1:
                start_date, end_date = json_data["meta"]["date_range"].split("->")
            elif version == 2:
                start_date = json_data["meta"]["start_date"] 
                end_date = json_data["meta"]["end_date"] 
                
            #Check 2B) Card data is present
            cards = json_data["card_ratings"]
            for card in cards:
                name = cards[card]["name"]
                colors = cards[card]["colors"]
                cmc = cards[card]["cmc"]
                types = cards[card]["types"]
                mana_cost = cards[card]["mana_cost"]
                image = cards[card]["image"]
                gihwr = cards[card]["deck_colors"]["All Decks"]["gihwr"]
                alsa = cards[card]["deck_colors"]["All Decks"]["alsa"]
                iwd = cards[card]["deck_colors"]["All Decks"]["iwd"]
                break
                
            if len(cards.keys()) < 100:
                result = Result.ERROR_UNREADABLE_FILE
                break
            
        except Exception as error:
            result = Result.ERROR_UNREADABLE_FILE
            break
        break
    return result, json_data
       
class DataPlatform:
    def __init__(self, diag_log_file, diag_log_enabled):
        self.sets = []
        self.diag_log_file = diag_log_file
        self.diag_log_enabled = diag_log_enabled
        self.draft = ""
        self.session = ""
        self.start_date = ""
        self.end_date = ""
        self.context = ssl.SSLContext()
        self.id = id
        self.operating_system = "PC"
        self.card_ratings = {}
        self.combined_data = {}
        self.card_list = []
        #self.driver_path = os.getcwd() + '\geckodriver.exe'
        #self.driver = webdriver.Firefox(executable_path = self.driver_path)
        self.combined_data["meta"] = {"collection_date" : str(datetime.datetime.now())}
        self.deck_colors = ["All Decks", "W","U","B","R","G","WU","WB","WR","WG","UB","UR","UG","BR","BG","RG","WUB","WUR","WUG","WBR","WBG","WRG","UBR","UBG","URG","BRG"]
    def OS(self, operating_system):
        self.operating_system = operating_system
    
    def Sets(self, sets):
        self.sets = sets
        
    def DraftType(self, draft_type):
        self.draft = draft_type
        
    def StartDate(self, start_date):
        result = False
        if DateCheck(start_date):
            result = True
            self.start_date = start_date
            self.combined_data["meta"]["start_date"] = self.start_date
        return result
    def EndDate(self, end_date):
        result = False
        if DateCheck(end_date):
            result = True
            self.end_date = end_date
            self.combined_data["meta"]["end_date"] = self.end_date
        return result
        
    def ID(self, id):
        result = False
        if id.isnumeric():
            result = True
            self.id = id
        return result
    def Version(self, version):
        self.combined_data["meta"]["version"] = version
        
    def SessionRepositoryVersion(self):
        version = ""
        try:
            url = "https://raw.github.com/bstaple1/MTGA_Draft_17Lands/master/version.txt"
            url_data = urllib.request.urlopen(url, context=self.context).read()
            
            version = self.ProcessRepositoryVersionData(url_data)
                
        except Exception as error:
            print("SessionRepositoryVersion Error: %s" % error)
        return version

    def SessionRepositoryDownload(self, filename):
        version = ""
        try:
            url = "https://raw.github.com/bstaple1/MTGA_Draft_17Lands/master/%s" % filename
            url_data = urllib.request.urlopen(url, context=self.context).read()
            
            with open(filename,'wb') as file:
                file.write(url_data)   
        except Exception as error:
            print("SessionRepositoryDownload Error: %s" % error)
        return version  


    def SessionCardData(self):
        arena_id = int(self.id)
        result = False
        local_check = False
        self.card_list = []
        result_string = "Couldn't Retrieve Card Data"
        for set in self.sets:
            if set == "dbl":
                continue
            retry = 5
            while retry:
                try:
                    #https://api.scryfall.com/cards/search?order=set&q=e%3AKHM
                    url = "https://api.scryfall.com/cards/search?order=set&q=e" + urlencode(':', safe='') + "%s" % (set)
                    url_data = urllib.request.urlopen(url, context=self.context).read()
                    
                    set_json_data = json.loads(url_data)
        
                    arena_id, result, result_string, local_check = self.ProcessCardData(set_json_data["data"], arena_id)
                    
                    while (set_json_data["has_more"] == True) and (result == True):
                        url = set_json_data["next_page"]
                        url_data = urllib.request.urlopen(url, context=self.context).read()
                        set_json_data = json.loads(url_data)
                        arena_id, result, result_string, local_check = self.ProcessCardData(set_json_data["data"], arena_id)
                    
                    #Collect arena IDs from local files
                    if local_check:
                        result, result_string = RetrieveLocalArenaData(self.operating_system, self.card_list, set.upper())
                    
                    if result == True:
                        break
                        
                except Exception as error:
                    error_string = "SessionCardData Error: %s" % error
                    result_string = error
                    print(error_string)     
                    LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
                
                if result == False:
                    retry -= 1
                    time.sleep(5)
        return result, result_string

    def InitializeCardRatings(self):
        self.card_ratings = {}

        for card in self.card_list:
            card_name = card["name"].split(" // ") [0]
            self.card_ratings[card_name] = []
            for color in self.deck_colors:
                self.card_ratings[card_name].append({color : {"gihwr" : 0.0, "iwd" : 0.0, "alsa" : 0.0}})

        #Add in basic lands
        lands = ["Mountain","Swamp","Plains","Forest","Island"]
        for land in lands:
            self.card_ratings[land] = []
            for color in self.deck_colors:
                self.card_ratings[land].append({color : {"gihwr" : 0.0, "iwd" : 0.0, "alsa" : 0.0}})
        
    def SessionCardRating(self, root, progress, initial_progress):
        current_progress = 0
        result = False
        self.InitializeCardRatings()
        for set in self.sets:
            if set == "dbl":
                continue
            for color in self.deck_colors:
                retry = 5
                result = False
                while retry:
                    
                    try:
                        url = "https://www.17lands.com/card_ratings/data?expansion=%s&format=%s&start_date=%s&end_date=%s" % (set, self.draft, self.start_date, self.end_date)
                        
                        if color != "All Decks":
                            url += "&colors=" + color
                        print(url)    
                        url_data = urllib.request.urlopen(url, context=self.context).read()
                        
                        set_json_data = json.loads(url_data)
                        self.RetrieveCardRatingsUrl(color, set_json_data)
                        result = True
                        break
                    except Exception as error:
                        error_string = "SessionCardRating Error: %s" % error
                        print(error_string)     
                        LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
                        time.sleep(15)
                        retry -= 1
                        
                if result:
                    current_progress += 3 / len(self.sets)
                    progress['value'] = current_progress + initial_progress
                    root.update()
                else:
                    break
                time.sleep(2)
         
            if set == "stx":
                break
            #if set == "dbl" and result:
            #    break
        self.combined_data["card_ratings"] = {}
        for card in self.card_list:
            self.ProcessCardRatings(card)
            
        return result 
        
    def SessionSets(self):
        sets = {}
        try:
            url = "https://api.scryfall.com/sets"
            url_data = urllib.request.urlopen(url, context=self.context).read()
            
            set_json_data = json.loads(url_data)
            sets = self.ProcessSetData(sets, set_json_data["data"])
            while set_json_data["has_more"] == True:
                url = set_json_data["next_page"]
                url_data = urllib.request.urlopen(url, context=self.context).read()
                set_json_data = json.loads(url_data)
                sets = self.ProcessSetData(sets, set_json_data["data"])
                
                
        except Exception as error:
            error_string = "SessionSets Error: %s" % error
            print(error_string)     
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        return sets   
    def SessionColorRatings(self):
        try:
            #https://www.17lands.com/color_ratings/data?expansion=VOW&event_type=QuickDraft&start_date=2019-1-1&end_date=2022-01-13&combine_splash=true
            url = "https://www.17lands.com/color_ratings/data?expansion=%s&event_type=%s&start_date=%s&end_date=%s&combine_splash=true" % (self.sets[0], self.draft, self.start_date, self.end_date)
            print(url)
            url_data = urllib.request.urlopen(url, context=self.context).read()
            
            color_json_data = json.loads(url_data)
            print(color_json_data)
            self.RetrieveColorRatings(color_json_data)
            
        except Exception as error:
            error_string = "SessionColorRatings Error: %s" % error
            print(error_string)     
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled) 
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
                
                gihwr = gihwr if gihwr != None else "0.0"
                
                win_count = float(gihwr) * int(card["ever_drawn_game_count"])
                gihwr = 100.0*(win_count + 10)/ ( int(card["ever_drawn_game_count"]) + 20) #Bayesian average

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
                
        return result  
        
    def RetrieveColorRatings(self, colors):
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
            self.combined_data["color_ratings"] = {}
            for color in colors:
                games = color["games"]
                if (color["is_summary"] == False) and (games > 5000):
                    color_name = color["color_name"]
                    winrate = round((float(color["wins"])/color["games"]) * 100, 1)
                    
                    color_label = [x for x in color_ratings_dict.keys() if x in color_name]
                    
                    print(color_name)
                    print(winrate)
                    
                    
                    if len(color_label):
                        
                        processed_colors = color_ratings_dict[color_label[0]]
                        
                        if processed_colors not in self.combined_data["color_ratings"].keys():
                            self.combined_data["color_ratings"][processed_colors] = winrate
            
        except Exception as error:
            print("RetrieveColorRatings Error: %s" % error)
          
    def ProcessCardData (self, data, arena_id):
        result = False
        local_check = False
        result_string = ""
        for card_data in data:
            try:
                #Skip Alchemy cards
                if card_data["name"].startswith("A-"):
                    continue
            
                card = {}
        
                card["cmc"] = card_data["cmc"]
                card["name"] = card_data["name"]
                card["color_identity"] = card_data["color_identity"]
                card["types"] = ExtractTypes(card_data["type_line"])
                card["image"] = []
                
                if arena_id == 0:
                    try:
                        card["arena_id"] = card_data["arena_id"]
                    except Exception as error:
                        local_check = True
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
                self.card_list.append(card)
                result = True
                
            except Exception as error:
                print("ProcessCardData Error: %s" % error)
                result_string = error
        #print("combined_data: %s" % str(combined_data))
        return arena_id, result, result_string, local_check 
        
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
            
        except Exception as error:
            print(error)
            
        #print("combined_data: %s" % str(combined_data))
        return
        
    def ProcessSetData (self, sets, data):
        counter = 0
        for set in data:
            try:
                set_name = set["name"]
                set_code = set["code"]
                
                if set_code == "dbl":
                    sets[set_name] = []
                    sets[set_name].append(set_code)
                    sets[set_name].append("vow")
                    sets[set_name].append("mid")
                elif (len(set_code) == 3) and (set["set_type"] == "expansion"):
                    sets[set_name] = []
                    sets[set_name].append(set_code)
                    #Add mystic archives to strixhaven
                    if set_code == "stx":
                        sets[set_name].append("sta")
                    counter += 1
                    
                    # Only retrieve the last 15 sets
                    if counter >= 15:
                        break
            except Exception as error:
                print("ProcessSetData Error: %s" % error)
        
        return sets
        
    def ProcessRepositoryVersionData(self, data):
        version = round(float(data.decode("ascii")) * 100)
        
        return version
    def ExportData(self):
        result = True
        try:
            output_file = self.sets[0].upper() + "_" + self.draft + "_Data.json"

            with open(output_file, 'w') as f:
                json.dump(self.combined_data, f)
                
            #Verify that the file was written
            write_result, write_data = FileIntegrityCheck(output_file)
            
            if write_result != Result.VALID:
                result = False
            
        except Exception as error:
            print("ExportData Error: %s" % error)
            result = False
            
        return result