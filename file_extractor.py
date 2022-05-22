import sys
import os
import time
import json
import urllib.request
import datetime
import ssl
import getpass
import itertools
import logging
from enum import Enum
import log_scanner as LS
from urllib.parse import quote as urlencode
LOCAL_DATA_FOLDER_PATH_WINDOWS = "Wizards of the Coast/MTGA/MTGA_Data/Downloads/Data/"
LOCAL_DATA_FOLDER_PATH_OSX = "Library/Application Support/com.wizards.mtga/Downloads/Data/"

LOCAL_DATA_FILE_PREFIX_CARDS = "Data_cards_"
LOCAL_DATA_FILE_PREFIX_TEXT = "Data_loc_"

SETS_FOLDER = os.path.join(os.getcwd(), "Sets")
SET_FILE_SUFFIX = "Data.json"

if not os.path.exists(SETS_FOLDER):
    os.makedirs(SETS_FOLDER)

PLATFORM_ID_OSX = "darwin"
PLATFORM_ID_WINDOWS = "win32"

LOG_LOCATION_WINDOWS = os.path.join('Users', getpass.getuser(), "AppData/LocalLow/Wizards Of The Coast/MTGA/Player.log")
LOG_LOCATION_OSX = "Library/Logs/Wizards of the Coast/MTGA/Player.log"

DEFAULT_GIHWR_AVERAGE = 0.0

WINDOWS_DRIVES = ["C:/","D:/","E:/","F:/"]
WINDOWS_PROGRAM_FILES = ["Program Files","Program Files (x86)"]

platform_log_dict = {
    PLATFORM_ID_OSX     : LOG_LOCATION_OSX,
    PLATFORM_ID_WINDOWS : LOG_LOCATION_WINDOWS,
}

file_logger = logging.getLogger("mtgaTool")

class Result(Enum):
    VALID = 0
    ERROR_MISSING_FILE = 1
    ERROR_UNREADABLE_FILE = 2
    
def RetrieveLocalSetList(sets):
    file_list = []
    main_sets = [v[0] for k, v in sets.items()]
    for file in os.listdir(SETS_FOLDER):
        try:
            name_segments = file.split("_")
            if len(name_segments) == 3:

                if ((name_segments[0].lower() in main_sets) and 
                    (name_segments[1] in LS.limited_types_dict.keys()) and 
                    (name_segments[2] == SET_FILE_SUFFIX)):
                    
                    set_name = list(sets.keys())[list(main_sets).index(name_segments[0].lower())]
                    result, json_data = FileIntegrityCheck(file)
                    if result == Result.VALID:
                        if json_data["meta"]["version"] == 1:
                            start_date, end_date = json_data["meta"]["date_range"].split("->")
                        else:
                            start_date = json_data["meta"]["start_date"] 
                            end_date = json_data["meta"]["end_date"] 
                        file_list.append((set_name, name_segments[1], start_date, end_date)) 
        except Exception as error:
            file_logger.info(f"RetrieveLocalSetList Error: {error}")
    
    return file_list
def ArenaLogLocation():
    file_location = ""
    try:
        if sys.platform == PLATFORM_ID_OSX:
            paths = [os.path.join(os.path.expanduser('~'), LOG_LOCATION_OSX)]
        else:
            path_list = [WINDOWS_DRIVES, [LOG_LOCATION_WINDOWS]]
            paths = [os.path.join(*x) for x in  itertools.product(*path_list)]
            
        for file_path in paths:
            if os.path.exists(file_path):
                file_location = file_path
                break
                
    except Exception as error:
        file_logger.info(f"ArenaLogLocation Error: {error}")
    return file_location
    
def RetrieveLocalArenaData(card_data, card_set):
    result_string = "Arena IDs Unavailable"
    result = False
    
    while(True):
        try:
            if sys.platform == PLATFORM_ID_OSX:
                paths = [os.path.join(os.path.expanduser('~'), LOCAL_DATA_FOLDER_PATH_OSX)]
            else:
                path_list = [WINDOWS_DRIVES, WINDOWS_PROGRAM_FILES, [LOCAL_DATA_FOLDER_PATH_WINDOWS]]
                paths = [os.path.join(*x) for x in  itertools.product(*path_list)]
        
            arena_cards_locations = SearchLocalFiles(paths, [LOCAL_DATA_FILE_PREFIX_CARDS])
            arena_text_locations = SearchLocalFiles(paths, [LOCAL_DATA_FILE_PREFIX_TEXT])

            if (len(arena_cards_locations) == 0) or (len(arena_text_locations) == 0):
                break
                
            #Retrieve the arena IDs without card names
            result, arena_data = RetrieveLocalArenaId(arena_cards_locations[0], card_set)
            
            if result == False:
                break
                
            #Retrieve the card names for each arena ID
            result = RetrieveLocalCardName(arena_text_locations[0], arena_data, card_data)
            
        except Exception as error:
            file_logger.info(f"RetrieveLocalArenaData Error: {error}")
        break
    return result, result_string
 
def SearchLocalFiles(paths, file_prefixes):
    file_locations = []
    for file_path in paths:
        file_logger.info(f"Searching file path {file_path} for {file_prefixes}")
        try:           
            if os.path.exists(file_path):
                for prefix in file_prefixes:
                    files = [filename for filename in os.listdir(file_path) if filename.startswith(prefix)]
                    
                    for file in files:
                        file_location = os.path.join(file_path, file)
                        file_locations.append(file_location)
        
        except Exception as error:
            file_logger.info(f"SearchLocalFiles Error: {error}")
                    
    return file_locations
    
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
        file_logger.info(f"RetrieveLocalArenaId Error: {error}")
        
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
        result = False
        file_logger.info(f"RetrieveLocalCardName Error: {error}")
    
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
    def __init__(self):
        self.sets = []
        self.draft = ""
        self.session = ""
        self.start_date = ""
        self.end_date = ""
        self.context = ssl.SSLContext()
        self.id = id
        self.card_ratings = {}
        self.combined_data = {}
        self.card_list = []
        self.combined_data["meta"] = {"collection_date" : str(datetime.datetime.now())}
        self.deck_colors = LS.DECK_COLORS

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
            file_logger.info(f"SessionRepositoryVersion Error: {error}")
        return version

    def SessionRepositoryDownload(self, filename):
        version = ""
        try:
            url = "https://raw.github.com/bstaple1/MTGA_Draft_17Lands/master/%s" % filename
            url_data = urllib.request.urlopen(url, context=self.context).read()
            
            with open(filename,'wb') as file:
                file.write(url_data)   
        except Exception as error:
            file_logger.info(f"SessionRepositoryDownload Error: {error}")
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
                        result, result_string = RetrieveLocalArenaData(self.card_list, set.upper())
                    
                    if result == True:
                        break
                        
                except Exception as error:
                    file_logger.info(url)     
                    file_logger.info(f"SessionCardData Error: {error}")
                
                if result == False:
                    retry -= 1
                    time.sleep(5)
        return result, result_string

    def Initialize17LandsData(self):
        self.card_ratings = {}

        for card in self.card_list:
            card_name = card["name"].split(" // ") [0]
            self.card_ratings[card_name] = []
            for color in self.deck_colors:
                self.card_ratings[card_name].append({color : {"gihwr" : DEFAULT_GIHWR_AVERAGE, "iwd" : 0.0, "alsa" : 0.0, "gih" : 0.0}})

        #Add in basic lands
        lands = ["Mountain","Swamp","Plains","Forest","Island"]
        for land in lands:
            self.card_ratings[land] = []
            for color in self.deck_colors:
                self.card_ratings[land].append({color : {"gihwr" : 0.0, "iwd" : 0.0, "alsa" : 0.0, "gih" : 0.0}})
        
    def Session17Lands(self, root, progress, initial_progress):
        current_progress = 0
        result = False
        self.Initialize17LandsData()
        for set in self.sets:
            if set == "dbl":
                continue
            for color in self.deck_colors:
                retry = 5
                result = False
                while retry:
                    
                    try:
                        url = "https://www.17lands.com/card_ratings/data?expansion=%s&format=%s&start_date=%s&end_date=%s" % (set.upper(), self.draft, self.start_date, self.end_date)
                        
                        if color != "All Decks":
                            url += "&colors=" + color
                        url_data = urllib.request.urlopen(url, context=self.context).read()
                        
                        set_json_data = json.loads(url_data)
                        self.Retrieve17Lands(color, set_json_data)
                        result = True
                        break
                    except Exception as error:
                        file_logger.info(url) 
                        file_logger.info(f"Session17Lands Error: {error}")   
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
            file_logger.info(f"SessionSets Error: {error}") 
        return sets   
    def SessionColorRatings(self):
        try:
            #https://www.17lands.com/color_ratings/data?expansion=VOW&event_type=QuickDraft&start_date=2019-1-1&end_date=2022-01-13&combine_splash=true
            url = "https://www.17lands.com/color_ratings/data?expansion=%s&event_type=%s&start_date=%s&end_date=%s&combine_splash=true" % (self.sets[0], self.draft, self.start_date, self.end_date)
            url_data = urllib.request.urlopen(url, context=self.context).read()
            
            color_json_data = json.loads(url_data)
            self.RetrieveColorRatings(color_json_data)
            
        except Exception as error:
            file_logger.info(url) 
            file_logger.info(f"SessionColorRatings Error: {error}") 
    def Retrieve17Lands(self, colors, cards):  
        result = True

        for card in cards:
            try:
                card_name = card["name"]
                gihwr = card["ever_drawn_win_rate"]
                iwd = card["drawn_improvement_win_rate"]
                alsa = card["avg_seen"]
                gih = int(card["ever_drawn_game_count"])
                
                gihwr = gihwr if gihwr != None else "0.0"

                gihwr = round(float(gihwr) * 100.0, 2)
                
                iwd = round(float(card["drawn_improvement_win_rate"]) * 100, 2)
                alsa = round(float(card["avg_seen"]), 2)
                try:
                    self.card_ratings[card_name].append({colors : {"gihwr" : gihwr, "iwd" : iwd, "alsa" : alsa, "gih" : gih}})
                except Exception as error:
                    self.card_ratings[card_name] = []
                    self.card_ratings[card_name].append({colors : {"gihwr" : gihwr, "iwd" : iwd, "alsa" : alsa, "gih" : gih}}) 
                self.card_ratings[card_name]
            except Exception as error:
                result = False
                file_logger.info(f"Retrieve17Lands Error: {error}")
                
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

                    if len(color_label):
                        
                        processed_colors = color_ratings_dict[color_label[0]]
                        
                        if processed_colors not in self.combined_data["color_ratings"].keys():
                            self.combined_data["color_ratings"][processed_colors] = winrate
            
        except Exception as error:
            file_logger.info(f"RetrieveColorRatings Error: {error}")

          
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
                    card["mana_cost"] = "0"
                    card["image"] = []
                self.card_list.append(card)
                result = True
                
            except Exception as error:
                file_logger.info(f"ProcessCardData Error: {error}")
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
                                                                                           "iwd" : value["iwd"],
                                                                                           "gih" : value["gih"]}
            
        except Exception as error:
            file_logger.info(f"ProcessCardRatings Error: {error}")
            
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
                file_logger.info(f"ProcessSetData Error: {error}")
        
        return sets
        
    def ProcessRepositoryVersionData(self, data):
        version = round(float(data.decode("ascii")) * 100)
        
        return version
    def ExportData(self):
        result = True
        try:
            output_file = "_".join((self.sets[0].upper(), self.draft, SET_FILE_SUFFIX))
            location = os.path.join(SETS_FOLDER, output_file)

            with open(location, 'w') as f:
                json.dump(self.combined_data, f)
                
            #Verify that the file was written
            write_result, write_data = FileIntegrityCheck(location)
            
            if write_result != Result.VALID:
                result = False
            
        except Exception as error:
            file_logger.info(f"ExportData Error: {error}")
            result = False
            
        return result