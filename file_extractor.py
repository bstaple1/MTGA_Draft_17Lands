import sys
import os
import time
import json
import urllib.request
import datetime
import ssl
import itertools
import logging
import re
import sqlite3
import constants
from enum import Enum
import log_scanner as LS
from urllib.parse import quote as urlencode

if not os.path.exists(constants.SETS_FOLDER):
    os.makedirs(constants.SETS_FOLDER)

if not os.path.exists(constants.TIER_FOLDER):
    os.makedirs(constants.TIER_FOLDER)

if not os.path.exists(constants.TEMP_FOLDER):
    os.makedirs(constants.TEMP_FOLDER)

file_logger = logging.getLogger(constants.LOG_TYPE_DEBUG)

class Result(Enum):
    VALID = 0
    ERROR_MISSING_FILE = 1
    ERROR_UNREADABLE_FILE = 2
    
def DecodeManaCost(encoded_cost):
    decoded_cost = ""
    cmc = 0
    if len(encoded_cost):
        cost_string = re.sub('\(|\)', '', encoded_cost)
        
        sections = cost_string[1:].split("o")
        for section in sections:
            cmc += int(section) if section.isnumeric() else 1

        decoded_cost = "".join("{{{0}}}".format(x) for x in sections)
    
    return decoded_cost, cmc
def RetrieveLocalSetList(sets):
    file_list = []
    main_sets = [v[constants.SET_LIST_17LANDS][0] for k, v in sets.items()]
    for file in os.listdir(constants.SETS_FOLDER):
        try:
            name_segments = file.split("_")
            if len(name_segments) == 3:

                if ((name_segments[0].upper() in main_sets) and 
                    (name_segments[1] in constants.LIMITED_TYPES_DICT.keys()) and 
                    (name_segments[2] == constants.SET_FILE_SUFFIX)):
                    
                    set_name = list(sets.keys())[list(main_sets).index(name_segments[0].upper())]
                    result, json_data = FileIntegrityCheck(os.path.join(constants.SETS_FOLDER,file))
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
    log_location = ""
    try:
        if sys.platform == constants.PLATFORM_ID_OSX:
            paths = [os.path.join(os.path.expanduser('~'), constants.LOG_LOCATION_OSX)]
        else:
            path_list = [constants.WINDOWS_DRIVES, [constants.LOG_LOCATION_WINDOWS]]
            paths = [os.path.join(*x) for x in  itertools.product(*path_list)]
            
        for file_path in paths:
            file_logger.info(f"Arena Log: Searching file path {file_path}")
            if os.path.exists(file_path):
                log_location = file_path
                break
                
    except Exception as error:
        file_logger.info(f"ArenaLogLocation Error: {error}")
    return log_location
    
def ArenaDirectoryLocation(log_location):
    arena_directory = ""
    try:
        #Retrieve the arena directory
        with open(log_location, 'r') as log_file:
            line = log_file.readline()
            location = re.findall(r"'(.*?)/Managed'", line, re.DOTALL)
            if location and os.path.exists(location[0]):
                arena_directory = location[0]
                file_logger.info(f"Arena Directory: {arena_directory}")

                
    except Exception as error:
        file_logger.info(f"ArenaDirectoryLocation Error: {error}")
    return arena_directory
 
def SearchLocalFiles(paths, file_prefixes):
    file_locations = []
    for file_path in paths:
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
    while(True):
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
            else:
                start_date = json_data["meta"]["start_date"] 
                end_date = json_data["meta"]["end_date"] 
                
            #Check 2B) Card data is present
            cards = json_data["card_ratings"]
            for card in cards:
                name = cards[card][constants.DATA_FIELD_NAME]
                colors = cards[card][constants.DATA_FIELD_COLORS]
                cmc = cards[card][constants.DATA_FIELD_CMC]
                types = cards[card][constants.DATA_FIELD_TYPES]
                mana_cost = cards[card]["mana_cost"]
                image = cards[card][constants.DATA_SECTION_IMAGES]
                gihwr = cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIHWR]
                alsa = cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_ALSA]
                iwd = cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_IWD]
                break
                
            if len(cards.keys()) < 100:
                result = Result.ERROR_UNREADABLE_FILE
                break
            
        except Exception as error:
            result = Result.ERROR_UNREADABLE_FILE
            break
        break
    return result, json_data
       
class FileExtractor:
    def __init__(self, directory):
        self.selected_sets = []
        self.set_list = []
        self.draft = ""
        self.session = ""
        self.start_date = ""
        self.end_date = ""
        self.directory = directory
        self.context = ssl.SSLContext()
        self.id = id
        self.card_ratings = {}
        self.combined_data = {"meta" : {"collection_date" : str(datetime.datetime.now())}}
        self.card_dict = {}
        self.deck_colors = constants.DECK_COLORS

    def ClearData(self):
        self.combined_data = {"meta" : {"collection_date" : str(datetime.datetime.now())}}
        
    def Sets(self, sets):
        self.selected_sets = sets
        
    def SetList(self):
        if not self.set_list:
            self.set_list = self.SessionSets()
        
        return self.set_list
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
        
    def Version(self, version):
        self.combined_data["meta"]["version"] = version
        
    def RetrieveLocalArenaData(self, database_size):
        result_string = "Couldn't Collect Local Card Data"
        result = False
        self.card_dict = {}
          
        if sys.platform == constants.PLATFORM_ID_OSX:
            directory = os.path.join(os.path.expanduser('~'), constants.LOCAL_DATA_FOLDER_PATH_OSX) if not self.directory else self.directory
            paths = [os.path.join(directory, constants.LOCAL_DOWNLOADS_DATA)]
        else:
            if not self.directory:
                path_list = [constants.WINDOWS_DRIVES, constants.WINDOWS_PROGRAM_FILES, [constants.LOCAL_DATA_FOLDER_PATH_WINDOWS]]
                paths = [os.path.join(*x) for x in  itertools.product(*path_list)]
            else:
                paths = [os.path.join(self.directory, constants.LOCAL_DOWNLOADS_DATA)]
        
        arena_cards_locations = SearchLocalFiles(paths, [constants.LOCAL_DATA_FILE_PREFIX_CARDS])
        arena_database_locations = SearchLocalFiles(paths, [constants.LOCAL_DATA_FILE_PREFIX_DATABASE])
        
        if (not len(arena_cards_locations) or 
            not len(arena_database_locations)):
            return result, result_string
        
        for set in self.selected_sets[constants.SET_LIST_ARENA]:
            result = False
            while(True):
                try:      
                    file_logger.info(f"Local Card Data: Searching file path {arena_cards_locations[0]}")
                    #Check temporary localization data and update it if necessary
                    result, card_text, card_enumerators, database_size = self.CollectLocalizationData(arena_database_locations[0], database_size)
                    
                    if not result:
                        break
                
                    #Retrieve the card data without text
                    result = self.RetrieveLocalCards(arena_cards_locations[0], set)
                    
                    if not result:
                        break
                                   

                        
                    #Assemble information for local data set
                    result = self.AssembleLocalDataSet(card_text, card_enumerators)
                    
                except Exception as error:
                    file_logger.info(f"RetrieveLocalArenaData Error: {error}")
                break
        
        if not result:
            file_logger.info(result_string)
        
        return result, result_string, database_size 
        
    def CollectLocalizationData(self, file_location, file_size):
        result = False
        card_text = {}
        card_enumerators = {}
        current_database_size = 0
        
        try:
            while(True): #break loop
                    
                #Determine if the database file matches the file size (indicates that the temporary data is up-to-date)
                database_size = os.path.getsize(file_location)
                
                if database_size != file_size:
                    file_logger.info(f"Database change detected {database_size}, {file_size}")
                    #Update the temp file with data from the database
                    if not self.RetrieveLocalDatabase(file_location):
                        break
                    
                #Collect the localization and enumeration data from the temp localization file
                with open(constants.TEMP_LOCALIZATION_FILE, 'r', encoding='utf-8') as data:
                    json_file = data.read()
                    json_data = json.loads(json_file)

                    card_text = json_data["localization"]
                    card_enumerators = json_data["enumeration"]
            
                
                current_database_size = database_size
                result = True
                break
        
        
        except Exception as error:
            file_logger.info(f"CollectLocalizationData Error: {error}")
        
        if not result:
            file_logger.info(f"Failed to create temp localization file")
        
        return result, card_text, card_enumerators, current_database_size
        

    def RetrieveLocalCards(self, file_location, card_set):
        result = False
        try:
            with open(file_location, 'r', encoding="utf8") as json_file:
                json_data = json.loads(json_file.read())
                
                for card in json_data:
                    card = {k.lower(): v for k, v in card.items()} #Making all of the keys lowercase
                    if ((card_set in card[constants.LOCAL_CARDS_KEY_SET]) or
                       ((constants.LOCAL_CARDS_KEY_DIGITAL_RELEASE_SET in card) and (card_set in card[constants.LOCAL_CARDS_KEY_DIGITAL_RELEASE_SET]))):
                        try:
                            if constants.LOCAL_CARDS_KEY_TOKEN in card:
                                continue
                            
                            group_id = card[constants.LOCAL_CARDS_KEY_GROUP_ID]
                            
                            if constants.LOCAL_CARDS_KEY_LINKED_FACES in card:
                                linked_id = int(card[constants.LOCAL_CARDS_KEY_LINKED_FACES].split(',')[0])
                                if linked_id < group_id:
                                    #The application will no longer list the names of all the card faces. This will address an issue with excessively long tooltips for specialize cards
                                    #self.card_dict[card["linkedFaces"][0]][constants.DATA_FIELD_NAME].append(card["titleId"])
                                    types = [int(x) for x in card[constants.LOCAL_CARDS_KEY_TYPES].split(',')] if constants.LOCAL_CARDS_KEY_TYPES in card else []
                                    self.card_dict[linked_id][constants.LOCAL_CARDS_KEY_TYPES].extend(types)
                                    continue
    
                            self.card_dict[group_id] = {constants.DATA_FIELD_NAME : [card[constants.LOCAL_CARDS_KEY_TITLE_ID]], constants.DATA_SECTION_IMAGES : []}
                            self.card_dict[group_id][constants.DATA_FIELD_TYPES] = [int(x) for x in card[constants.LOCAL_CARDS_KEY_TYPES].split(',')] if constants.LOCAL_CARDS_KEY_TYPES in card else []
                            self.card_dict[group_id][constants.DATA_FIELD_COLORS] = [int(x) for x in card[constants.LOCAL_CARDS_KEY_COLOR_ID].split(',')] if constants.LOCAL_CARDS_KEY_COLOR_ID in card else []
                            mana_cost, cmc = DecodeManaCost(card[constants.LOCAL_CARDS_KEY_CASTING_COST]) if constants.LOCAL_CARDS_KEY_CASTING_COST in card else ("",0)
                            self.card_dict[group_id][constants.DATA_FIELD_CMC] = cmc
                            self.card_dict[group_id]["mana_cost"] = mana_cost

                            result = True
                        except Exception as error:
                            pass
        except Exception as error:
            file_logger.info(f"RetrieveLocalCards Error: {error}")
            
        return result
      
    def RetrieveLocalDatabase(self, file_location):
        result = False
        card_data = {}
        try:
            #Open Sqlite3 database
            while(True):
                connection = sqlite3.connect(file_location)
                connection.row_factory = sqlite3.Row
                cursor = connection.cursor()
                
                rows = [dict(row) for row in cursor.execute(constants.LOCAL_DATABASE_LOCALIZATION_QUERY)]
                
                if not rows:
                    break
                
                result, card_data["localization"] = self.RetrieveLocalCardText(rows)
                
                if not result:
                    break
                
                        
                rows = [dict(row) for row in cursor.execute(constants.LOCAL_DATABASE_ENUMERATOR_QUERY)]
                
                if not rows:
                    break
                
                result, card_data["enumeration"] = self.RetrieveLocalCardEnumerators(rows)
                
                if not result:
                    break
                    
                #store the localization data in a temporary file
                with open(constants.TEMP_LOCALIZATION_FILE, 'w', encoding='utf-8') as json_file:
                    json.dump(card_data, json_file)
                
                result = True
                break
                
        except Exception as error:
            result = False
            file_logger.info(f"RetrieveLocalDatabase Error: {error}")
        
        return result
      
    def RetrieveLocalCardText(self, data):
        result = True
        card_text = {}
        try:
            #Retrieve the title (card name) for each of the collected arena IDs
            card_text = {x[constants.LOCAL_DATABASE_LOCALIZATION_COLUMN_ID] : x[constants.LOCAL_DATABASE_LOCALIZATION_COLUMN_TEXT] for x in data}
    
        except Exception as error:
            result = False
            file_logger.info(f"RetrieveLocalCardText Error: {error}")
        
        return result, card_text
        
    def RetrieveLocalCardEnumerators(self, data):
        result = True
        card_enumerators = {constants.DATA_FIELD_COLORS : {}, constants.DATA_FIELD_TYPES : {}}
        try:
            for row in data:
                    if row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_TYPE] == constants.LOCAL_DATABASE_ENUMERATOR_TYPE_CARD_TYPES:
                        card_enumerators[constants.DATA_FIELD_TYPES][row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_VALUE]] = str(row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_ID])
                    elif row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_TYPE] == constants.LOCAL_DATABASE_ENUMERATOR_TYPE_COLOR:
                        card_enumerators[constants.DATA_FIELD_COLORS][row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_VALUE]] = str(row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_ID])

        except Exception as error:
            result = False
            file_logger.info(f"RetrieveLocalCardEnumerators Error: {error}")
        
        return result, card_enumerators
    
    def AssembleLocalDataSet(self, card_text, card_enumerators):
        result = False
        try:
            for card in self.card_dict:
                try:
                    self.card_dict[card][constants.DATA_FIELD_NAME] = " // ".join(card_text[str(x)] for x in self.card_dict[card][constants.DATA_FIELD_NAME])     
                    self.card_dict[card][constants.DATA_FIELD_TYPES] = list(set([card_text[card_enumerators[constants.DATA_FIELD_TYPES][str(x)]] for x in self.card_dict[card][constants.DATA_FIELD_TYPES]]))
                    self.card_dict[card][constants.DATA_FIELD_COLORS] = [constants.CARD_COLORS_DICT[card_text[card_enumerators[constants.DATA_FIELD_COLORS][str(x)]]] for x in self.card_dict[card][constants.DATA_FIELD_COLORS]]
                    if "Creature" in self.card_dict[card][constants.DATA_FIELD_TYPES]:
                        index = self.card_dict[card][constants.DATA_FIELD_TYPES].index("Creature")
                        self.card_dict[card][constants.DATA_FIELD_TYPES].insert(0, self.card_dict[card][constants.DATA_FIELD_TYPES].pop(index))
                    result = True
                except Exception as error:
                    pass
    
        except Exception as error:
            result = False
            file_logger.info(f"AssembleLocalDataSet Error: {error}")
        
        return result
        
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


    def SessionScryfallData(self):
        result = False
        self.card_dict = {}
        result_string = "Couldn't Retrieve Card Data"
        for set in self.selected_sets[constants.SET_LIST_SCRYFALL]:
            if set == "dbl":
                continue
            retry = 5
            while retry:
                try:
                    #https://api.scryfall.com/cards/search?order=set&unique=prints&q=e%3AMID
                    url = "https://api.scryfall.com/cards/search?order=set&unique=prints&q=e" + urlencode(':', safe='') + "%s" % (set)
                    url_data = urllib.request.urlopen(url, context=self.context).read()
                    
                    set_json_data = json.loads(url_data)
            
                    result, result_string = self.ProcessScryfallData(set_json_data["data"])
                    
                    while (set_json_data["has_more"] == True) and (result == True):
                        url = set_json_data["next_page"]
                        url_data = urllib.request.urlopen(url, context=self.context).read()
                        set_json_data = json.loads(url_data)
                        result, result_string = self.ProcessScryfallData(set_json_data["data"])
                    
                    
                    if result == True:
                        break
                        
                except Exception as error:
                    file_logger.info(url)     
                    file_logger.info(f"SessionScryfallData Error: {error}")
                
                if result == False:
                    retry -= 1
                    time.sleep(5)
        return result, result_string

    def Initialize17LandsData(self):
        self.card_ratings = {}

        for card in self.card_dict:
            self.card_dict[card][constants.DATA_FIELD_DECK_COLORS] = {}
            for color in self.deck_colors:
                self.card_dict[card][constants.DATA_FIELD_DECK_COLORS][color] = {x : 0.0 for x in constants.DATA_FIELD_17LANDS_DICT.keys() if x != constants.DATA_SECTION_IMAGES}


    def Session17Lands(self, root, progress, initial_progress):
        current_progress = 0
        result = False
        self.Initialize17LandsData()
        for set in self.selected_sets[constants.SET_LIST_17LANDS]:
            if set == "dbl":
                continue
            for color in self.deck_colors:
                retry = 5
                result = False
                while retry:
                    
                    try:
                        url = f"https://www.17lands.com/card_ratings/data?expansion={set}&format={self.draft}&start_date={self.start_date}&end_date={self.end_date}"
                        
                        if color != constants.FILTER_OPTION_ALL_DECKS:
                            url += "&colors=" + color
                        url_data = urllib.request.urlopen(url, context=self.context).read()
                        
                        set_json_data = json.loads(url_data)
                        self.Retrieve17Lands(color, set_json_data)
                        result = True
                        break
                    except Exception as error:
                        file_logger.info(url) 
                        file_logger.info(f"Session17Lands Error: {error}")   
                        time.sleep(constants.CARD_RATINGS_BACKOFF_DELAY_SECONDS)
                        retry -= 1
                        
                if result:
                    current_progress += 3 / len(self.selected_sets[constants.SET_LIST_17LANDS])
                    progress['value'] = current_progress + initial_progress
                    root.update()
                else:
                    break
                time.sleep(constants.CARD_RATINGS_INTER_DELAY_SECONDS)
         
            if set == "stx":
                break
        for card in self.card_dict:
            self.ProcessCardRatings(self.card_dict[card])
        self.combined_data["card_ratings"] = self.card_dict
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
            url = f"https://www.17lands.com/color_ratings/data?expansion={self.selected_sets[constants.SET_LIST_17LANDS][0]}&event_type={self.draft}&start_date={self.start_date}&end_date={self.end_date}&combine_splash=true"
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
                card_data = {constants.DATA_SECTION_RATINGS : [], constants.DATA_SECTION_IMAGES : []}
                color_data = {colors : {}}
                for k, v in constants.DATA_FIELD_17LANDS_DICT.items():
                    if k == constants.DATA_SECTION_IMAGES:
                        for field in v:
                            if field in card and len(card[field]):
                                image_url = f"{constants.URL_17LANDS}{card[field]}" if constants.IMAGE_17LANDS_SITE_PREFIX in card[field] else card[field]
                                card_data[constants.DATA_SECTION_IMAGES].append(image_url)
                    elif v in card:
                        if (k in constants.WIN_RATE_OPTIONS) or (k == constants.DATA_FIELD_IWD):
                            color_data[colors][k] = round(float(card[v]) * 100.0, 2) if card[v] != None else 0.0
                        elif ((k == constants.DATA_FIELD_ATA) or 
                              (k == constants.DATA_FIELD_ALSA)):
                            color_data[colors][k] = round(float(card[v]), 2)
                        else:
                            color_data[colors][k] = int(card[v])

                card_name = card[constants.DATA_FIELD_NAME]
                
                if card_name not in self.card_ratings:
                    self.card_ratings[card_name] = card_data
                    
                self.card_ratings[card_name][constants.DATA_SECTION_RATINGS].append(color_data)
 
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

          
    def ProcessScryfallData (self, data):
        result = False
        result_string = "Arena IDs Unavailable"
        for card_data in data:
            try:
                if "arena_id" not in card_data:
                    continue
                
                arena_id = card_data["arena_id"]

                self.card_dict[arena_id] = {
                    constants.DATA_FIELD_NAME : card_data[constants.DATA_FIELD_NAME],
                    constants.DATA_FIELD_CMC : card_data[constants.DATA_FIELD_CMC],
                    constants.DATA_FIELD_COLORS : card_data["color_identity"],
                    constants.DATA_FIELD_TYPES : ExtractTypes(card_data["type_line"]),
                    "mana_cost" : 0,
                    constants.DATA_SECTION_IMAGES : [],
                }

                if "card_faces" in card_data:
                    self.card_dict[arena_id]["mana_cost"] = card_data["card_faces"][0]["mana_cost"]
                    self.card_dict[arena_id][constants.DATA_SECTION_IMAGES].append(card_data["card_faces"][0]["image_uris"]["normal"])
                    self.card_dict[arena_id][constants.DATA_SECTION_IMAGES].append(card_data["card_faces"][1]["image_uris"]["normal"])
                        
                else:
                    self.card_dict[arena_id]["mana_cost"] = card_data["mana_cost"]
                    self.card_dict[arena_id][constants.DATA_SECTION_IMAGES] = [card_data["image_uris"]["normal"]]

                result = True

            except Exception as error:
                file_logger.info(f"ProcessScryfallData Error: {error}")
                result_string = error

        return result, result_string
        
    def ProcessCardRatings (self, card):
        try:
            card_sides = card[constants.DATA_FIELD_NAME].split(" // ") 
            matching_cards = [x for x in self.card_ratings.keys() if x in card_sides]
            if(matching_cards):
                ratings_card_name = matching_cards[0]
                deck_colors = self.card_ratings[ratings_card_name][constants.DATA_SECTION_RATINGS]
                
                card[constants.DATA_SECTION_IMAGES] = self.card_ratings[ratings_card_name][constants.DATA_SECTION_IMAGES]
                for deck_color in deck_colors:
                    for key, value in deck_color.items():
                        for field in value:
                            card[constants.DATA_FIELD_DECK_COLORS][key][field] = value[field]
                        #card[constants.DATA_FIELD_DECK_COLORS][key] = {constants.DATA_FIELD_GIHWR :  value[constants.DATA_FIELD_GIHWR], 
                        #                                               constants.DATA_FIELD_ALSA  :  value[constants.DATA_FIELD_ALSA],
                        #                                               constants.DATA_FIELD_IWD   :  value[constants.DATA_FIELD_IWD],
                        #                                               constants.DATA_FIELD_GIH   :  value[constants.DATA_FIELD_GIH],
                        #                                               constants.DATA_FIELD_OHWR  :  value[constants.DATA_FIELD_OHWR],
                        #                                               constants.DATA_FIELD_NGOH  :  value[constants.DATA_FIELD_NGOH],
                        #                                               constants.DATA_FIELD_GPWR  :  value[constants.DATA_FIELD_GPWR],
                        #                                               constants.DATA_FIELD_NGP   :  value[constants.DATA_FIELD_NGP]}
        except Exception as error:
            file_logger.info(f"ProcessCardRatings Error: {error}")

        return
        
    def ProcessSetData (self, sets, data):
        counter = 0
        for set in data:
            try:
                set_name = set[constants.DATA_FIELD_NAME]
                set_code = set["code"]
                
                if set_code == "dbl":
                    sets[set_name] = {}
                    sets[set_name][constants.SET_LIST_ARENA] = ["VOW","MID"]
                    sets[set_name][constants.SET_LIST_17LANDS] = [set_code.upper()]
                    sets[set_name][constants.SET_LIST_SCRYFALL] = ["VOW","MID"]
                    counter += 1
                elif (set["set_type"] in constants.SUPPORTED_SET_TYPES):
                    if set["set_type"] == constants.SET_TYPE_ALCHEMY:
                        sets[set_name] = {}
                        if ("parent_set_code" in set) and ("block_code" in set):
                            sets[set_name][constants.SET_LIST_ARENA] = [set["parent_set_code"].upper()]
                            sets[set_name][constants.SET_LIST_17LANDS] = [f"{set['block_code'].upper()}{set['parent_set_code'].upper()}"]
                            sets[set_name][constants.SET_LIST_SCRYFALL] = [set_code.upper(), set["parent_set_code"].upper()]
                        else:
                            sets[set_name] = {key:[set_code.upper()] for key in [constants.SET_LIST_ARENA, constants.SET_LIST_SCRYFALL, constants.SET_LIST_17LANDS]}
                    elif (set["set_type"] == constants.SET_TYPE_MASTERS) and (set["digital"] == False):
                        continue
                    else:
                        sets[set_name] = {key:[set_code.upper()] for key in [constants.SET_LIST_ARENA, constants.SET_LIST_SCRYFALL, constants.SET_LIST_17LANDS]}
                        #Add mystic archives to strixhaven
                        if set_code == "stx":
                            sets[set_name][constants.SET_LIST_ARENA].append("STA")
                            sets[set_name][constants.SET_LIST_SCRYFALL].append("STA")
                    counter += 1
                    
                # Only retrieve the last 20 sets
                if counter >= 25:
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
            output_file = "_".join((self.selected_sets[constants.SET_LIST_17LANDS][0], self.draft, constants.SET_FILE_SUFFIX))
            location = os.path.join(constants.SETS_FOLDER, output_file)

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