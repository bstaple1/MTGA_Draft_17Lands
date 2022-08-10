import os
import time
import json
import re
import logging
import constants 
import card_logic as CL
import file_extractor as FE
from collections import OrderedDict

if not os.path.exists(constants.DRAFT_LOG_FOLDER):
    os.makedirs(constants.DRAFT_LOG_FOLDER)

scanner_logger = logging.getLogger(constants.LOG_TYPE_DEBUG)

class ArenaScanner:
    def __init__(self, filename, step_through, set_list):
        self.arena_file = filename
        self.set_list = set_list
        self.logger = logging.getLogger(constants.LOG_TYPE_DRAFT)
        self.logger.setLevel(logging.INFO)
        
        self.logging_enabled = True
        
        self.step_through = step_through
        self.set_data = None
        self.draft_type = constants.LIMITED_TYPE_UNKNOWN
        self.pick_offset = 0
        self.pack_offset = 0
        self.search_offset = 0
        self.draft_sets = []
        self.current_pick = 0
        self.picked_cards = [[] for i in range(8)]
        self.taken_cards = []
        self.sideboard = []
        self.pack_cards = [[]] * 8
        self.initial_pack = [[]] * 8
        self.current_pack = 0
        self.previous_picked_pack = 0
        self.current_picked_pick = 0
        self.file_size = 0
        self.data_source = "None"

    def ArenaFile(self, filename):
        self.arena_file = filename

    def LogEnable(self, enable):
        self.logging_enabled = enable
        self.LogSuspend(not enable)

    def LogSuspend(self, suspended):
        if suspended:
            self.logger.setLevel(logging.CRITICAL)
        elif self.logging_enabled:
            self.logger.setLevel(logging.INFO)

    def NewLog(self, set, event):
        try:
            log_name = f"DraftLog_{set}_{event}_{int(time.time())}.log"
            log_path = os.path.join(constants.DRAFT_LOG_FOLDER, log_name)
            for handler in self.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    self.logger.removeHandler(handler)
            formatter = logging.Formatter('%(asctime)s,%(message)s', datefmt='<%d%m%Y %H:%M:%S>')
            new_handler = logging.FileHandler(log_path, delay=True)
            new_handler.setFormatter(formatter)
            self.logger.addHandler(new_handler)
            scanner_logger.info(f"Creating new draft log: {log_path}")
        except Exception as error:
            scanner_logger.info(f"NewLog Error: {error}")

    def ClearDraft(self, full_clear):
        if full_clear:
            self.search_offset = 0
            self.file_size = 0
        self.set_data = None
        self.draft_type = constants.LIMITED_TYPE_UNKNOWN
        self.pick_offset = 0
        self.pack_offset = 0
        self.draft_sets = None
        self.current_pick = 0
        self.picked_cards = [[] for i in range(8)]
        self.taken_cards = []
        self.sideboard = []
        self.pack_cards = [[]] * 8
        self.initial_pack = [[]] * 8
        self.current_pack = 0
        self.previous_picked_pack = 0
        self.current_picked_pick = 0
        self.data_source = "None"
        
    def DraftStartSearch(self): 
        update = False
        event_type = ""
        event_line = ""

        try:
            #Check if a new player.log was created (e.g. application was started before Arena was started)
            if self.file_size > os.path.getsize(self.arena_file):
                self.ClearDraft(True)
            self.file_size = os.path.getsize(self.arena_file)
            offset = self.search_offset
            with open(self.arena_file, 'r') as log:
                log.seek(offset)
                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    for start_string in constants.DRAFT_START_STRINGS:
                        if start_string in line:
                            self.search_offset = offset
                            string_offset = line.find(start_string)
                            event_data = json.loads(line[string_offset + len(start_string):])
                            update, event_type = self.DraftStartSearchV1(event_data)
                            event_line = line
                        

            if update:
                self.NewLog(self.draft_sets[0], event_type)
                self.logger.info(event_line)
                self.pick_offset = self.search_offset
                self.pack_offset = self.search_offset
                scanner_logger.info(f"New draft detected {event_type}, {self.draft_sets}")
        except Exception as error:
            scanner_logger.info(f"DraftStartSearch Error: {error}")
            
        return update
    def DraftStartSearchV1(self, event_data):
        update = False
        event_type = ""
        try:
            request_data = json.loads(event_data["request"])
            payload_data = json.loads(request_data["Payload"])
            event_name = payload_data["EventName"]
            
            scanner_logger.info(f"Event found {event_name}")
            
            event_sections = event_name.split('_')
            
            #Find set name within the event string
            sets = [i[constants.SET_LIST_17LANDS][0] for i in self.set_list.values() for x in event_sections if i[constants.SET_LIST_17LANDS][0] in x]
            sets = list(dict.fromkeys(sets)) #Remove duplicates while retaining order
            events = []
            if sets:
                #Find event type in event string
                events = [i for i in constants.LIMITED_TYPES_DICT.keys() for x in event_sections if i in x]
                
                if not events and [i for i in constants.DRAFT_DETECTION_CATCH_ALL for x in event_sections if i in x]:
                    events.append("PremierDraft") #Unknown draft events will be parsed as premier drafts
            
            if sets and events:
                #event_set = sets[0]
                if events[0] == "Sealed":
                    #Trad_Sealed_NEO_20220317
                    event_type = "TradSealed" if "Trad" in event_sections else "Sealed"
                else:
                    event_type = events[0]
                draft_type = constants.LIMITED_TYPES_DICT[event_type]
                self.ClearDraft(False)
                self.draft_type = draft_type
                self.draft_sets = sets
                update = True

        except Exception as error:
            scanner_logger.info(f"DraftStartSearchV1 Error: {error}")
            
        return update, event_type
    def DraftStartSearchV2(self, event_data):
        try:
            request_data = json.loads(event_data["request"])
            params_data = request_data["params"]
            event_name = params_data["eventName"]
            
            event_string = event_name.split('_')
            
            if len(event_string) > 1:
                event_type = event_string[0]
                event_set = event_string[1]
                
                if event_type in constants.LIMITED_TYPES_DICT.keys():
                    self.draft_type = constants.LIMITED_TYPES_DICT[event_type]
                    self.draft_sets = [event_set.upper()]
                    self.NewLog(event_set, event_type)
                    self.logger.info(event_data)
                                
        except Exception as error:
            scanner_logger.info(f"DraftStartSearchV2 Error: {error}")
            
    #Wrapper function for performing a search based on the draft type
    def DraftDataSearch(self):
        
        if self.draft_type == constants.LIMITED_TYPE_DRAFT_PREMIER_V1:
            if len(self.initial_pack[0]) == 0:
                self.DraftPackSearchPremierP1P1()
            self.DraftPackSearchPremierV1()
            self.DraftPickedSearchPremierV1()
        elif self.draft_type == constants.LIMITED_TYPE_DRAFT_PREMIER_V2:
            if len(self.initial_pack[0]) == 0:
                self.DraftPackSearchPremierP1P1()
            self.DraftPackSearchPremierV2()
            self.DraftPickedSearchPremierV2() 
        elif self.draft_type == constants.LIMITED_TYPE_DRAFT_QUICK:
            self.DraftPackSearchQuick()
            self.DraftPickedSearchQuick()
        elif self.draft_type == constants.LIMITED_TYPE_DRAFT_TRADITIONAL:
            if len(self.initial_pack[0]) == 0:
                self.DraftPackSearchTraditionalP1P1()
            self.DraftPackSearchTraditional()
            self.DraftPickedSearchTraditional()
        elif (self.draft_type == constants.LIMITED_TYPE_SEALED) or (self.draft_type == constants.LIMITED_TYPE_SEALED_TRADITIONAL):
            self.SealedPackSearch()
        return
        
    def DraftPackSearchPremierP1P1(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "CardsInPack"
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        #Remove any prefix (e.g. log timestamp)
                        start_offset = line.find("{\"id\":")                       
                        self.logger.info(line)
                        draft_data = json.loads(line[start_offset:])
                        request_data = draft_data["request"]
                        payload_data = json.loads(request_data)["Payload"]
                        
                        pack_cards = []
                        try:

                            card_data = json.loads(payload_data)
                            cards = card_data["CardsInPack"]

                            for card in cards:
                                pack_cards.append(str(card))
                            
                            pack = card_data["PackNumber"]
                            pick = card_data["PickNumber"]
                            
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [[]] * 8
                        
                            if len(self.initial_pack[pack_index]) == 0:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                                
                            if (self.current_pack == 0) and (self.current_pick == 0):
                                self.current_pack = pack
                                self.current_pick = pick
                            
                            if(self.step_through):
                                break
        
                        except Exception as error:
                            self.logger.info(f"DraftPackSearchPremierP1P1 Sub Error: {error}")
        except Exception as error:
            self.logger.info(f"DraftPackSearchPremierP1P1 Error: {error}")
        
        return pack_cards
    def DraftPickedSearchPremierV1(self):
        offset = self.pick_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick "
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pick_offset = offset
                        start_offset = line.find("{\"id\"")
                        self.logger.info(line)

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
                            
                            self.picked_cards[pack_index].append(card)
                            self.taken_cards.append(card)
                            
                            self.previous_picked_pack = pack
                            self.current_picked_pick = pick
                            
                            if self.step_through:
                                break; 
                            
                        except Exception as error:
                            self.logger.info(f"DraftPickedSearchPremierV1 Error: {error}")         
        except Exception as error:
            self.logger.info(f"DraftPickedSearchPremierV1 Error: {error}")

        
    def DraftPackSearchPremierV1(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]Draft.Notify "
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pack_offset = offset
                        start_offset = line.find("{\"draftId\"")
                        self.logger.info(line)
                        pack_cards = []
                        #Identify the pack
                        draft_data = json.loads(line[start_offset:])
                        try:
                                
                            cards = draft_data["PackCards"].split(',') 
                                
                            for card in cards:
                                pack_cards.append(str(card))
                                        
                            pack = draft_data["SelfPack"]
                            pick = draft_data["SelfPick"]
                                
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [[]] * 8
                        
                            if len(self.initial_pack[pack_index]) == 0:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                            
                            self.current_pack = pack
                            self.current_pick = pick
                            
                            if(self.step_through):
                                break
    
                        except Exception as error:
                            self.logger.info(f"DraftPackSearchPremierV1 Error: {error}")
             
        except Exception as error:
            self.logger.info(f"DraftPackSearchPremierV1 Error: {error}")
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
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pack_offset = offset
                        self.logger.info(line)
                        pack_cards = []
                        #Identify the pack
                        draft_data = json.loads(line[len(draft_string):])
                        try:

                            cards = draft_data["PackCards"].split(',') 
                                
                            for card in cards:
                                pack_cards.append(str(card))
                                        
                            pack = draft_data["SelfPack"]
                            pick = draft_data["SelfPick"]
                                
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [[]] * 8
                        
                            if len(self.initial_pack[pack_index]) == 0:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                            
                            self.current_pack = pack
                            self.current_pick = pick
                            
                            if(self.step_through):
                                break
    
                        except Exception as error:
                            self.logger.info(f"DraftPackSearchPremierV2 Error: {error}")
             
        except Exception as error:
            self.logger.info(f"DraftPackSearchPremierV2 Error: {error}")
        return pack_cards

    
    def DraftPickedSearchPremierV2(self):
        offset = self.pick_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]==> Draft.MakeHumanDraftPick "
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.logger.info(line)
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
                                 
                            self.picked_cards[pack_index].append(card)
                            self.taken_cards.append(card)
                            
                            self.previous_picked_pack = pack
                            self.current_picked_pick = pick
    
                            
                            if self.step_through:
                                break; 
                            
                        except Exception as error:
                            self.logger.info(f"DraftPickedSearchPremierV2 Error: {error}")
          
        except Exception as error:
            self.logger.info(f"DraftPickedSearchPremierV2 Error: {error}")
    
    def DraftPackSearchQuick(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "DraftPack"
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pack_offset = offset
                        #Remove any prefix (e.g. log timestamp)
                        start_offset = line.find("{\"CurrentModule\"")                       
                        self.logger.info(line)
                        draft_data = json.loads(line[start_offset:])
                        payload_data = json.loads(draft_data["Payload"])
                        pack_data = payload_data["DraftPack"]
                        draft_status = payload_data["DraftStatus"]
                        
                        if draft_status == "PickNext":
                            pack_cards = []
                            try:

                                cards = pack_data
                                
                                for card in cards:
                                    pack_cards.append(str(card))
                                            
                                pack = payload_data["PackNumber"] + 1
                                pick = payload_data["PickNumber"] + 1  
                                pack_index = (pick - 1) % 8
                                
                                if self.current_pack != pack:
                                    self.initial_pack = [[]] * 8
                            
                                if len(self.initial_pack[pack_index]) == 0:
                                    self.initial_pack[pack_index] = pack_cards
                                    
                                self.pack_cards[pack_index] = pack_cards
                                    
                                self.current_pack = pack
                                self.current_pick = pick
                                
                                if(self.step_through):
                                    break
        
                            except Exception as error:
                                self.logger.info(f"DraftPackSearchQuick Error: {error}")
            if log.closed == False:
                log.close() 
        except Exception as error:
            self.logger.info(f"DraftPackSearchQuick Error: {error}")
        
        return pack_cards
        
    def DraftPickedSearchQuick(self):
        offset = self.pick_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]==> BotDraft_DraftPick "
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.logger.info(line)
                        self.pick_offset = offset
                        try:
                            #Identify the pack
                            draft_data = json.loads(line[string_offset+len(draft_string):])
                            
                            request_data = json.loads(draft_data["request"])
                            payload_data = json.loads(request_data["Payload"])
                            pick_data = payload_data["PickInfo"]
                            
                            pack = pick_data["PackNumber"] + 1
                            pick = pick_data["PickNumber"] + 1
                            card = pick_data["CardId"]
                            
                            pack_index = (pick - 1) % 8
                            
                            if self.previous_picked_pack != pack:
                                self.picked_cards = [[] for i in range(8)]
                                 
                            self.previous_picked_pack = pack
                            self.current_picked_pick = pick
                            
                            self.picked_cards[pack_index].append(card)
                            self.taken_cards.append(card)
    
                            if self.step_through:
                                break
                            
                        except Exception as error:
                            self.logger.info(f"DraftPickedSearchQuick Error: {error}")
            if log.closed == False:
                log.close()      
        except Exception as error:
            self.logger.info(f"DraftPickedSearchQuick Error: {error}")
            
    def DraftPackSearchTraditionalP1P1(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "CardsInPack"
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        #Remove any prefix (e.g. log timestamp)
                        start_offset = line.find("{\"id\":")                       
                        self.logger.info(line)
                        draft_data = json.loads(line[start_offset:])
                        request_data = draft_data["request"]
                        payload_data = json.loads(request_data)["Payload"]
                        
                        pack_cards = []
                        try:

                            card_data = json.loads(payload_data)
                            cards = card_data["CardsInPack"]

                            for card in cards:
                                pack_cards.append(str(card))
                            
                            pack = card_data["PackNumber"]
                            pick = card_data["PickNumber"]
                            
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [[]] * 8
                        
                            if len(self.initial_pack[pack_index]) == 0:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                                
                            if (self.current_pack == 0) and (self.current_pick == 0):
                                self.current_pack = pack
                                self.current_pick = pick
                            
                            if(self.step_through):
                                break
        
                        except Exception as error:
                            self.logger.info(f"DraftPackSearchTraditionalP1P1 Error: {error}")
        except Exception as error:
            self.logger.info(f"DraftPackSearchTraditionalP1P1 Error: {error}")
        
        return pack_cards
        
    def DraftPickedSearchTraditional(self):
        offset = self.pick_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick "
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pick_offset = offset
                        start_offset = line.find("{\"id\"")
                        self.logger.info(line)

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
                            
                            self.picked_cards[pack_index].append(card)
                            self.taken_cards.append(card)
                            
                            self.previous_picked_pack = pack
                            self.current_picked_pick = pick
                            
                            if self.step_through:
                                break; 
                            
                        except Exception as error:
                            self.logger.info(f"DraftPickedSearchTraditional Error: {error}")       
        except Exception as error:
            self.logger.info(f"DraftPickedSearchTraditional Error: {error}") 

        
    def DraftPackSearchTraditional(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "[UnityCrossThreadLogger]Draft.Notify "
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pack_offset = offset
                        start_offset = line.find("{\"draftId\"")
                        self.logger.info(line)
                        pack_cards = []
                        #Identify the pack
                        draft_data = json.loads(line[start_offset:])
                        try:
                                
                            cards = draft_data["PackCards"].split(',') 
                                
                            for card in cards:
                                pack_cards.append(str(card))
                                        
                            pack = draft_data["SelfPack"]
                            pick = draft_data["SelfPick"]
                                
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [[]] * 8
                        
                            if len(self.initial_pack[pack_index]) == 0:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                            
                            self.current_pack = pack
                            self.current_pick = pick
                            
                            if(self.step_through):
                                break
    
                        except Exception as error:
                            self.logger.info(f"DraftPackSearchTraditional Error: {error}") 
             
        except Exception as error:
            self.logger.info(f"DraftPackSearchTraditional Error: {error}") 
        return pack_cards

    def SealedPackSearch(self):
        offset = self.pack_offset
        draft_data = object()
        draft_string = "EventGrantCardPool"
        pack_cards = []
        pack = 0
        pick = 0
        #Identify and print out the log lines that contain the draft packs
        try:
            with open(self.arena_file, 'r') as log:
                log.seek(offset)

                while(True):
                    line = log.readline()
                    if not line:
                        break
                    offset = log.tell()
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        self.pack_offset = offset
                        start_offset = line.find("{\"CurrentModule\"")
                        self.logger.info(line)
                        #Identify the pack
                        draft_data = json.loads(line[start_offset:])
                        payload_data = json.loads(draft_data["Payload"])
                        changes = payload_data["Changes"]
                        try:
                            for change in changes:
                                if change["Source"] == "EventGrantCardPool":
                                    card_list_data = change["GrantedCards"]
                                    for card_data in card_list_data:
                                        card = str(card_data["GrpId"])
                                        self.taken_cards.append(card)
                                                   
                        except Exception as error:
                            self.logger.info(f"SealedPackSearch Error: {error}") 
             
        except Exception as error:
            self.logger.info(f"SealedPackSearch Error: {error}") 
        return pack_cards
        
    def RetrieveDataSources(self):
        data_sources = OrderedDict()
        
        try:
            if self.draft_type != constants.LIMITED_TYPE_UNKNOWN:
                draft_list = list(constants.LIMITED_TYPES_DICT.keys())
                draft_type = [x for x in draft_list if constants.LIMITED_TYPES_DICT[x] == self.draft_type][0]
                draft_list.insert(0, draft_list.pop(draft_list.index(draft_type)))
                
                #Search for the set files
                for set in self.draft_sets:
                    for type in draft_list:
                        file_name = "_".join((set,type,constants.SET_FILE_SUFFIX))
                        file = FE.SearchLocalFiles([constants.SETS_FOLDER], [file_name])
                        if len(file):
                            result, json_data = FE.FileIntegrityCheck(file[0])
                            
                            if result == FE.Result.VALID:
                                type_string = f"[{set[0:3]}]{type}" if re.findall("^[Yy]\d{2}", set) else type
                                data_sources[type_string] = file[0]
        
        except Exception as error:
            scanner_logger.info(f"RetrieveDataSources Error: {error}")
    
        if len(data_sources) == 0:
            data_sources = constants.DATA_SOURCES_NONE

        return data_sources
        
    def RetrieveTierSource(self):
        tier_sources = []
        
        try:
            if self.draft_sets:
                file = FE.SearchLocalFiles([constants.TIER_FOLDER], [constants.TIER_FILE_PREFIX])
                
                if len(file):
                    tier_sources = file
        
        except Exception as error:
            scanner_logger.info(f"RetrieveTierSource Error: {error}")

        return tier_sources
        
    def RetrieveSetData(self, file):
        result = FE.Result.ERROR_MISSING_FILE
        self.set_data = None
        
        try:
            result, json_data = FE.FileIntegrityCheck(file)
            
            if result == FE.Result.VALID:
                self.set_data = json_data
        
        except Exception as error:
            scanner_logger.info(f"RetrieveSetData Error: {error}")
            
        return result
        
    def RetrieveColorLimits(self, bayesian_enabled):
        deck_limits = {}
        
        try:
            if self.set_data:
                upper_limit, lower_limit = CL.RatingsLimits(self.set_data["card_ratings"], bayesian_enabled)
                deck_limits ={"upper" : upper_limit, "lower" : lower_limit}
        except Exception as error:
            scanner_logger.info(f"RetrieveColorLimits Error: {error}")
        return deck_limits
        
    def RetrieveColorWinRate(self, label_type):
        deck_colors = {}
        for colors in constants.COLUMN_OPTIONS:
            deck_color = colors
            if (label_type == constants.DECK_FILTER_FORMAT_NAMES) and (deck_color in constants.COLOR_NAMES_DICT):
                deck_color = constants.COLOR_NAMES_DICT[deck_color]
            deck_colors[colors] = deck_color
        
        try:
            if self.set_data:
                for colors in self.set_data["color_ratings"].keys():
                    for deck_color in deck_colors.keys():
                        if (len(deck_color) == len(colors)) and set(deck_color).issubset(colors):
                            filter_label = deck_color
                            if (label_type == constants.DECK_FILTER_FORMAT_NAMES) and (deck_color in constants.COLOR_NAMES_DICT):
                                filter_label = constants.COLOR_NAMES_DICT[deck_color]
                            ratings_string = filter_label + " (%s%%)" % (self.set_data["color_ratings"][colors])
                            deck_colors[deck_color] = ratings_string
                if self.set_data["meta"]["version"] < constants.DATA_SET_VERSION_3:
                    for option in constants.WIN_RATE_OPTIONS_VERSION_3:
                        deck_colors.pop(option)
        except Exception as error:
            scanner_logger.info(f"RetrieveColorWinRate Error: {error}")

        #Switch key and value
        deck_colors = {v: k for k, v in deck_colors.items()}

        return deck_colors
       
    def PickedCards(self, pack_index):
        picked_cards = []
        
        if self.set_data != None:
            if pack_index < len(self.picked_cards):
                for card in self.picked_cards[pack_index]:
                    try:
                        picked_cards.append(self.set_data["card_ratings"][card]["name"])
                    except Exception as error:
                        scanner_logger.info(f"PickedCards Error: {error}")
            
        return picked_cards  

    def InitialPackCards(self, pack_index):
        pack_cards = []
        
        if self.set_data != None:
            if pack_index < len(self.initial_pack):
                for card in self.initial_pack[pack_index]:
                    try:
                        pack_cards.append(self.set_data["card_ratings"][card])
                    except Exception as error:
                        scanner_logger.info(f"InitialPackCards Error: {error}")
        
        return pack_cards        
        
    def PackCards(self, pack_index):
        pack_cards = []
        
        if self.set_data != None:
            if pack_index < len(self.pack_cards):
                for card in self.pack_cards[pack_index]:
                    try:
                        pack_cards.append(self.set_data["card_ratings"][card])
                    except Exception as error:
                        scanner_logger.info(f"PackCards Error: {error}")
        
        return pack_cards
        
    def TakenCards(self):
        taken_cards = []
        
        if self.set_data != None:
            for card in self.taken_cards:
                try:
                    taken_cards.append(self.set_data["card_ratings"][card])
                except Exception as error:
                    scanner_logger.info(f"TakenCards Error: {error}")
        
        return taken_cards
        
    def RetrieveTierData(self, files, deck_colors):
        tier_data = {}
        count = 0
        try:
            for file in files:
                if os.path.exists(file):
                    with open(file, 'r') as json_file:
                        data = json.loads(json_file.read())
                        if [i for i in self.draft_sets if i in data["meta"]["set"]]:
                            tier_id = f"Tier{count}"
                            tier_label = data["meta"]["label"]
                            tier_label = f'{tier_label[:8]}...' if len(tier_label) > 11 else tier_label #Truncate label if it's too long
                            tier_key = f'{tier_id} ({tier_label})'
                            deck_colors[tier_key] = tier_id
                            tier_data[tier_id] = data
                            count += 1
             
        except Exception as error:
            scanner_logger.info(f"RetrieveTierData Error: {error}")  
        return tier_data