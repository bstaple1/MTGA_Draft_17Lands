import os
import time
import json
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

def LogEntry(log_name, entry_text, diag_log_enabled):
    if diag_log_enabled:
        try:
            with open(log_name, "a") as log_file:
                log_file.write("<%s>%s\n" % (time.strftime('%X %x'), entry_text))
        except Exception as error:
            print("LogEntry Error:  %s" % error)


class LogScanner:
    def __init__(self,log_file, step_through, diag_log_enabled, os):
        self.os = os
        self.log_file = log_file
        self.step_through = step_through
        directory = "Logs\\" if self.os == "PC" else "Logs/"
        self.diag_log_file = directory + "DraftLog_%s.log" % (str(time.time()))
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
        self.sideboard = []
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
        self.sideboard = []
        self.pack_cards = [None] * 8
        self.initial_pack = [None] * 8
        self.current_pack = 0
        self.previous_picked_pack = 0
        self.current_picked_pick = 0

    def DraftStartSearch(self): 
        #Open the file
        switcher={
                "[UnityCrossThreadLogger]==> Event_Join " : (lambda x, y: self.DraftStartSearchV1(x, y)),
                "[UnityCrossThreadLogger]==> Event.Join " : (lambda x, y: self.DraftStartSearchV2(x, y)),
                "[UnityCrossThreadLogger]==> BotDraft_DraftStatus " : (lambda x, y: self.DraftStartSearchV1(x, y)),
             }
        
        
        try:
            #Check if a new player.log was created (e.g. application was started before Arena was started)
            if self.search_offset > os.path.getsize(self.log_file):
                self.ClearDraft(True)
            offset = self.search_offset
            previous_draft_type = self.draft_type
            previous_draft_set = self.draft_set
            with open(self.log_file, 'r', errors="ignore") as log:
                log.seek(offset)
                for line in log:
                    offset += len(line)
                    
                    for search_string in switcher.keys():
                        string_offset = line.find(search_string)
                        if string_offset != -1:
                            self.search_offset = offset
                            start_parser = switcher.get(search_string, lambda: None)
                            event_data = json.loads(line[string_offset + len(search_string):])
                            start_parser(event_data, offset)
                            LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                            break
                                
            if (self.draft_type != DRAFT_TYPE_UNKNOWN) and \
               ((self.draft_type != previous_draft_type) or \
                (self.draft_set != previous_draft_set)):
                self.pick_offset = self.search_offset 
                self.pack_offset = self.search_offset
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
                        self.draft_set = event_set.upper()
                        directory = "Logs\\"
                        if self.os == "MAC":
                            directory = "Logs/"
                        self.diag_log_file = directory + "DraftLog_%s_%s_%u.log" % (event_set, event_type, int(time.time()))
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
                    self.draft_set = event_set.upper()
                    directory = "Logs\\"
                    if self.os == "MAC":
                        directory = "Logs/"
                    self.diag_log_file = directory + "DraftLog_%s_%s_%u.log" % (event_set, event_type, int(time.time()))
                    #LogEntry(self.diag_log_file, event_data, self.diag_log_enabled)
                                
        except Exception as error:
            print("DraftStartSearchV2 Error: %s" % error)
            
    #Wrapper function for performing a search based on the draft type
    def DraftSearch(self):
        #if self.draft_set == None:
        #    self.ClearDraft(False)
        self.DraftStartSearch()
        
        if self.draft_type == DRAFT_TYPE_PREMIER_V1:
            if self.initial_pack[0] == None:
                self.DraftPackSearchPremierP1P1()
            self.DraftPackSearchPremierV1()
            self.DraftPickedSearchPremierV1()
        elif self.draft_type == DRAFT_TYPE_PREMIER_V2:
            if self.initial_pack[0] == None:
                self.DraftPackSearchPremierP1P1()
            self.DraftPackSearchPremierV2()
            self.DraftPickedSearchPremierV2() 
        elif self.draft_type == DRAFT_TYPE_QUICK:
            self.DraftPackSearchQuick()
            self.DraftPickedSearchQuick()
            
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
            with open(self.log_file, 'r') as log:
                log.seek(offset)

                for line in log:
                    offset += len(line)
                    
                    string_offset = line.find(draft_string)
                    
                    if string_offset != -1:
                        #Remove any prefix (e.g. log timestamp)
                        start_offset = line.find("{\"id\":")                       
                        LogEntry(self.diag_log_file, line, self.diag_log_enabled)
                        draft_data = json.loads(line[start_offset:])
                        request_data = draft_data["request"]
                        payload_data = json.loads(request_data)["Payload"]
                        
                        pack_cards = []
                        parsed_cards = []
                        try:

                            card_data = json.loads(payload_data)
                            cards = card_data["CardsInPack"]

                            for card in cards:
                                card_string = str(card)
                                if card_string in self.set_data["card_ratings"].keys():
                                    if len(self.set_data["card_ratings"][card_string]):
                                        parsed_cards.append(self.set_data["card_ratings"][card_string]["name"])
                                        pack_cards.append(self.set_data["card_ratings"][card_string])
                            
                            pack = card_data["PackNumber"]
                            pick = card_data["PickNumber"]
                            
                            pack_index = (pick - 1) % 8
                            
                            if self.current_pack != pack:
                                self.initial_pack = [None] * 8
                        
                            if self.initial_pack[pack_index] == None:
                                self.initial_pack[pack_index] = pack_cards
                                
                            self.pack_cards[pack_index] = pack_cards
                                
                            if (self.current_pack == 0) and (self.current_pick == 0):
                                self.current_pack = pack
                                self.current_pick = pick
                            
                            if(self.step_through):
                                break
        
                        except Exception as error:
                            error_string = "DraftPackSearchPremierP1P1 Sub Error: %s" % error
                            print(error_string)
                            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
                        print("Pack: %u, Pick: %u, Cards: %s" % (pack, pick, parsed_cards))
            if log.closed == False:
                log.close() 
        except Exception as error:
            error_string = "DraftPackSearchPremierP1P1 Error: %s" % error
            print(error_string)
            LogEntry(self.diag_log_file, error_string,  self.diag_log_enabled)
        
        return pack_cards
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
            LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        
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
                                break
                            
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
        self.deck_colors = {"All Decks" : "","Auto" : "", "W" : "","U" : "","B" : "","R" : "","G" : "","WU" : "","WB" : "","WR" : "","WG" : "","UB" : "","UR" : "","UG" : "","BR" : "","BG" : "","RG" : "","WUB" : "","WUR" : "","WUG" : "","WBR" : "","WBG" : "","WRG" : "","UBR" : "","UBG" : "","URG" : "","BRG" : ""}

        draft_list = [x for x in draft_types_dict.keys() if draft_types_dict[x] == self.draft_type]
        draft_list.extend(list(draft_types_dict.keys()))
        self.set_data = None
        try:
            
            for type in draft_list:
                root = os.getcwd()
                for files in os.listdir(root):
                    set_case = [self.draft_set.upper(), self.draft_set.lower()]
                    for case in set_case:
                        filename = case + "_" + type + "_Data.json"
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