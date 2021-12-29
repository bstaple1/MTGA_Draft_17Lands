#!/usr/bin/env python3
"""! @brief Magic the Gathering draft application that utilizes 17Lands data"""


##
# @mainpage Magic Draft Application
#
# @section description_main Description
# A program that utilizes 17Lands data to dispay pick ratings, deck statistics, and deck suggestions
#
# @section notes_main Notes
# - 
#


##
# @file main.py
#
# @brief 
#
# @section Description
# A program that utilizes 17Lands data to dispay pick ratings, deck statistics, and deck suggestions
#
# @section libraries_main Libraries/Modules
# - tkinter standard library (https://docs.python.org/3/library/tkinter.html)
#   - Access to GUI functions.
# - pynput library (https://pypi.org/project/pynput)
#   - Access to the keypress monitoring functions.
# - datetime standard library (https://docs.python.org/3/library/datetime.html)
#   - Access to the current date function.
# - urllib standard library (https://docs.python.org/3/library/urllib.html)
#   - Access to URL opening function.
# - json standard library (https://docs.python.org/3/library/json.html)
#   - Access to the json encoding and decoding functions
# - os standard library (https://docs.python.org/3/library/os.html)
#   - Access to the file system navigation functions.
# - time standard library (https://docs.python.org/3/library/time.html)
#   - Access to sleep function.
# - getopt standard library (https://docs.python.org/3/library/getopt.html)
#   - Access to the command line interface functions.
# - sys standard library (https://docs.python.org/3/library/sys.html)
#   - Access to the command line argument list.
# - io standard library (https://docs.python.org/3/library/sys.html)
#   - Access to the command line argument list.
# - PIL library (https://pillow.readthedocs.io/en/stable/)
#   - Access to image manipulation modules.
# - file_extractor module (local)
#   - Access to the functions used for downloading the data sets.
# - card_logic module (local)
#   - Access to the functions used for processing the card data.
#
# @section Notes
# - Comments are Doxygen compatible.
#
# @section TODO
# - None.
#
# @section Author(s)
# - Created by Bryan Stapleton on 12/25/2021

# Imports
from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog
from pynput.keyboard import Key, Listener, KeyCode
from datetime import date
import urllib
import json
import os
import time 
import getopt
import sys
import io
import file_extractor as FE
import card_logic as CL

# Global Constants
## The different types of draft.
DRAFT_TYPE_UNKNOWN     = 0
DRAFT_TYPE_PREMIER_V1  = 1
DRAFT_TYPE_PREMIER_V2  = 2
DRAFT_TYPE_QUICK       = 3
DRAFT_TYPE_TRADITIONAL = 4

## Location of the MTGA player log.
LOG_LOCATION_PC = "\\AppData\\LocalLow\\Wizards Of The Coast\\MTGA\\Player.log"
LOG_LOCATION_MAC = "/Library/Logs/Wizards of the Coast/MTGA/Player.log"

#Dictionaries
## Used to identify draft type based on log string
draft_types_dict = {
    "PremierDraft"     : DRAFT_TYPE_PREMIER_V1,
    "QuickDraft"       : DRAFT_TYPE_QUICK,
    "TraditionalDraft" : DRAFT_TYPE_TRADITIONAL,
}

## Used to identify OS type based on CLI string
os_log_dict = {
    "MAC" : LOG_LOCATION_MAC,
    "PC"  : LOG_LOCATION_PC,
}


# Functions
##
def OnPress(key, ui):
    if key == KeyCode.from_char('\x06'): #CTRL+F
        ui.WindowLift(ui.root)

def KeyListener(window_ui):
    Listener(on_press=lambda event: OnPress(event, ui=window_ui)).start()
         

def LogEntry(log_name, entry_text, diag_log_enabled):
    if diag_log_enabled:
        try:
            with open(log_name, "a") as log_file:
                log_file.write("<%s>%s\n" % (time.strftime('%X %x'), entry_text))
        except Exception as error:
            print("LogEntry Error:  %s" % error)

def FixedMap(style, option):
    # Returns the style map for 'option' with any styles starting with
    # ("!disabled", "!selected", ...) filtered out

    # style.map() returns an empty list for missing options, so this should
    # be future-safe
    return [elm for elm in style.map("Treeview", query_opt=option)
            if elm[:2] != ("!disabled", "!selected")]
    
def NavigateFileLocation(os_type):
    file_location = ""
    try:
        computer_root = os.path.abspath(os.sep);
        
        for root, dirs, files in os.walk(computer_root):
            for path in root:
                try:
                    user_directory = path + "Users/"
                    for directories in os.walk(user_directory):
                        users = directories[1]
                        
                        for user in users:
                            file_path = user_directory + user + os_log_dict[os_type]
                            
                            print("File Path: %s" % file_path)
                            try:
                                if os.path.exists(file_path):
                                    file_location = file_path
                            except Exception as error:
                                print(error)
                        break
                    
                except Exception as error:
                    print (error)
            break
    except Exception as error:
        print("NavigateFileLocation Error: %s" % error)
    print(file_location)
    return file_location
    
def ReadConfig():
    hotkey_enabled = False
    themes_enabled = False
    images_enabled = False
    table_width = 270
    try:
        with open("config.json", 'r') as config:
            config_json = config.read()
            config_data = json.loads(config_json)
        hotkey_enabled = config_data["features"]["hotkey_enabled"]
        #themes_enabled = config_data["features"]["themes_enabled"]
        images_enabled = config_data["features"]["images_enabled"]
        table_width = int(config_data["settings"]["table_width"])
    except Exception as error:
        print("ReadConfig Error: %s" % error)
    return hotkey_enabled, themes_enabled, images_enabled, table_width

def ResetConfig():
    config = {}
    
    try:
        config["features"] = {}
        config["features"]["hotkey_enabled"] = False
        config["features"]["images_enabled"] = True
        
        config["settings"] = {}
        config["settings"]["table_width"] = 270
        
        config["card_logic"] = {}
        config["card_logic"]["minimum_creatures"] = 13
        config["card_logic"]["minimum_noncreatures"] = 6
        config["card_logic"]["ratings_threshold"] = 500
        config["card_logic"]["deck_types"] = {}
        config["card_logic"]["deck_types"]["Mid"] = {}
        config["card_logic"]["deck_types"]["Mid"] = {"distribution" : [0,0,4,3,2,1,0], "maximum_card_count" : 23, "recommended_creature_count" : 15, "cmc_average" : 3.04}
        config["card_logic"]["deck_types"]["Aggro"] = {}
        config["card_logic"]["deck_types"]["Aggro"] = {"distribution" : [0,1,4,5,2,1,0], "maximum_card_count" : 24, "recommended_creature_count" : 17, "cmc_average" : 2.40}
        config["card_logic"]["deck_types"]["Control"] = {}
        config["card_logic"]["deck_types"]["Control"] = {"distribution" : [0,0,3,3,3,1,1], "maximum_card_count" : 22, "recommended_creature_count" : 14, "cmc_average" : 3.68}
    
        with open('config.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)
    except Exception as error:
        print("ResetConfig Error: %s" % error)


def CopySuggested(deck_colors, deck, set_data, color_options, set):
    colors = color_options[deck_colors.get()]
    deck_string = ""
    try:
        deck_string = CL.CopyDeck(deck[colors]["deck_cards"],deck[colors]["sideboard_cards"],set_data["card_ratings"], set)
        CopyClipboard(deck_string)
    except Exception as error:
        print("CopySuggested Error: %s" % error)
    return 
    
def CopyTaken(taken_cards, set_data, set, color):
    deck_string = ""
    try:
        stacked_cards = CL.StackCards(taken_cards, color)
        deck_string = CL.CopyDeck(stacked_cards, None, set_data["card_ratings"], set)
        CopyClipboard(deck_string)

    except Exception as error:
        print("CopyTaken Error: %s" % error)
    return 
    
def CopyClipboard(copy):
    try:
        #Attempt to copy to clipboard
        clip = Tk()
        clip.withdraw()
        clip.clipboard_clear()
        clip.clipboard_append(copy)
        clip.update()
        clip.destroy()
    except Exception as error:
        print("CopyClipboard Error: %s" % error)
    return 

class LogScanner:
    def __init__(self,log_file, step_through, diag_log_enabled, os):
        self.os = os
        self.log_file = log_file
        self.step_through = step_through
        self.diag_log_file = "DraftLog_%s.log" % (str(time.time()))
        self.diag_log_enabled = diag_log_enabled
        self.set_data = None
        self.deck_colors = {}
        self.deck_limits = {}
        self.draft_type = DRAFT_TYPE_UNKNOWN
        self.pick_offset = 0
        self.pack_offset = 0
        self.search_offset = 0
        self.draft_set = None
        self.current_pick = 0
        self.picked_cards = [[] for i in range(8)]
        self.taken_cards = []
        self.pack_cards = [None] * 8
        self.initial_pack = [None] * 8
        self.current_pack = 0
        self.previous_picked_pack = 0
        self.current_picked_pick = 0
        
    def ClearDraft(self, full_clear):
        if full_clear:
            self.search_offset = 0
            
        self.set_data = None
        self.deck_colors = {}
        self.deck_limits = {}
        self.draft_type = DRAFT_TYPE_UNKNOWN
        self.pick_offset = 0
        self.pack_offset = 0
        self.draft_set = None
        self.current_pick = 0
        self.picked_cards = [[] for i in range(8)]
        self.taken_cards = []
        self.pack_cards = [None] * 8
        self.initial_pack = [None] * 8
        self.current_pack = 0
        self.previous_picked_pack = 0
        self.current_picked_pick = 0

    def DraftStartSearch(self):   
        offset = self.search_offset
        #Open the file
        print("DraftStartSearch: %u" % offset)
        switcher={
                "[UnityCrossThreadLogger]==> Event_Join " : (lambda x, y: self.DraftStartSearchV1(x, y)),
                "[UnityCrossThreadLogger]==> Event.Join " : (lambda x, y: self.DraftStartSearchV2(x, y)),
                "[UnityCrossThreadLogger]==> BotDraft_DraftStatus " : (lambda x, y: self.DraftStartSearchV1(x, y)),
             }
        
        
        try:
            with open(self.log_file, 'r', errors="ignore") as log:
                log.seek(offset)
                for line in log:
                    offset += len(line)
                    
                    for search_string in switcher.keys():
                        string_offset = line.find(search_string)
                        if string_offset != -1:
                            self.search_offset = offset
                            print("Draft found at %u" % offset)
                            start_parser = switcher.get(search_string, lambda: None)
                            event_data = json.loads(line[string_offset + len(search_string):])
                            start_parser(event_data, offset)
                            LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                            break
                                
            if self.draft_type != DRAFT_TYPE_UNKNOWN:
                self.RetrieveSet()

        except Exception as error:
            print("DraftStartSearch Error: %s" % error)
            
    
    def DraftStartSearchV1(self, event_data, offset):
        try:
            request_data = json.loads(event_data["request"])
            payload_data = json.loads(request_data["Payload"])
            event_name = payload_data["EventName"]
            
            event_string = event_name.split('_')
            
            if len(event_string) > 1:

                for count, event in enumerate(event_string):
                    if event in draft_types_dict.keys():
                        event_type = event
                        if count == 0:
                            event_set = event_string[count + 1]
                        else:
                            event_set = event_string[count - 1]
                        
                
                        self.draft_type = draft_types_dict[event_type]
                        self.draft_set = event_set
                        self.pick_offset = offset 
                        self.pack_offset = offset
                        self.diag_log_file = "DraftLog_%s_%s_%u.log" % (event_set, event_type, int(time.time()))
                        break
        except Exception as error:
            print("DraftStartSearchV1 Error: %s" % error)
            
    
    def DraftStartSearchV2(self, event_data, offset):
        try:
            request_data = json.loads(event_data["request"])
            params_data = request_data["params"]
            event_name = params_data["eventName"]
            
            event_string = event_name.split('_')
            
            if len(event_string) > 1:
                event_type = event_string[0]
                event_set = event_string[1]
                
                if event_type in draft_types_dict.keys():
                    self.draft_type = draft_types_dict[event_type]
                    self.draft_set = event_set
                    self.pick_offset = offset 
                    self.pack_offset = offset
                    self.diag_log_file = "DraftLog_%s_%s_%u.log" % (event_set, event_type, int(time.time()))
                    #LogEntry(self.diag_log_file, event_data, self.diag_log_enabled)
                                
        except Exception as error:
            print("DraftStartSearchV2 Error: %s" % error)
            
    #Wrapper function for performing a search based on the draft type
    def DraftSearch(self):
        print("Draft Search")
        if self.draft_set == None:
            self.ClearDraft(False)
            self.DraftStartSearch()
        
        if self.draft_type == DRAFT_TYPE_PREMIER_V1:
            self.DraftPackSearchPremierV1()
            self.DraftPickedSearchPremierV1()
        elif self.draft_type == DRAFT_TYPE_PREMIER_V2:
            self.DraftPackSearchPremierV2()
            self.DraftPickedSearchPremierV2()  
        elif self.draft_type == DRAFT_TYPE_QUICK:
            self.DraftPackSearchQuick()
            self.DraftPickedSearchQuick()
            
        return
    def DraftPickedSearchPremierV1(self):
        offset = self.pick_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick "
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.log_file, 'r') as log:
                log.seek(offset)

                for line in log:
                    offset += len(line)
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pick_offset = offset
                        start_offset = line.find("{\"id\"")
                        LogEntry(self.diag_log_file, line, self.diag_log_enabled)

                        try:
                            #Identify the pack
                            draft_data = json.loads(line[start_offset:])
                            
                            request_data = json.loads(draft_data["request"])
                            param_data = json.loads(request_data["Payload"])
                            
                            pack = int(param_data["Pack"])
                            pick = int(param_data["Pick"])
                            card = str(param_data["GrpId"])
                            
                            pack_index = (pick - 1) % 8
                            
                            if self.previous_picked_pack != pack:
                                self.picked_cards = [[] for i in range(8)]
                            
                            self.picked_cards[pack_index].append(self.set_data["card_ratings"][card]["name"])
                            self.taken_cards.append(self.set_data["card_ratings"][card])
                            
                            self.previous_picked_pack = pack
                            self.current_picked_pick = pick
                            
                            if self.step_through:
                                break; 
                            
                        except Exception as error:
                            error_string = "DraftPickedSearchPremierV1 Error: %s" % error
                            print(error_string)
                            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)         
        except Exception as error:
            error_string = "DraftPickedSearchPremierV1 Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)

        
    def DraftPackSearchPremierV1(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]Draft.Notify "
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.log_file, 'r') as log:
                log.seek(offset)

                for line in log:
                    offset += len(line)
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pack_offset = offset
                        start_offset = line.find("{\"draftId\"")
                        LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                        pack_cards = []
                        #Identify the pack
                        draft_data = json.loads(line[start_offset:])
                        parsed_cards = []
                        try:
                                
                            cards = draft_data["PackCards"].split(',') 
                                
                            for count, card in enumerate(cards):
                                if card in self.set_data["card_ratings"].keys():
                                    if len(self.set_data["card_ratings"][card]):
                                        parsed_cards.append(self.set_data["card_ratings"][card]["name"])
                                        pack_cards.append(self.set_data["card_ratings"][card])
                                        pack = draft_data["SelfPack"]
                                        pick = draft_data["SelfPick"]
                                
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [None] * 8
                        
                            if self.initial_pack[pack_index] == None:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                            
                            self.current_pack = pack
                            self.current_pick = pick
                            
                            if(self.step_through):
                                break
    
                        except Exception as error:
                            error_string = "DraftPackSearchPremierV1 Sub Error: %s" % error
                            print(error_string)
                            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
                        print("Pack: %u, Pick: %u, Cards: %s" % (draft_data["SelfPack"], draft_data["SelfPick"], parsed_cards))
             
        except Exception as error:
            error_string = "DraftPackSearchPremierV1 Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        return pack_cards
        
    def DraftPackSearchPremierV2(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]Draft.Notify "
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.log_file, 'r') as log:
                log.seek(offset)

                for line in log:
                    offset += len(line)
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pack_offset = offset
                        LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                        pack_cards = []
                        #Identify the pack
                        draft_data = json.loads(line[len(draft_string):])
                        parsed_cards = []
                        try:

                            cards = draft_data["PackCards"].split(',') 
                                
                            for count, card in enumerate(cards):
                                if card in self.set_data["card_ratings"].keys():
                                    if len(self.set_data["card_ratings"][card]):
                                        parsed_cards.append(self.set_data["card_ratings"][card]["name"])
                                        pack_cards.append(self.set_data["card_ratings"][card])
                                        pack = draft_data["SelfPack"]
                                        pick = draft_data["SelfPick"]
                                
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [None] * 8
                        
                            if self.initial_pack[pack_index] == None:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                            
                            self.current_pack = pack
                            self.current_pick = pick
                            
                            if(self.step_through):
                                break
    
                        except Exception as error:
                            error_string = "DraftPackSearchPremierV2 Sub Error: %s" % error
                            print(error_string)
                            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
                        print("Pack: %u, Pick: %u, Cards: %s" % (draft_data["SelfPack"], draft_data["SelfPick"], parsed_cards))
             
        except Exception as error:
            error_string = "DraftPackSearchPremierV2 Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        return pack_cards

    
    def DraftPickedSearchPremierV2(self):
        offset = self.pick_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]==> Draft.MakeHumanDraftPick "
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.log_file, 'r') as log:
                log.seek(offset)

                for line in log:
                    offset += len(line)
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        #print(line)
                        LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                        self.pick_offset = offset
                        try:
                            #Identify the pack
                            draft_data = json.loads(line[len(draft_string):])
                            
                            request_data = json.loads(draft_data["request"])
                            param_data = request_data["params"]
                            
                            pack = int(param_data["packNumber"])
                            pick = int(param_data["pickNumber"])
                            card = param_data["cardId"]
                            
                            pack_index = (pick - 1) % 8
                            
                            if self.previous_picked_pack != pack:
                                self.picked_cards = [[] for i in range(8)]
                                 
                            self.picked_cards[pack_index].append(self.set_data["card_ratings"][card]["name"])
                            self.taken_cards.append(self.set_data["card_ratings"][card])
                            
                            self.previous_picked_pack = pack
                            self.current_picked_pick = pick
    
                            print("Picked - Pack: %u, Pick: %u, Cards: %s" % (pack, pick, self.picked_cards[pack_index]))
                            
                            if self.step_through:
                                break; 
                            
                        except Exception as error:
                            error_string = "DraftPickedSearchPremierV2 Error: %s" % error
                            print(error_string)
                            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
          
        except Exception as error:
            error_string = "DraftPickedSearchPremierV2 Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
    
    def DraftPackSearchQuick(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "DraftPack"
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.log_file, 'r') as log:
                log.seek(offset)

                for line in log:
                    offset += len(line)
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        #Remove any prefix (e.g. log timestamp)
                        start_offset = line.find("{\"CurrentModule\"")                       
                        LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                        draft_data = json.loads(line[start_offset:])
                        payload_data = json.loads(draft_data["Payload"])
                        pack_data = payload_data["DraftPack"]
                        draft_status = payload_data["DraftStatus"]
                        
                        if draft_status == "PickNext":
                            self.pack_offset = offset
                            pack_cards = []
                            parsed_cards = []
                            try:

                                cards = pack_data
                                
                                for count, card in enumerate(cards):
                                    if card in self.set_data["card_ratings"].keys():
                                        if len(self.set_data["card_ratings"][card]):
                                            parsed_cards.append(self.set_data["card_ratings"][card]["name"])
                                            pack_cards.append(self.set_data["card_ratings"][card])
                                            pack = payload_data["PackNumber"] + 1
                                            pick = payload_data["PickNumber"] + 1
                                    
                                pack_index = (pick - 1) % 8
                                
                                if self.current_pack != pack:
                                    self.initial_pack = [None] * 8
                            
                                if self.initial_pack[pack_index] == None:
                                    self.initial_pack[pack_index] = pack_cards
                                    
                                self.pack_cards[pack_index] = pack_cards
                                    
                                self.current_pack = pack
                                self.current_pick = pick
                                
                                if(self.step_through):
                                    break
        
                            except Exception as error:
                                error_string = "DraftPackSearchQuick Sub Error: %s" % error
                                print(error_string)
                                LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
                            print("Pack: %u, Pick: %u, Cards: %s" % (pack, pick, parsed_cards))
            if log.closed == False:
                log.close() 
        except Exception as error:
            error_string = "DraftPackSearchQuick Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string)
        
        return pack_cards
        
    def DraftPickedSearchQuick(self):
        offset = self.pick_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]==> BotDraft_DraftPick "
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.log_file, 'r') as log:
                log.seek(offset)

                for line in log:
                    offset += len(line)
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                        self.pick_offset = offset
                        try:
                            #Identify the pack
                            draft_data = json.loads(line[string_offset+len(draft_string):])
                            
                            request_data = json.loads(draft_data["request"])
                            payload_data = json.loads(request_data["Payload"])
                            print("payload_data: %s" % str(payload_data))
                            pick_data = payload_data["PickInfo"]
                            print("pick_data: %s" % str(pick_data))
                            
                            pack = pick_data["PackNumber"] + 1
                            pick = pick_data["PickNumber"] + 1
                            card = pick_data["CardId"]
                            
                            pack_index = (pick - 1) % 8
                            
                            if self.previous_picked_pack != pack:
                                self.picked_cards = [[] for i in range(8)]
                                 
                            self.previous_picked_pack = pack
                            self.current_picked_pick = pick
                            
                            self.picked_cards[pack_index].append(self.set_data["card_ratings"][card]["name"])
                            self.taken_cards.append(self.set_data["card_ratings"][card])
    
                            print("Picked - Pack: %u, Pick: %u, Cards: %s, offset: %u" % (pack, pick, self.picked_cards[pack_index], self.pack_offset))
                            
                            if self.step_through:
                                break;
                            
                        except Exception as error:
                            error_string = "DraftPickedSearchQuick Sub Error: %s" % error
                            print(error_string)
                            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            if log.closed == False:
                log.close()      
        except Exception as error:
            error_string = "DraftPickedSearchQuick Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string)
    def RetrieveSet(self):
        file_location = ''
        self.deck_colors = {"All Decks" : "","Auto" : "", "AI" : "", "W" : "","U" : "","B" : "","R" : "","G" : "","WU" : "","WB" : "","WR" : "","WG" : "","UB" : "","UR" : "","UG" : "","BR" : "","BG" : "","RG" : "","WUB" : "","WUR" : "","WUG" : "","WBR" : "","WBG" : "","WRG" : "","UBR" : "","UBG" : "","URG" : "","BRG" : ""}

        draft_string = [x for x in draft_types_dict.keys() if draft_types_dict[x] == self.draft_type]
        draft_string.extend(list(draft_types_dict.keys()))
        self.set_data = None
        try:
            
            for type in draft_string:
                root = os.getcwd()
                for files in os.listdir(root):
                    filename = self.draft_set + "_" + type + "_Data.json"
                    if filename == files:
                        file_location = os.path.join(root, filename)
                        print("File Found: %s" % file_location)
                        break                    
                if len(file_location):
                    break
                    
            if len(file_location):
                with open(file_location, 'r') as json_file:
                    json_data = json_file.read()
                json_file.close()
                self.set_data = json.loads(json_data)
                try:
                    #Identify the upper and lower limits of the gihwr for each set color combination
                    for color in self.deck_colors.keys():
                        upper_limit, lower_limit = CL.DeckColorLimits(self.set_data["card_ratings"], color)
                        self.deck_limits[color] = {"upper" : upper_limit, "lower" : lower_limit}
                    #Identify the win percentages for the deck colors
                    for colors in self.set_data["color_ratings"].keys():
                        for deck_color in self.deck_colors.keys():
                            if (len(deck_color) == len(colors)) and set(deck_color).issubset(colors):
                                ratings_string = deck_color + " (%s%%)" % (self.set_data["color_ratings"][colors])
                                self.deck_colors[deck_color] = ratings_string
                            elif self.deck_colors[deck_color] == "":
                                self.deck_colors[deck_color] = deck_color
                    print("deck_colors: %s" % str(self.deck_colors))
                except Exception as error:
                    print("RetrieveSet Sub Error: %s" % error)
                    for deck_color in self.deck_colors.keys():
                        self.deck_colors[deck_color] = deck_color
                    
        except Exception as error:
            print("RetrieveSet Error: %s" % error)   
        return
        
class WindowUI:
    def __init__(self, root, filename, step_through, diag_log_enabled, os, themes, images, table_width):
        self.root = root
        
        self.images_enabled = images
        if themes:
            self.root.tk.call("source", "sun-valley.tcl")
            self.root.tk.call("set_theme", "dark")
            
        self.filename = filename
        self.step_through = step_through
        self.diag_log_enabled = diag_log_enabled
        self.os = os
        self.draft = LogScanner(self.filename, self.step_through, self.diag_log_enabled, self.os)
        self.diag_log_file = self.draft.diag_log_file
        self.diag_log_enabled = self.draft.diag_log_enabled
        self.table_width = table_width
        
        Grid.rowconfigure(self.root, 8, weight = 1)
        Grid.columnconfigure(self.root, 0, weight = 1)
        
        #Menu Bar
        self.menubar = Menu(self.root)
        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open", command=self.FileOpen)
        self.datamenu = Menu(self.menubar, tearoff=0)
        self.datamenu.add_command(label="View Sets", command=self.SetViewPopup)
        
        log_value_string = "Disable Log" if self.diag_log_enabled else "Enable Log"

        self.datamenu.add_command(label=log_value_string, command=self.ToggleLog)
        self.datamenu.add_command(label="Reset Config", command=ResetConfig)
        self.cardmenu = Menu(self.menubar, tearoff=0)
        self.cardmenu.add_command(label="Taken Cards", command=self.TakenCardsPopup)
        self.cardmenu.add_command(label="Suggest Decks", command=self.SuggestDeckPopup)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.menubar.add_cascade(label="Data", menu=self.datamenu)
        self.menubar.add_cascade(label="Cards", menu=self.cardmenu)
        self.root.config(menu=self.menubar)
        
        style = Style()
        style.map("Treeview", 
                foreground=FixedMap(style, "foreground"),
                background=FixedMap(style, "background"))
                
        self.current_draft_frame = Frame(self.root)
        self.current_draft_label = Label(self.current_draft_frame, text="Current Draft:", font='Helvetica 9 bold', anchor="e", width = 15)
        
        self.current_draft_value_label = Label(self.current_draft_frame, text="", font='Helvetica 9', anchor="w", width=15)
        
        self.deck_colors_frame = Frame(self.root)
        self.deck_colors_label = Label(self.deck_colors_frame, text="Deck Filter:", font='Helvetica 9 bold', anchor="e", width = 15)
        
        self.deck_colors_options_selection = StringVar(self.root)
        self.deck_colors_options_list = []
        
        optionsStyle = Style()
        optionsStyle.configure('my.TMenubutton', font=('Helvetica', 9))
        
        self.deck_colors_options = OptionMenu(self.deck_colors_frame, self.deck_colors_options_selection, *self.deck_colors_options_list, style="my.TMenubutton")
        self.deck_colors_options.config(width=11)
        
        self.refresh_button_frame = Frame(self.root)
        self.refresh_button = Button(self.refresh_button_frame, command=self.UpdateCallback, text="Refresh");
        
        self.status_frame = Frame(self.root)
        self.pack_pick_label = Label(self.status_frame, text="Pack: 0, Pick: 0", font='Helvetica 9 bold')
        
        self.pack_table_frame = Frame(self.root, width=10)

        headers = {"Card"   : {"width" : .55, "anchor" : W},
                  "Color"   : {"width" : .15, "anchor" : CENTER},
                  "All"     : {"width" : .15, "anchor" : CENTER},
                  "Filter"  : {"width" : .15, "anchor" : CENTER}}
        self.pack_table = self.CreateHeader(self.pack_table_frame, 0, headers, self.table_width)
        
        self.missing_frame = Frame(self.root)
        self.missing_cards_label = Label(self.missing_frame, text = "Missing Cards", font='Helvetica 9 bold')
       
        self.missing_table_frame = Frame(self.root, width=10)

        self.missing_table = self.CreateHeader(self.missing_table_frame, 0, headers, self.table_width)
        
        self.stat_frame = Frame(self.root)
        stat_header = {"Colors"   : {"width" : .19, "anchor" : W},
                       "1"        : {"width" : .11, "anchor" : CENTER},
                       "2"        : {"width" : .11, "anchor" : CENTER},
                       "3"        : {"width" : .11, "anchor" : CENTER},
                       "4"        : {"width" : .11, "anchor" : CENTER},
                       "5"        : {"width" : .11, "anchor" : CENTER},
                       "6+"       : {"width" : .11, "anchor" : CENTER},
                       "Total"    : {"width" : .15, "anchor" : CENTER}}
        self.stat_table = self.CreateHeader(self.root, 0, stat_header, self.table_width)
        self.stat_label = Label(self.stat_frame, text = "Deck Stats:", font='Helvetica 9 bold', anchor="e", width = 15)

        self.stat_options_selection = StringVar(self.root)
        self.stat_options_list = ["Creatures","Noncreatures","All"]
        self.stat_options_selection.trace("w", self.UpdateDeckStatsCallback)
        
        self.stat_options = OptionMenu(self.stat_frame, self.stat_options_selection, self.stat_options_list[0], *self.stat_options_list, style="my.TMenubutton")
        self.stat_options.config(width=11) 
        
        self.current_draft_frame.grid(row = 0, column = 0, columnspan = 1)
        self.deck_colors_frame.grid(row = 1, column = 0, columnspan = 1)
        self.refresh_button_frame.grid(row = 2, column = 0, columnspan = 1, stick = 'nsew')
        self.status_frame.grid(row = 3, column = 0, columnspan = 1, sticky = 'nsew')
        self.pack_table_frame.grid(row = 4, column = 0, columnspan = 1, sticky = 'nsew')
        self.missing_frame.grid(row = 5, column = 0, columnspan = 1, sticky = 'nsew')
        self.missing_table_frame.grid(row = 6, column = 0, columnspan = 1, sticky = 'nsew')
        self.stat_frame.grid(row=7, column = 0, columnspan = 1, sticky = 'nsew') 
        self.stat_table.grid(row=8, column = 0, columnspan = 1, sticky = 'nsew')
        
        self.current_draft_label.pack(side=LEFT, expand = True, fill = None)
        self.current_draft_value_label.pack(side=RIGHT,expand = True, fill = None)
        self.deck_colors_label.pack(side=LEFT,expand = True, fill = None)
        self.deck_colors_options.pack(side=RIGHT,expand = True, fill = None)
        self.refresh_button.pack(expand = True, fill = "both")
        self.pack_pick_label.pack(expand = False, fill = None)
        self.pack_table.pack(expand = True, fill = 'both')
        self.missing_cards_label.pack(expand = False, fill = None)
        self.missing_table.pack(expand = True, fill = 'both')
        self.stat_label.pack(side=LEFT, expand = True, fill = None)
        self.stat_options.pack(side=RIGHT, expand = True, fill = None)
        
        #self.draft.DraftSearch()
        self.check_timestamp = 0
        self.previous_timestamp = 0
        
        self.UpdateUI()
        
        self.deck_colors_options_selection.trace("w", self.UpdateCallback)
        self.root.attributes("-topmost", True)

        
    def CreateHeader(self, frame, height, headers, total_width):
        header_labels = tuple(headers.keys())
        list_box = Treeview(frame, columns = header_labels, show = 'headings')
        list_box.config(height=height)
        style = Style() 
        style.configure("Treeview.Heading", font=("Arial", 8))
        try:
            list_box.tag_configure("darkgrey", background="#808080")
            list_box.tag_configure("custombold", font=("Arial Bold", 8))
            list_box.tag_configure("customfont", font=("Arial", 8))
            list_box.tag_configure("whitecard", font=("Arial", 8, "bold"), background = "#FFFFFF", foreground = "#000000")
            list_box.tag_configure("redcard", font=("Arial", 8, "bold"), background = "#FF6C6C", foreground = "#000000")
            list_box.tag_configure("bluecard", font=("Arial", 8, "bold"), background = "#6078F3", foreground = "#000000")
            list_box.tag_configure("blackcard", font=("Arial", 8, "bold"), background = "#BFBFBF", foreground = "#000000")
            list_box.tag_configure("greencard", font=("Arial", 8, "bold"), background = "#60DC68", foreground = "#000000")
            list_box.tag_configure("goldcard", font=("Arial", 8, "bold"), background = "#F0E657", foreground = "#000000")
            for count, column in enumerate(header_labels):
                list_box.column(column, stretch = NO, anchor = headers[column]["anchor"], width = int(headers[column]["width"] * total_width))
                list_box.heading(column, text = column, anchor = CENTER)
            list_box["show"] = "headings"  # use after setting column's size
        except Exception as error:
            error_string = "CreateHeader Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        return list_box
        
    def UpdatePackTable(self, card_list, taken_cards, filtered_color, color_options, limits):
        try:
            filtered_list = CL.CardFilter(card_list,
                                          taken_cards,
                                          filtered_color,
                                          color_options,
                                          limits)
            filtered_list.sort(key=lambda x : x["rating_filter"], reverse = True)
            # clear the previous rows
            for row in self.pack_table.get_children():
                self.pack_table.delete(row)
            self.root.update()
            
            list_length = len(filtered_list)
            
            if list_length:
                self.pack_table.config(height = list_length)
            else:
                self.pack_table.config(height=1)
                
            #Update the filtered column header with the filtered colors
            if filtered_color == "All Decks":
                self.pack_table.heading("Filter", text = "All")
            else:
                self.pack_table.heading("Filter", text = filtered_color)
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                
                self.pack_table.insert("",index = count, iid = count, values = (card["name"], card["colors"], card["rating_all"], card["rating_filter"]), tag = (row_tag,))
            self.pack_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.pack_table, card_list=card_list, selected_color=filtered_color))
        except Exception as error:
            error_string = "UpdatePackTable Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateMissingTable(self, current_pack, previous_pack, picked_cards, taken_cards, filtered_color, color_options, limits):
        try:
            for row in self.missing_table.get_children():
                self.missing_table.delete(row)
            self.root.update()
            
            if previous_pack != None:
                missing_cards = [x for x in previous_pack if x not in current_pack]
                
                list_length = len(missing_cards)
                
                if list_length:
                    self.missing_table.config(height = list_length)
                else:
                    self.missing_table.config(height=1)
                    
                #Update the filtered column header with the filtered colors
                if filtered_color == "All Decks":
                    self.missing_table.heading("Filter", text = "All")
                else:
                    self.missing_table.heading("Filter", text = filtered_color)
                
                if list_length:
                    filtered_list = CL.CardFilter(missing_cards,
                                                  taken_cards,
                                                  filtered_color,
                                                  color_options,
                                                  limits)
                    
                    filtered_list.sort(key=lambda x : x["rating_filter"], reverse = True)
                    
                    for count, card in enumerate(filtered_list):
                        row_tag = CL.RowColorTag(card["colors"])
                        card_name = "*" + card["name"] if card["name"] in picked_cards else card["name"]
                        
                        self.missing_table.insert("",index = count, iid = count, values = (card_name, card["colors"], card["rating_all"], card["rating_filter"]), tag = (row_tag,))
                    self.missing_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.missing_table, card_list=missing_cards, selected_color=filtered_color))
        except Exception as error:
            error_string = "UpdateMissingTable Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateTakenTable(self, taken_table, taken_cards, filtered_color, color_options,limits):
        try:
            
            filtered_list = CL.CardFilter(taken_cards,
                                          taken_cards,
                                          filtered_color,
                                          color_options,
                                          limits)
                    
            filtered_list.sort(key=lambda x : x["rating_filter"], reverse = True)
            
            list_length = len(filtered_list)
            
            
            #Update the filtered column header with the filtered colors
            if filtered_color == "All Decks":
                taken_table.heading("Filter", text = "All")
            else:
                taken_table.heading("Filter", text = filtered_color)
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                taken_table.insert("",index = count, iid = count, values = (card["name"], card["colors"], card["rating_all"], card["rating_filter"]), tag = (row_tag,))
            taken_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=taken_table, card_list=taken_cards, selected_color=filtered_color))
        except Exception as error:
            error_string = "UpdateTakenTable Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateSuggestDeckTable(self, suggest_table, selected_color, suggested_decks, color_options):
        try:             
            color = color_options[selected_color.get()]
            suggested_deck = suggested_decks[color]["deck_cards"]
            suggested_deck.sort(key=lambda x : x["cmc"], reverse = False)
            for row in suggest_table.get_children():
                suggest_table.delete(row)
            
            for count, card in enumerate(suggested_deck):
                row_tag = CL.RowColorTag(card["colors"])
                suggest_table.insert("",index = count, values = (card["name"],
                                                                 "%d" % card["count"],
                                                                 card["colors"],
                                                                 card["cmc"],
                                                                 card["types"]), tag = (row_tag,))
            suggest_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=suggest_table, card_list=suggested_deck, selected_color=color))
    
        except Exception as error:
            error_string = "UpdateSuggestTable Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateDeckStatsTable(self, taken_cards, filter_type):
        try:             
            filter = []
            if filter_type == "Creatures":
                filter = ["Creature", "Planeswalker"]
            elif filter_type == "Noncreatures":
                filter = ["Instant", "Sorcery","Enchantment","Artifact"]
            else:
                filter = ["Creature", "Planeswalker","Instant", "Sorcery","Enchantment","Artifact"]

            colors = {"Black":"B","Blue":"U", "Green":"G", "Red":"R", "White":"W", "NC":""}
            colors_filtered = {}
            for color,symbol in colors.items():
                if symbol == "":
                    card_colors_sorted = CL.DeckColorSearch(taken_cards, symbol, filter, True, True, False)               
                else:
                    card_colors_sorted = CL.DeckColorSearch(taken_cards, symbol, filter, True, False, True)
                cmc_total, total, distribution = CL.ColorCmc(card_colors_sorted)
                colors_filtered[color] = {}
                colors_filtered[color]["symbol"] = symbol
                colors_filtered[color]["total"] = total
                colors_filtered[color]["distribution"] = distribution
            
            #Sort list by total
            colors_filtered = dict(sorted(colors_filtered.items(), key = lambda item: item[1]["total"], reverse = True))
            
            for row in self.stat_table.get_children():
                self.stat_table.delete(row)

            list_length = len(colors_filtered)
            if list_length:
                self.stat_table.config(height = list_length)
            else:
                self.stat_table.config(height=1)
            
            print(colors_filtered)
            count = 0
            for color,values in colors_filtered.items():
                row_tag = CL.RowColorTag(values["symbol"])
                self.stat_table.insert("",index = count, values = (color,
                                                                    values["distribution"][1],
                                                                    values["distribution"][2],
                                                                    values["distribution"][3],
                                                                    values["distribution"][4],
                                                                    values["distribution"][5],
                                                                    values["distribution"][6],
                                                                    values["total"]), tag = (row_tag,))
                count += 1
        except Exception as error:
            error_string = "UpdateDeckStats Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdatePackPick(self, pack, pick):
        try:
            new_label = "Pack: %u, Pick: %u" % (pack, pick)
            self.pack_pick_label.config(text = new_label)
        
        except Exception as error:
            error_string = "UpdatePackPick Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)   
     
    def UpdateCurrentDraft(self, set, draft_type):
        try: 
            draft_type_string = ''
            
            for key, value in draft_types_dict.items():
                if draft_types_dict[key] == draft_type:
                    draft_type_string = key
                    
            new_label = "%s %s" % (set, draft_type_string)
            self.current_draft_value_label.config(text = new_label)
        
        except Exception as error:
            error_string = "UpdateCurrentDraft Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateOptions(self, options_list):
        try: 
            
            menu = self.deck_colors_options["menu"]
            menu.delete(0, "end")
            self.deck_colors_options_list = []
            
            for key, data in options_list.items():
                if len(data):
                    menu.add_command(label=data, 
                                    command=lambda value=data: self.deck_colors_options_selection.set(value))
                    self.deck_colors_options_list.append(data)
                    
            if len(self.deck_colors_options_list):        
                selected_option = "Auto"
                
                self.deck_colors_options_selection.set(options_list[selected_option])
                print("deck_colors_options_list: %s" % str(self.deck_colors_options_list))
                print("selected color %s,%s" % (options_list[selected_option], self.deck_colors_options_selection.get()))
        except Exception as error:
            error_string = "UpdateOptions Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateCallback(self, *args):
        self.draft.DraftSearch()
        
        if len(self.deck_colors_options_list) == 0:
            self.UpdateOptions(self.draft.deck_colors)
                
        filtered_color = CL.ColorFilter(self.draft.taken_cards, self.deck_colors_options_selection.get(), self.draft.deck_colors)

        self.UpdateCurrentDraft(self.draft.draft_set, self.draft.draft_type)
        self.UpdatePackPick(self.draft.current_pack, self.draft.current_pick)
        pack_index = (self.draft.current_pick - 1) % 8
        self.UpdatePackTable(self.draft.pack_cards[pack_index], 
                             self.draft.taken_cards,
                             filtered_color,
                             self.draft.deck_colors,
                             self.draft.deck_limits)
        self.UpdateMissingTable(self.draft.pack_cards[pack_index],
                                self.draft.initial_pack[pack_index],
                                self.draft.picked_cards[pack_index],
                                self.draft.taken_cards,
                                filtered_color,
                                self.draft.deck_colors,
                                self.draft.deck_limits)   
                                
        self.UpdateDeckStatsCallback()

    def UpdateDeckStatsCallback(self, *args):
        self.UpdateDeckStatsTable(self.draft.taken_cards, self.stat_options_selection.get())

    def UpdateUI(self):
        try:
            self.current_timestamp = os.stat(self.filename).st_mtime
            
            if self.current_timestamp != self.previous_timestamp:
                self.previous_timestamp = self.current_timestamp
                
                previous_pick = self.draft.current_pick
                previous_pack = self.draft.current_pack
                
                while(1):

                    self.UpdateCallback()
                    print("previous pick: %u, current pick: %u" % (previous_pick, self.draft.current_pick))
                    if self.draft.current_pack < previous_pack:
                        self.DraftReset(False)
                        self.UpdateCallback()
                    if self.draft.step_through and (previous_pick != self.draft.current_pick):
                        input("Continue?")
                    else:
                        print("Exiting Step Loop")
                        break
                        
                    previous_pick = self.draft.current_pick
                    previous_pack = self.draft.current_pack
        except Exception as error:
            error_string = "UpdateUI Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
        self.root.after(1000, self.UpdateUI)
        
    def WindowLift(self, root):
        if root.state()=="iconic":
            root.deiconify()
            root.lift()
            root.attributes("-topmost", True)
        else:
            root.attributes("-topmost", False)
            root.iconify()
            
    def SetViewPopup(self):
        popup = Toplevel()
        popup.wm_title("Set Data")
        
        try:
            column_headers = ('SET', 'DRAFT', 'START DATE', 'END DATE')
            list_box = Treeview(popup, columns = column_headers, show = 'headings')
            list_box.tag_configure('gray', background='#cccccc')
            list_box.tag_configure('bold', font=('Arial Bold', 10))
            
            set_label = Label(popup, text="SET:")
            draft_label = Label(popup, text="DRAFT:")
            start_label = Label(popup, text="START DATE:")
            end_label = Label(popup, text="END DATE:")
            color_label = Label(popup, text="COLOR RATING:")
            id_label = Label(popup, text="ID:")
            choices = ["QuickDraft", "PremierDraft", "TraditionalDraft"]
            
            draft_value = StringVar(self.root)
            draft_value.set('QuickDraft')
            draft_entry = OptionMenu(popup, draft_value, choices[0], *choices)
            
            set_entry = Entry(popup)
            set_entry.insert(END, 'MID')
            start_entry = Entry(popup)
            start_entry.insert(END, '2019-1-1')
            end_entry = Entry(popup)
            end_entry.insert(END, str(date.today()))
            id_entry = Entry(popup)
            id_entry.insert(END, 0)
            
            progress = Progressbar(popup,orient=HORIZONTAL,length=100,mode='determinate')
            
            color_checkbox_value = IntVar()
            color_checkbox = Checkbutton(popup,
                                         variable=color_checkbox_value,
                                         onvalue=1,
                                         offvalue=0)
            
            add_button = Button(popup, command=lambda: self.AddSet(set_entry,
                                                                   draft_value,
                                                                   start_entry,
                                                                   end_entry,
                                                                   add_button,
                                                                   progress,
                                                                   list_box,
                                                                   id_entry,
                                                                   color_checkbox_value), text="ADD SET")
            
            
            for count, column in enumerate(column_headers):
                list_box.column(column, anchor = CENTER, stretch = YES, width = 100)
                list_box.heading(column, text = column, anchor = CENTER)
        except Exception as error:
            error_string = "SetViewPopup Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        
        list_box.grid(row=0, column=0, columnspan=8, stick = 'nsew')
        set_label.grid(row=1, column=0, stick = 'nsew')
        set_entry.grid(row=1, column=1, stick = 'nsew')
        start_label.grid(row=1, column=2, stick = 'nsew')
        start_entry.grid(row=1, column=3, stick = 'nsew')
        end_label.grid(row=1, column=4, stick = 'nsew')
        end_entry.grid(row=1, column=5, stick = 'nsew')
        draft_label.grid(row=1, column=6, stick = 'nsew')
        draft_entry.grid(row=1, column=7, stick = 'nsew')
        id_label.grid(row=2, column=0, stick = 'nsew')
        id_entry.grid(row=2, column=1, stick = 'nsew')
        color_label.grid(row=2, column=2, stick = 'nsew')
        color_checkbox.grid(row=2, column=3, stick = 'nsew')
        add_button.grid(row=3, column=0, columnspan=8, stick = 'nsew')
        progress.grid(row=4, column=0, columnspan=8, stick = 'nsew')

        self.DataViewUpdate(list_box)
        
        popup.attributes("-topmost", True)
    def TakenCardsPopup(self):
        popup = Toplevel()
        popup.wm_title("Taken Cards")
        
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            
            filtered_color = CL.ColorFilter(self.draft.taken_cards, 
                                            self.deck_colors_options_selection.get(), 
                                            self.draft.deck_colors)
            
            copy_button = Button(popup, command=lambda:CopyTaken(self.draft.taken_cards,
                                                                 self.draft.set_data,
                                                                 self.draft.draft_set,
                                                                 filtered_color),
                                                                 text="Copy to Clipboard")
            
            headers = {"Card"  : {"width" : .55, "anchor" : W},
                       "Color" : {"width" : .15, "anchor" : CENTER},
                       "All"   : {"width" : .15, "anchor" : CENTER},
                       "Filter": {"width" : .15, "anchor" : CENTER}}
            taken_table_frame = Frame(popup)
            taken_scrollbar = Scrollbar(taken_table_frame, orient=VERTICAL)
            taken_scrollbar.pack(side=RIGHT, fill=Y)
            taken_table = self.CreateHeader(taken_table_frame, 20, headers, self.table_width)
            taken_table.config(yscrollcommand=taken_scrollbar.set)
            taken_scrollbar.config(command=taken_table.yview)
            
            copy_button.grid(row=0, column=0, stick="nsew")
            taken_table_frame.grid(row=1, column=0, stick = "nsew")
            taken_table.pack(expand = True, fill = "both")
            
            
            self.UpdateTakenTable(taken_table,
                                  self.draft.taken_cards,
                                  filtered_color,
                                  self.draft.deck_colors,
                                  self.draft.deck_limits)
            popup.attributes("-topmost", True)
        except Exception as error:
            error_string = "TakenCards Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def SuggestDeckPopup(self):
        popup = Toplevel()
        popup.wm_title("Suggested Decks")
        
        try:
            Grid.rowconfigure(popup, 3, weight = 1)
            
            suggested_decks = CL.SuggestDeck(self.draft.taken_cards, self.draft.deck_colors, self.draft.deck_limits)
            
            choices = ["None"]
            deck_color_options = {}
            
            if len(suggested_decks):
                choices = []
                for color in suggested_decks:
                    rating_label = "%s %s (Rating:%d)" % (color, suggested_decks[color]["type"], suggested_decks[color]["rating"])
                    deck_color_options[rating_label] = color
                    choices.append(rating_label)
                
            deck_colors_label = Label(popup, text="Deck Colors:", anchor = 'e', font='Helvetica 9 bold')
            
            deck_colors_value = StringVar(popup)
            deck_colors_entry = OptionMenu(popup, deck_colors_value, choices[0], *choices)
            
            deck_colors_button = Button(popup, command=lambda:self.UpdateSuggestDeckTable(suggest_table,
                                                                                          deck_colors_value,
                                                                                          suggested_decks,
                                                                                          deck_color_options),
                                                                                          text="Update")
            
            copy_button = Button(popup, command=lambda:CopySuggested(deck_colors_value,
                                                                     suggested_decks,
                                                                     self.draft.set_data,
                                                                     deck_color_options,
                                                                     self.draft.draft_set),
                                                                     text="Copy to Clipboard")
            
            headers = {"Card"  : {"width" : .40, "anchor" : W},
                       "Count" : {"width" : .14, "anchor" : CENTER},
                       "Color" : {"width" : .10, "anchor" : CENTER},
                       "Cost"  : {"width" : .10, "anchor" : CENTER},
                       "Type"  : {"width" : .26, "anchor" : CENTER}}
            suggest_table_frame = Frame(popup)
            suggest_scrollbar = Scrollbar(suggest_table_frame, orient=VERTICAL)
            suggest_scrollbar.pack(side=RIGHT, fill=Y)
            suggest_table = self.CreateHeader(suggest_table_frame, 20, headers, 380)
            suggest_table.config(yscrollcommand=suggest_scrollbar.set)
            suggest_scrollbar.config(command=suggest_table.yview)
            
            deck_colors_label.grid(row=0,column=0,columnspan=1,stick="nsew")
            deck_colors_entry.grid(row=0,column=1,columnspan=1,stick="nsew")
            deck_colors_button.grid(row=1,column=0,columnspan=2,stick="nsew")
            copy_button.grid(row=2,column=0,columnspan=2,stick="nsew")
            suggest_table_frame.grid(row=3, column=0, columnspan = 2, stick = 'nsew')
            
            suggest_table.pack(expand = True, fill = 'both')
            
            self.UpdateSuggestDeckTable(suggest_table, deck_colors_value, suggested_decks, deck_color_options)
            popup.attributes("-topmost", True)
        except Exception as error:
            error_string = "SuggestDeckPopup Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        
    def AddSet(self, set, draft, start, end, button, progress, list_box, id, color_rating):
        button['state'] = 'disabled'
        progress['value']=0
        self.root.update()
        DP = FE.DataPlatform(2.00, set.get(), draft.get(), start.get(), end.get(), id.get())
        if color_rating.get():
            DP.SessionColorRatings()
        DP.SessionCardData()
        progress['value']=10
        self.root.update()
        if(DP.SessionCardRating(self.root, progress, progress['value'])):
            DP.ExportData()
            progress['value']=100
        else:
            progress['value']=0
        button['state'] = 'normal'
        self.root.update()
        self.DataViewUpdate(list_box)
        
    def DataViewUpdate(self, list_box):
        #Delete the content of the list box
        for row in list_box.get_children():
                list_box.delete(row)
        self.root.update()
        for directory, directory_names, filenames in os.walk(os.getcwd()):
            for filename in filenames:
                name_segments = filename.split("_")
                if len(name_segments) == 3:
                    if name_segments[1] in draft_types_dict.keys():
                        #Retrieve the start and end dates
                        try:
                            json_data = {}
                            with open(filename, 'r') as json_file:
                                json_data = json_file.read()
                            json_data = json.loads(json_data)
                            if json_data["meta"]["version"] == 1:
                                print(json_data["meta"]["date_range"])
                                start_date, end_date = json_data["meta"]["date_range"].split("->")
                                list_box.insert("", index = 0, values = (name_segments[0], name_segments[1], start_date, end_date))
                            elif json_data["meta"]["version"] == 2:
                                start_date = json_data["meta"]["start_date"] 
                                end_date = json_data["meta"]["end_date"] 
                                list_box.insert("", index = 0, values = (name_segments[0], name_segments[1], start_date, end_date))
                        except Exception as error:
                            error_string = "DataViewUpdate Error: %s" % error
                            print(error_string)
                            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
            break
            
    def OnClickTable(self, event, table, card_list, selected_color):
        for item in table.selection():
            card_name = table.item(item, "value")[0]
            for card in card_list:
                card_name = card_name if card_name[0] != '*' else card_name[1:]
                if card_name == card["name"]:
                    try:
                        tooltip = CreateCardToolTip(table, event,
                                                           card["name"],
                                                           card["deck_colors"][selected_color]["alsa"],
                                                           card["deck_colors"][selected_color]["iwd"],
                                                           card["deck_colors"][selected_color]["gihwr"],
                                                           card["image"],
                                                           self.images_enabled,
                                                           self.os)
                    except Exception as error:
                        tooltip = CreateCardToolTip(table, event,
                                                           card["name"],
                                                           0,
                                                           0,
                                                           0,
                                                           card["image"],
                                                           self.images_enabled,
                                                           self.os)
                    break
    def FileOpen(self):
        filename = filedialog.askopenfilename(filetypes=(("Log Files", "*.log"),
                                                         ("All files", "*.*") ))
                                              
        if filename:
            self.filename = filename
            self.DraftReset(True)
            self.draft.log_file = filename
            self.UpdateCallback()
            
    def ToggleLog(self):
        
        if self.diag_log_enabled:
            log_value_string = "Enable Log"
            self.diag_log_enabled = False
        else:
            log_value_string = "Disable Log"
            self.diag_log_enabled = True 
        self.datamenu.entryconfigure(1, label=log_value_string)
        
    def DraftReset(self, full_reset):
        self.draft.ClearDraft(full_reset)
        self.deck_colors_options_list = []
    
class CreateCardToolTip(object):
    def __init__(self, widget, event, card_name, alsa, iwd, gihwr, image, images_enabled, os):
        self.waittime = 1     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.card_name = card_name
        self.alsa = alsa
        self.iwd = iwd
        self.gihwr = gihwr
        self.image = image
        self.os = os
        self.images_enabled = images_enabled
        self.widget.bind("<Leave>", self.Leave)
        self.widget.bind("<ButtonPress>", self.Leave)
        self.id = None
        self.tw = None
        self.event = event
        self.images = []
        self.Enter()
       
    def Enter(self, event=None):
        self.Schedule()

    def Leave(self, event=None):
        self.Unschedule()
        self.HideTip()

    def Schedule(self):
        self.Unschedule()
        self.id = self.widget.after(self.waittime, self.ShowTip)

    def Unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def ShowTip(self, event=None):  
        try:
            x = y = 0
            x = self.widget.winfo_pointerx() + 25
            y = self.widget.winfo_pointery() + 20
            # creates a toplevel window
            self.tw = Toplevel(self.widget)
            # Leaves only the label and removes the app window
            self.tw.wm_overrideredirect(True)
            if self.os == "MAC":
               self.tw.wm_overrideredirect(False) 
            self.tw.wm_geometry("+%d+%d" % (x, y))
   
            tt_frame = Frame(self.tw, borderwidth=5,relief="solid")
            
            #Add scryfall image
            if self.images_enabled:
                from PIL import Image, ImageTk
                size = 260, 362
                
                self.images = []
                for count, picture in enumerate(self.image):
                    raw_data = urllib.request.urlopen(picture).read()
                    im = Image.open(io.BytesIO(raw_data))
                    im.thumbnail(size, Image.ANTIALIAS)
                    image = ImageTk.PhotoImage(im)
                    image_label = Label(tt_frame, image=image)
                    columnspan = 1 if len(self.image) == 2 else 2
                    image_label.grid(column=count, row=4, columnspan=columnspan)
                    self.images.append(image)
            
            card_label = Label(tt_frame, justify="left", text=self.card_name, font=("Consolas", 12, "bold"))
            alsa_label = Label(tt_frame, justify="left", text="Average Last Seen At  :", font=("Consolas", 10, "bold"))
            alsa_value = Label(tt_frame, text=self.alsa, font=("Consolas", 10))
            iwd_label = Label(tt_frame, text="Improvement When Drawn:", font=("Consolas", 10, "bold"))
            iwd_value = Label(tt_frame, text=str(self.iwd) + "pp", font=("Consolas", 10))
            gihwr_label = Label(tt_frame, text="Games In Hand Win Rate:", font=("Consolas", 10, "bold"))
            gihwr_value = Label(tt_frame, text=str(self.gihwr) + "%", font=("Consolas", 10))
            card_label.grid(column=0, row=0, columnspan=2)
            alsa_label.grid(column=0, row=1, columnspan=1)
            alsa_value.grid(column=1, row=1, columnspan=1)
            iwd_label.grid(column=0, row=2, columnspan=1)
            iwd_value.grid(column=1, row=2, columnspan=1)
            gihwr_label.grid(column=0, row=3, columnspan=1)
            gihwr_value.grid(column=1, row=3, columnspan=1)

            tt_frame.pack()
            

            
            self.tw.attributes("-topmost", True)
        except Exception as error:
            print("Showtip Error: %s" % error)

    def HideTip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()
def Startup(argv):
    version = 2.50
    file_location = ""
    step_through = False
    diag_log_enabled = True
    os = "PC"
    try:
        opts, args = getopt.getopt(argv, "f:",["step","disablediag","os="])
    except Exception as error:
        print(error)
        
    try:
        for opt, arg in opts:
            if opt in "-f":
                file_location = arg
            elif opt in "--step":
                step_through = True
            elif opt in "--disablediag":
                diag_log_enabled = False
            elif opt in "--os=":
                os = arg                
    except Exception as error:
        print(error)
    
    print(os)
    
    window = Tk()
    window.title("Magic Draft %.2f" % version)
    window.resizable(width = True, height = True)
    
    if file_location == "":
        file_location = NavigateFileLocation(os);
        
    hotkey, themes, images, table_width = ReadConfig()
    
    ui = WindowUI(window, file_location, step_through, diag_log_enabled, os, themes, images, table_width)
    
    if hotkey:
        KeyListener(ui)    
    
    window.mainloop()
    
def main(argv):
    Startup(argv)
if __name__ == "__main__":
    main(sys.argv[1:])
  