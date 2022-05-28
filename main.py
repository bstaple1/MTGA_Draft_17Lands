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
# - sys standard library (https://docs.python.org/3/library/sys.html)
#   - Access to the command line argument list.
# - io standard library (https://docs.python.org/3/library/sys.html)
#   - Access to the command line argument list.
# - PIL library (https://pillow.readthedocs.io/en/stable/)
#   - Access to image manipulation modules.
# - ttkwidgets library (https://github.com/TkinterEP/ttkwidgets)
#   - Access to the autocomplete entry box widget.
# - file_extractor module (local)
#   - Access to the functions used for downloading the data sets.
# - card_logic module (local)
#   - Access to the functions used for processing the card data.
# - log_scanner module (local)
#   - Access to the functions used for reading the arena log.
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
import tkinter.messagebox as MessageBox
import urllib
import os
import argparse
import sys
import io
import functools
import logging
import logging.handlers
import file_extractor as FE
import card_logic as CL
import log_scanner as LS
from ttkwidgets.autocomplete import AutocompleteEntry

__version__= 2.85

DEBUG_LOG_FOLDER = os.path.join(os.getcwd(), "Debug")
DEBUG_LOG_FILE = os.path.join(DEBUG_LOG_FOLDER, "debug.log")

if not os.path.exists(DEBUG_LOG_FOLDER):
    os.makedirs(DEBUG_LOG_FOLDER)

ui_logger = logging.getLogger("mtgaTool")
ui_logger.setLevel(logging.INFO)
handlers = {
    logging.handlers.TimedRotatingFileHandler(DEBUG_LOG_FILE, when='D', interval=1, backupCount=7, utc=True),
    logging.StreamHandler(sys.stdout),
}
formatter = logging.Formatter('%(asctime)s,%(message)s', datefmt='<%m/%d/%Y %H:%M:%S>')
for handler in handlers:
    handler.setFormatter(formatter)
    ui_logger.addHandler(handler)
        
    
def CheckVersion(platform, version):
    return_value = False
    repository_version = platform.SessionRepositoryVersion()
    repository_version = int(repository_version)
    client_version = round(float(version) * 100)
    if repository_version > client_version:
        return_value = True
        
        
    repository_version = round(float(repository_version) / 100.0, 2)
    return return_value, repository_version
        
def OnPress(key, ui):
    if key == KeyCode.from_char('\x07'): #CTRL+G
        ui.WindowLift(ui.root)

def KeyListener(window_ui):
    Listener(on_press=lambda event: OnPress(event, ui=window_ui)).start()


def FixedMap(style, option):
    # Returns the style map for 'option' with any styles starting with
    # ("!disabled", "!selected", ...) filtered out

    # style.map() returns an empty list for missing options, so this should
    # be future-safe
    return [elm for elm in style.map("Treeview", query_opt=option)
            if elm[:2] != ("!disabled", "!selected")]

def TableFilterOptions(table, filter_a, filter_b, filter_c):
    non_color_options = ["All GIHWR", "All IWD", "All ALSA"]
    filter_dict = {"FilterA" : filter_a, "FilterB" : filter_b, "FilterC" : filter_c}
    
    for key, value in filter_dict.items():
        if len(value) == 1: #Single color filter
            if value[0] == "All Decks":
                table.heading(key, text = "All")
            elif value[0] in non_color_options:
                color, type = value[0].split(" ")
                table.heading(key, text = type)
            else:
                table.heading(key, text = value)
        else: #Multi-color filters
            table.heading(key, text = "/".join(value))

def CopySuggested(deck_colors, deck, set_data, color_options, set):
    colors = color_options[deck_colors.get()]
    deck_string = ""
    try:
        deck_string = CL.CopyDeck(deck[colors]["deck_cards"],deck[colors]["sideboard_cards"],set_data["card_ratings"], set)
        CopyClipboard(deck_string)
    except Exception as error:
        ui_logger.info(f"CopySuggested Error: {error}")
    return 
    
def CopyTaken(taken_cards, set_data, set, color):
    deck_string = ""
    try:
        stacked_cards = CL.StackCards(taken_cards, color)
        deck_string = CL.CopyDeck(stacked_cards, None, set_data["card_ratings"], set)
        CopyClipboard(deck_string)

    except Exception as error:
        ui_logger.info(f"CopyTaken Error: {error}")
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
        ui_logger.info(f"CopyClipboard Error: {error}")
    return 
    

        
class WindowUI:
    def __init__(self, root, filename, step_through, configuration):
        self.root = root
        self.configuration = configuration
        self.filename = filename
        self.step_through = step_through
        
        self.draft = LS.ArenaScanner(self.filename, self.step_through)
        self.trace_ids = []
        
        self.deck_limits = {}
        self.tier_data = {}
        self.deck_colors = self.draft.RetrieveColorWinRate()
        self.data_sources = self.draft.RetrieveDataSources()
        self.tier_source = self.draft.RetrieveTierSource()
        
        Grid.rowconfigure(self.root, 8, weight = 1)
        Grid.columnconfigure(self.root, 0, weight = 1)
        Grid.columnconfigure(self.root, 1, weight = 1)
        #Menu Bar
        self.menubar = Menu(self.root)
        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open", command=self.FileOpen)
        self.datamenu = Menu(self.menubar, tearoff=0)
        self.datamenu.add_command(label="View Sets", command=self.SetViewPopup)

        self.cardmenu = Menu(self.menubar, tearoff=0)
        self.cardmenu.add_command(label="Taken Cards", command=self.TakenCardsPopup)
        self.cardmenu.add_command(label="Suggest Decks", command=self.SuggestDeckPopup)
        self.cardmenu.add_command(label="Compare Cards", command=self.CardComparePopup)
        
        self.settingsmenu = Menu(self.menubar, tearoff=0)
        self.settingsmenu.add_command(label="Settings", command=self.SettingsPopup)
        
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.menubar.add_cascade(label="Data", menu=self.datamenu)
        self.menubar.add_cascade(label="Cards", menu=self.cardmenu)
        self.menubar.add_cascade(label="Settings", menu=self.settingsmenu)
        self.root.config(menu=self.menubar)
        
        style = Style()
        style.map("Treeview", 
                foreground=FixedMap(style, "foreground"),
                background=FixedMap(style, "background"))
                
        current_draft_label_frame = Frame(self.root)
        self.current_draft_label = Label(current_draft_label_frame, text="Current Draft:", font='Helvetica 9 bold', anchor="e")
        
        current_draft_value_frame = Frame(self.root)
        self.current_draft_value_label = Label(current_draft_value_frame, text="", font='Helvetica 9', anchor="w")
        
        data_source_label_frame = Frame(self.root)
        self.data_source_label = Label(data_source_label_frame, text="Data Source:", font='Helvetica 9 bold', anchor="e")
        
        deck_colors_label_frame = Frame(self.root)
        self.deck_colors_label = Label(deck_colors_label_frame, text="Deck Filter:", font='Helvetica 9 bold', anchor="e")
        
        self.data_source_selection = StringVar(self.root)
        self.data_source_list = self.data_sources
        
        self.deck_stats_checkbox_value = IntVar(self.root)
        self.missing_cards_checkbox_value = IntVar(self.root)
        self.auto_highest_checkbox_value = IntVar(self.root)
        self.curve_bonus_checkbox_value = IntVar(self.root)
        self.color_bonus_checkbox_value = IntVar(self.root)
        self.bayesian_average_checkbox_value = IntVar(self.root)
        self.draft_log_checkbox_value = IntVar(self.root)
        self.column_2_selection = StringVar(self.root)
        self.column_2_list = self.deck_colors
        self.column_3_selection = StringVar(self.root)
        self.column_3_list = self.deck_colors
        self.column_4_selection = StringVar(self.root)
        self.column_4_list = self.deck_colors

        optionsStyle = Style()
        optionsStyle.configure('my.TMenubutton', font=('Helvetica', 9))
        
        data_source_option_frame = Frame(self.root)
        self.data_source_options = OptionMenu(data_source_option_frame, self.data_source_selection, self.data_source_selection.get(), *self.data_source_list, style="my.TMenubutton")
        
        deck_colors_option_frame = Frame(self.root)
        self.deck_colors_options = OptionMenu(deck_colors_option_frame, self.column_4_selection, self.column_4_selection.get(), *self.column_4_list, style="my.TMenubutton")
        
        self.refresh_button_frame = Frame(self.root)
        self.refresh_button = Button(self.refresh_button_frame, command= lambda : self.UpdateCallback(True), text="Refresh");
        
        self.status_frame = Frame(self.root)
        self.pack_pick_label = Label(self.status_frame, text="Pack: 0, Pick: 0", font='Helvetica 9 bold')
        
        self.pack_table_frame = Frame(self.root, width=10)

        headers = {"Card"    : {"width" : .46, "anchor" : W},
                  "FilterA"  : {"width" : .18, "anchor" : CENTER},
                  "FilterB"  : {"width" : .18, "anchor" : CENTER},
                  "FilterC"  : {"width" : .18, "anchor" : CENTER}}
        self.pack_table = self.CreateHeader(self.pack_table_frame, 0, headers, self.configuration.table_width)
        
        self.missing_frame = Frame(self.root)
        self.missing_cards_label = Label(self.missing_frame, text = "Missing Cards", font='Helvetica 9 bold')
       
        self.missing_table_frame = Frame(self.root, width=10)

        self.missing_table = self.CreateHeader(self.missing_table_frame, 0, headers, self.configuration.table_width)
        
        self.stat_frame = Frame(self.root)
        stat_header = {"Colors"   : {"width" : .19, "anchor" : W},
                       "1"        : {"width" : .11, "anchor" : CENTER},
                       "2"        : {"width" : .11, "anchor" : CENTER},
                       "3"        : {"width" : .11, "anchor" : CENTER},
                       "4"        : {"width" : .11, "anchor" : CENTER},
                       "5"        : {"width" : .11, "anchor" : CENTER},
                       "6+"       : {"width" : .11, "anchor" : CENTER},
                       "Total"    : {"width" : .15, "anchor" : CENTER}}
        self.stat_table = self.CreateHeader(self.root, 0, stat_header, self.configuration.table_width)
        self.stat_label = Label(self.stat_frame, text = "Deck Stats:", font='Helvetica 9 bold', anchor="e", width = 15)

        self.stat_options_selection = StringVar(self.root)
        self.stat_options_list = ["Creatures","Noncreatures","All"]
        
        self.stat_options = OptionMenu(self.stat_frame, self.stat_options_selection, self.stat_options_list[0], *self.stat_options_list, style="my.TMenubutton")
        self.stat_options.config(width=11) 
        
        citation_label = Label(self.root, text="Powered by 17Lands*", font='Helvetica 9 ', anchor="e", borderwidth=2, relief="groove")
        hotkey_label = Label(self.root, text="CTRL+G to Minimize", font='Helvetica 8 ', anchor="e")
        footnote_label = Label(self.root, text="*This application is not endorsed by 17Lands", font='Helvetica 8 ', anchor="e")
        
        citation_label.grid(row = 0, column = 0, columnspan = 2) 
        current_draft_label_frame.grid(row = 1, column = 0, columnspan = 1, sticky = 'nsew')
        current_draft_value_frame.grid(row = 1, column = 1, columnspan = 1, sticky = 'nsew')
        data_source_label_frame.grid(row = 2, column = 0, columnspan = 1, sticky = 'nsew')
        data_source_option_frame.grid(row = 2, column = 1, columnspan = 1, sticky = 'nsew')
        deck_colors_label_frame.grid(row = 3, column = 0, columnspan = 1, sticky = 'nsew')
        deck_colors_option_frame.grid(row = 3, column = 1, columnspan = 1, sticky = 'nsw')
        hotkey_label.grid(row = 4, column = 0, columnspan = 2) 
        self.refresh_button_frame.grid(row = 5, column = 0, columnspan = 2, sticky = 'nsew')
        self.status_frame.grid(row = 6, column = 0, columnspan = 2, sticky = 'nsew')
        self.pack_table_frame.grid(row = 7, column = 0, columnspan = 2, sticky = 'nsew')
        footnote_label.grid(row = 12, column = 0, columnspan = 2)
        self.EnableDeckStates(self.deck_stats_checkbox_value.get())
        self.EnableMissingCards(self.missing_cards_checkbox_value.get())

        self.refresh_button.pack(expand = True, fill = "both")

        self.pack_pick_label.pack(expand = False, fill = None)
        self.pack_table.pack(expand = True, fill = 'both')
        self.missing_cards_label.pack(expand = False, fill = None)
        self.missing_table.pack(expand = True, fill = 'both')
        self.stat_label.pack(side=LEFT, expand = True, fill = None)
        self.stat_options.pack(side=RIGHT, expand = True, fill = None)
        self.current_draft_label.pack(expand = True, fill = None, anchor="e")
        self.current_draft_value_label.pack(expand = True, fill = None, anchor="w")
        self.data_source_label.pack(expand = True, fill = None, anchor="e")
        self.data_source_options.pack(expand = True, fill = None, anchor="w")
        self.deck_colors_label.pack(expand = False, fill = None, anchor="e")
        self.deck_colors_options.pack(expand = False, fill = None, anchor="w")
        self.check_timestamp = 0
        self.previous_timestamp = 0
        
        self.UpdateSettingsData()

        self.root.attributes("-topmost", True)

        self.VersionCheck()

    def CreateHeader(self, frame, height, headers, total_width):
        header_labels = tuple(headers.keys())
        list_box = Treeview(frame, columns = header_labels, show = 'headings')
        list_box.config(height=height)
        style = Style() 
        style.configure("Treeview.Heading", font=("Cascadia", 7))
        try:
            list_box.tag_configure("darkgrey", background="#808080")
            list_box.tag_configure("custombold", font=("Cascadia Bold", 7))
            list_box.tag_configure("customfont", font=("Cascadia", 7))
            list_box.tag_configure("whitecard", font=("Cascadia", 7, "bold"), background = "#FFFFFF", foreground = "#000000")
            list_box.tag_configure("redcard", font=("Cascadia", 7, "bold"), background = "#FF6C6C", foreground = "#000000")
            list_box.tag_configure("bluecard", font=("Cascadia", 7, "bold"), background = "#6078F3", foreground = "#000000")
            list_box.tag_configure("blackcard", font=("Cascadia", 7, "bold"), background = "#BFBFBF", foreground = "#000000")
            list_box.tag_configure("greencard", font=("Cascadia", 7, "bold"), background = "#60DC68", foreground = "#000000")
            list_box.tag_configure("goldcard", font=("Cascadia", 7, "bold"), background = "#F0E657", foreground = "#000000")
            for count, column in enumerate(header_labels):
                list_box.column(column, stretch = NO, anchor = headers[column]["anchor"], width = int(headers[column]["width"] * total_width))
                list_box.heading(column, text = column, anchor = CENTER)
            list_box["show"] = "headings"  # use after setting column's size
        except Exception as error:
            ui_logger.info(f"CreateHeader Error: {error}")
        return list_box

    def UpdatePackTable(self, card_list, taken_cards, filtered):
        try:
            filtered_list = CL.CardFilter(card_list,
                                          taken_cards,
                                          filtered,
                                          self.deck_colors,
                                          self.deck_limits,
                                          self.tier_data,
                                          self.configuration,
                                          self.configuration.curve_bonus_enabled,
                                          self.configuration.color_bonus_enabled)
                                          
            filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
            # clear the previous rows
            for row in self.pack_table.get_children():
                self.pack_table.delete(row)
            
            list_length = len(filtered_list)
            
            if list_length:
                self.pack_table.config(height = list_length)
            else:
                self.pack_table.config(height=1)
                
            #Update the filtered column header with the filtered colors
            TableFilterOptions(self.pack_table, filtered["filtered_a"], filtered["filtered_b"], filtered["filtered_c"])
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                
                self.pack_table.insert("",index = count, iid = count, values = (card["name"], card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
            self.pack_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.pack_table, card_list=card_list, selected_color=filtered["filtered_c"]))
        except Exception as error:
            ui_logger.info(f"UpdatePackTable Error: {error}")
            
    def UpdateMissingTable(self, current_pack, previous_pack, picked_cards, taken_cards, filtered):
        try:
            for row in self.missing_table.get_children():
                self.missing_table.delete(row)
            
            #Update the filtered column header with the filtered colors
            TableFilterOptions(self.missing_table, filtered["filtered_a"], filtered["filtered_b"], filtered["filtered_c"])
            if len(previous_pack) == 0:
                self.missing_table.config(height=1)
            else:
                missing_cards = [x for x in previous_pack if x not in current_pack]
                
                list_length = len(missing_cards)
                
                if list_length:
                    self.missing_table.config(height = list_length)
                else:
                    self.missing_table.config(height=1) 
                
                if list_length:
                    filtered_list = CL.CardFilter(missing_cards,
                                                  taken_cards,
                                                  filtered,
                                                  self.deck_colors,
                                                  self.deck_limits,
                                                  self.tier_data,
                                                  self.configuration,
                                                  False,
                                                  False)
                    
                    filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
                    for count, card in enumerate(filtered_list):
                        row_tag = CL.RowColorTag(card["colors"])
                        card_name = "*" + card["name"] if card["name"] in picked_cards else card["name"]
                        
                        self.missing_table.insert("",index = count, iid = count, values = (card_name, card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
                    self.missing_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.missing_table, card_list=missing_cards, selected_color=filtered["filtered_c"]))
        except Exception as error:
            ui_logger.info(f"UpdateMissingTable Error: {error}")

    def ClearCompareTable(self, compare_table, matching_cards):
        matching_cards.clear()
        compare_table.delete(*compare_table.get_children())

    def UpdateCompareTable(self, compare_table, matching_cards, entry_box, card_list, filtered):
        try:
            added_card = entry_box.get()
            if len(added_card):
                cards = [card_list[x] for x in card_list if card_list[x]["name"] == added_card and card_list[x] not in matching_cards]
                entry_box.delete(0,END)
                if len(cards):
                    matching_cards.append(cards[0])

            filtered_list = CL.CardFilter(matching_cards,
                                          matching_cards,
                                          filtered,
                                          self.deck_colors,
                                          self.deck_limits,
                                          self.tier_data,
                                          self.configuration,
                                          self.configuration.curve_bonus_enabled,
                                          self.configuration.color_bonus_enabled)
                    
            filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
            compare_table.delete(*compare_table.get_children())
            
            #Update the filtered column header with the filtered colors
            TableFilterOptions(compare_table, filtered["filtered_a"], filtered["filtered_b"], filtered["filtered_c"])
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                compare_table.insert("",index = count, iid = count, values = (card["name"], card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
            compare_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=compare_table, card_list=matching_cards, selected_color=filtered["filtered_c"]))
        except Exception as error:
            ui_logger.info(f"UpdateCompareTable Error: {error}")

    def UpdateTakenTable(self, taken_table, taken_cards, filtered):
        try:
            filtered_list = CL.CardFilter(taken_cards,
                                          taken_cards,
                                          filtered,
                                          self.deck_colors,
                                          self.deck_limits,
                                          self.tier_data,
                                          self.configuration,
                                          False,
                                          False)
                    
            filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
            list_length = len(filtered_list)
            
            #Update the filtered column header with the filtered colors
            TableFilterOptions(taken_table, filtered["filtered_a"], filtered["filtered_b"], filtered["filtered_c"])
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                taken_table.insert("",index = count, iid = count, values = (card["name"], card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
            taken_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=taken_table, card_list=taken_cards, selected_color=filtered["filtered_c"]))
        except Exception as error:
            ui_logger.info(f"UpdateTakenTable Error: {error}")
            
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
            suggest_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=suggest_table, card_list=suggested_deck, selected_color=[color]))
    
        except Exception as error:
            ui_logger.info(f"UpdateSuggestTable Error: {error}")
            
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
            ui_logger.info(f"UpdateDeckStats Error: {error}")
            
    def UpdatePackPick(self, pack, pick):
        try:
            new_label = "Pack: %u, Pick: %u" % (pack, pick)
            self.pack_pick_label.config(text = new_label)
        
        except Exception as error:
            ui_logger.info(f"UpdatePackPick Error: {error}")
     
    def UpdateCurrentDraft(self, set, draft_type):
        try: 
            draft_type_string = ''
            
            for key, value in LS.limited_types_dict.items():
                if LS.limited_types_dict[key] == draft_type:
                    draft_type_string = key
                    
            new_label = " %s %s" % (set, draft_type_string)
            self.current_draft_value_label.config(text = new_label)
        except Exception as error:
            ui_logger.info(f"UpdateCurrentDraft Error: {error}")
     
    def UpdateSourceOptions(self, new_list):
        self.ControlTrace(False)
        try:
            if new_list:
                self.data_source_selection.set(next(iter(self.data_sources)))
                menu = self.data_source_options["menu"]
                menu.delete(0, "end")

                self.data_source_list = []

                for key, data in self.data_sources.items():
                    menu.add_command(label=key, 
                                    command=lambda value=key: self.data_source_selection.set(value))
                    self.data_source_list.append(key)

            elif self.data_source_selection.get() not in self.data_sources.keys():
                self.data_source_selection.set(next(iter(self.data_sources)))



        except Exception as error:
            ui_logger.info(f"UpdateSourceOptions Error: {error}")
            
        self.ControlTrace(True)
     
    def UpdateFilterOptions(self):
        self.ControlTrace(False)
        try: 
            if self.column_2_selection.get() not in self.deck_colors.values():
                self.column_2_selection.set("All ALSA")
            if self.column_3_selection.get() not in self.deck_colors.values():
                self.column_3_selection.set("All Decks")
            if self.column_4_selection.get() not in self.deck_colors.values():
                self.column_4_selection.set("Auto")
            
            menu = self.deck_colors_options["menu"]
            menu.delete(0, "end")
            self.column_2_list = []
            self.column_3_list = []
            self.column_4_list = []

            for key, data in self.deck_colors.items():
                if len(data):
                    menu.add_command(label=data, 
                                    command=lambda value=data: self.column_4_selection.set(value))
                    #self.deck_colors_options_list.append(data)
                    self.column_2_list.append(data)
                    self.column_3_list.append(data)
                    self.column_4_list.append(data)
                
        except Exception as error:
            ui_logger.info(f"UpdateFilterOptions Error: {error}")
            
        self.ControlTrace(True)
        
    def DefaultSettingsCallback(self, *args):
        CL.ResetConfig()
        
        self.configuration = CL.ReadConfig()
        self.ControlTrace(False)
        try:
           self.column_2_selection.set(self.configuration.column_2) 
           self.column_3_selection.set(self.configuration.column_3)
           self.column_4_selection.set(self.configuration.column_4)
           self.deck_stats_checkbox_value.set(self.configuration.stats_enabled)
           self.missing_cards_checkbox_value.set(self.configuration.missing_enabled)
           self.auto_highest_checkbox_value.set(self.configuration.auto_highest_enabled)
           self.curve_bonus_checkbox_value.set(self.configuration.curve_bonus_enabled)
           self.color_bonus_checkbox_value.set(self.configuration.color_bonus_enabled)
           self.bayesian_average_checkbox_value.set(self.configuration.bayesian_average_enabled)
           self.draft_log_checkbox_value.set(self.configuration.draft_log_enabled)
        except Exception as error:
           self.column_2_selection.set("All ALSA") 
           self.column_3_selection.set("All Decks")
           self.column_4_selection.set("Auto")
           self.deck_stats_checkbox_value.set(False)
           self.missing_cards_checkbox_value.set(False)
           self.auto_highest_checkbox_value.set(False)
           self.curve_bonus_checkbox_value.set(False)
           self.color_bonus_checkbox_value.set(False)
           self.bayesian_average_checkbox_value.set(False)
           self.draft_log_checkbox_value.set(False)
        self.ControlTrace(True)
        self.UpdateSettingsCallback()      

    def UpdateSourceCallback(self, *args):

        self.draft.RetrieveSetData(self.data_sources[self.data_source_selection.get()])
        self.deck_limits = self.draft.RetrieveColorLimits(True)
        self.deck_colors = self.draft.RetrieveColorWinRate()
        self.tier_data = self.draft.RetrieveTierData(self.tier_source, self.deck_colors)
        self.UpdateCallback(False)

    def UpdateSettingsCallback(self, *args):
        self.configuration.column_2 = self.column_2_selection.get()
        self.configuration.column_3 = self.column_3_selection.get()
        self.configuration.column_4 = self.column_4_selection.get()
        
        self.configuration.missing_enabled = bool(self.missing_cards_checkbox_value.get())
        self.configuration.stats_enabled = bool(self.deck_stats_checkbox_value.get())
        self.configuration.auto_highest_enabled = bool(self.auto_highest_checkbox_value.get())
        self.configuration.curve_bonus_enabled = bool(self.curve_bonus_checkbox_value.get())
        self.configuration.color_bonus_enabled = bool(self.color_bonus_checkbox_value.get())
        self.configuration.bayesian_average_enabled = bool(self.bayesian_average_checkbox_value.get())
        self.configuration.draft_log_enabled = bool(self.draft_log_checkbox_value.get())
        CL.WriteConfig(self.configuration)
        
        self.UpdateSettingsData()
        self.UpdateCallback(False)     
        

    def UpdateDraftData(self):
        if self.draft.DraftStartSearch():
            self.data_sources = self.draft.RetrieveDataSources()
            self.tier_source = self.draft.RetrieveTierSource()
            self.UpdateSourceOptions(True)
            self.draft.RetrieveSetData(self.data_sources[self.data_source_selection.get()])

            self.deck_limits = self.draft.RetrieveColorLimits(True)
            self.deck_colors = self.draft.RetrieveColorWinRate()
            self.tier_data = self.draft.RetrieveTierData(self.tier_source, self.deck_colors)

        self.draft.DraftDataSearch()     

    def UpdateSettingsData(self):
        self.ControlTrace(False)
        try:
           self.column_2_selection.set(self.configuration.column_2) 
           self.column_3_selection.set(self.configuration.column_3)
           self.column_4_selection.set(self.configuration.column_4)
           self.deck_stats_checkbox_value.set(self.configuration.stats_enabled)
           self.missing_cards_checkbox_value.set(self.configuration.missing_enabled)
           self.auto_highest_checkbox_value.set(self.configuration.auto_highest_enabled)
           self.curve_bonus_checkbox_value.set(self.configuration.curve_bonus_enabled)
           self.color_bonus_checkbox_value.set(self.configuration.color_bonus_enabled)
           self.bayesian_average_checkbox_value.set(self.configuration.bayesian_average_enabled)
           self.draft_log_checkbox_value.set(self.configuration.draft_log_enabled)
        except Exception as error:
           self.column_2_selection.set("All ALSA") 
           self.column_3_selection.set("All Decks")
           self.column_4_selection.set("Auto")
           self.deck_stats_checkbox_value.set(False)
           self.missing_cards_checkbox_value.set(False)
           self.auto_highest_checkbox_value.set(False)
           self.curve_bonus_checkbox_value.set(False)
           self.color_bonus_checkbox_value.set(False)
           self.bayesian_average_checkbox_value.set(False)
           self.draft_log_checkbox_value.set(False)
        self.ControlTrace(True) 
        
        self.draft.LogEnable(self.configuration.draft_log_enabled)
        
        
    def UpdateCallback(self, enable_draft_search):
        if enable_draft_search:
            self.UpdateDraftData()
        
        self.UpdateSourceOptions(False)
        self.UpdateFilterOptions()
        
        self.EnableDeckStates(self.deck_stats_checkbox_value.get())
        self.EnableMissingCards(self.missing_cards_checkbox_value.get())
              
        taken_cards = self.draft.TakenCards()
        
        filtered = {}
        filtered["filtered_a"] = CL.ColorFilter(taken_cards, self.column_2_selection.get(), self.deck_colors, self.configuration)
        filtered["filtered_b"] = CL.ColorFilter(taken_cards, self.column_3_selection.get(), self.deck_colors, self.configuration)
        filtered["filtered_c"] = CL.ColorFilter(taken_cards, self.column_4_selection.get(), self.deck_colors, self.configuration)

        self.UpdateCurrentDraft(self.draft.draft_set, self.draft.draft_type)
        self.UpdatePackPick(self.draft.current_pack, self.draft.current_pick)
        pack_index = (self.draft.current_pick - 1) % 8

        pack_cards = self.draft.PackCards(pack_index)
        self.UpdatePackTable(pack_cards, 
                             taken_cards,
                             filtered)
                             
        self.UpdateMissingTable(pack_cards,
                                self.draft.InitialPackCards(pack_index),
                                self.draft.PickedCards(pack_index),
                                taken_cards,
                                filtered)   
                                
        self.UpdateDeckStatsCallback()

    def UpdateDeckStatsCallback(self, *args):
        self.UpdateDeckStatsTable(self.draft.TakenCards(), self.stat_options_selection.get())

    def UpdateUI(self):
        try:
            self.current_timestamp = os.stat(self.filename).st_mtime
            
            if self.current_timestamp != self.previous_timestamp:
                self.previous_timestamp = self.current_timestamp
                
                previous_pick = self.draft.current_pick
                previous_pack = self.draft.current_pack
                
                while(True):

                    self.UpdateCallback(True)
                    if self.draft.current_pack < previous_pack:
                        self.DraftReset(True)
                        self.UpdateCallback(True)
                    if self.draft.step_through and (previous_pick != self.draft.current_pick):
                        input("Continue?")
                    else:
                        break
                        
                    previous_pick = self.draft.current_pick
                    previous_pack = self.draft.current_pack
        except Exception as error:
            ui_logger.info(f"UpdateUI Error: {error}")
            
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
        Grid.rowconfigure(popup, 1, weight = 1)
        try:
            extractor = FE.FileExtractor()
            sets = extractor.SessionSets()
        
            column_headers = ('Set', 'Draft', 'Start Date', 'End Date')
            list_box_frame = Frame(popup)
            list_box_scrollbar = Scrollbar(list_box_frame, orient=VERTICAL)
            list_box_scrollbar.pack(side=RIGHT, fill=Y)
            
            list_box = Treeview(list_box_frame, columns = column_headers, show = 'headings')
            list_box.tag_configure('gray', background='#cccccc')
            list_box.tag_configure('bold', font=('Arial Bold', 10))
            
            list_box.config(yscrollcommand=list_box_scrollbar.set)
            list_box_scrollbar.config(command=list_box.yview)
            
            notice_label = Label(popup, text="17Lands has an embargo period of 12 days for new sets on Magic Arena. Visit https://www.17lands.com for more details.", font='Helvetica 9', anchor="c")
            set_label = Label(popup, text="Set:")
            draft_label = Label(popup, text="Draft:")
            start_label = Label(popup, text="Start Date:")
            end_label = Label(popup, text="End Date:")
            draft_choices = ["PremierDraft", "QuickDraft", "TradDraft", "Sealed", "TradSealed"]
            
            draft_value = StringVar(self.root)
            draft_value.set('PremierDraft')
            draft_entry = OptionMenu(popup, draft_value, draft_choices[0], *draft_choices)
            
            set_choices = [k for k, v in sets.items()]
            
            set_value = StringVar(self.root)
            set_value.set('PremierDraft')
            set_entry = OptionMenu(popup, set_value, set_choices[0], *set_choices)
            
            start_entry = Entry(popup)
            start_entry.insert(END, '2019-1-1')
            end_entry = Entry(popup)
            end_entry.insert(END, str(date.today()))
            
            progress = Progressbar(popup,orient=HORIZONTAL,length=100,mode='determinate')
            
            add_button = Button(popup, command=lambda: self.AddSet(extractor,
                                                                   set_value,
                                                                   draft_value,
                                                                   start_entry,
                                                                   end_entry,
                                                                   add_button,
                                                                   progress,
                                                                   list_box,
                                                                   sets,
                                                                   2.00), text="ADD SET")
            
            
            for column in column_headers:
                list_box.column(column, anchor = CENTER, stretch = YES, width = 100)
                list_box.heading(column, text = column, anchor = CENTER)
                
            notice_label.grid(row=0, column=0, columnspan=8, sticky = 'nsew')
            list_box_frame.grid(row=1, column=0, columnspan=8, sticky = 'nsew')
            set_label.grid(row=2, column=0, sticky = 'nsew')
            set_entry.grid(row=2, column=1, sticky = 'nsew')
            start_label.grid(row=2, column=2, sticky = 'nsew')
            start_entry.grid(row=2, column=3, sticky = 'nsew')
            end_label.grid(row=2, column=4, sticky = 'nsew')
            end_entry.grid(row=2, column=5, sticky = 'nsew')
            draft_label.grid(row=2, column=6, sticky = 'nsew')
            draft_entry.grid(row=2, column=7, sticky = 'nsew')
            add_button.grid(row=3, column=0, columnspan=8, sticky = 'nsew')
            progress.grid(row=4, column=0, columnspan=8, sticky = 'nsew')
            
            list_box.pack(expand = True, fill = "both")
    
            self.DataViewUpdate(list_box, sets)
            
            popup.attributes("-topmost", True)
        except Exception as error:
            ui_logger.info(f"SetViewPopup Error: {error}")
        
    def CardComparePopup(self):
        popup = Toplevel()
        popup.wm_title("Card Compare")
        
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            
            filtered = {}
            taken_cards = self.draft.TakenCards()
            filtered["filtered_a"] = CL.ColorFilter(taken_cards, self.column_2_selection.get(), self.deck_colors, self.configuration)
            filtered["filtered_b"] = CL.ColorFilter(taken_cards, self.column_3_selection.get(), self.deck_colors, self.configuration)
            filtered["filtered_c"] = CL.ColorFilter(taken_cards, self.column_4_selection.get(), self.deck_colors, self.configuration)
            
            matching_cards = []
            
            card_frame = Frame(popup)

            set_card_names = [v["name"] for k,v in self.draft.set_data["card_ratings"].items()]
            card_entry = AutocompleteEntry(
                         card_frame, 
                         completevalues=set_card_names
                         )
            
            headers = {"Card"    : {"width" : .46, "anchor" : W},
                    "FilterA"  : {"width" : .18, "anchor" : CENTER},
                    "FilterB"  : {"width" : .18, "anchor" : CENTER},
                    "FilterC"  : {"width" : .18, "anchor" : CENTER}}
            compare_table_frame = Frame(popup)
            compare_scrollbar = Scrollbar(compare_table_frame, orient=VERTICAL)
            compare_scrollbar.pack(side=RIGHT, fill=Y)
            compare_table = self.CreateHeader(compare_table_frame, 20, headers, self.configuration.table_width)
            compare_table.config(yscrollcommand=compare_scrollbar.set)
            compare_scrollbar.config(command=compare_table.yview)
            
            clear_button = Button(popup, text="Clear", command=lambda:self.ClearCompareTable(compare_table, matching_cards))

            card_frame.grid(row=0, column=0, sticky="nsew")
            clear_button.grid(row=1, column=0, sticky= "nsew")
            compare_table_frame.grid(row=2, column=0, sticky="nsew")
            
            compare_table.pack(expand = True, fill = "both")
            card_entry.pack(side = LEFT, expand = True, fill = "both")

            card_entry.bind("<Return>", lambda event: self.UpdateCompareTable(compare_table,
                                                                              matching_cards,
                                                                              card_entry,
                                                                              self.draft.set_data["card_ratings"],
                                                                              filtered))
            
            popup.attributes("-topmost", True)
        except Exception as error:
            ui_logger.info(f"CardComparePopup Error: {error}")
            
    def TakenCardsPopup(self):
        popup = Toplevel()
        popup.wm_title("Taken Cards")
        
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            taken_cards = self.draft.TakenCards()
            filtered = {}
            filtered["filtered_a"] = CL.ColorFilter(taken_cards, self.column_2_selection.get(), self.deck_colors, self.configuration)
            filtered["filtered_b"] = CL.ColorFilter(taken_cards, self.column_3_selection.get(), self.deck_colors, self.configuration)
            filtered["filtered_c"] = CL.ColorFilter(taken_cards, self.column_4_selection.get(), self.deck_colors, self.configuration)
            
            copy_button = Button(popup, command=lambda:CopyTaken(taken_cards,
                                                                 self.draft.set_data,
                                                                 self.draft.draft_set,
                                                                 filtered["filtered_c"]),
                                                                 text="Copy to Clipboard")
            
            headers = {"Card"    : {"width" : .46, "anchor" : W},
                       "FilterA"  : {"width" : .18, "anchor" : CENTER},
                       "FilterB"  : {"width" : .18, "anchor" : CENTER},
                       "FilterC"  : {"width" : .18, "anchor" : CENTER}}
            taken_table_frame = Frame(popup)
            taken_scrollbar = Scrollbar(taken_table_frame, orient=VERTICAL)
            taken_scrollbar.pack(side=RIGHT, fill=Y)
            taken_table = self.CreateHeader(taken_table_frame, 20, headers, self.configuration.table_width)
            taken_table.config(yscrollcommand=taken_scrollbar.set)
            taken_scrollbar.config(command=taken_table.yview)
            
            copy_button.grid(row=0, column=0, stick="nsew")
            taken_table_frame.grid(row=1, column=0, stick = "nsew")
            taken_table.pack(expand = True, fill = "both")
            
            
            self.UpdateTakenTable(taken_table,
                                  taken_cards,
                                  filtered)
            popup.attributes("-topmost", True)
        except Exception as error:
            ui_logger.info(f"TakenCardsPopup Error: {error}")
            
    def SuggestDeckPopup(self):
        popup = Toplevel()
        popup.wm_title("Suggested Decks")
        
        try:
            Grid.rowconfigure(popup, 3, weight = 1)
            
            suggested_decks = CL.SuggestDeck(self.draft.TakenCards(), self.deck_colors, self.deck_limits, self.configuration)
            
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
            ui_logger.info(f"SuggestDeckPopup Error: {error}")
            
    def SettingsPopup(self):
        popup = Toplevel()
        popup.wm_title("Settings")
        #popup.geometry("210x75")
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            
            self.ControlTrace(False)
            
            column_2_label = Label(popup, text="Column 2:", font='Helvetica 9 bold', anchor="w")
            column_3_label = Label(popup, text="Column 3:", font='Helvetica 9 bold', anchor="w")
            column_4_label = Label(popup, text="Column 4:", font='Helvetica 9 bold', anchor="w")
            deck_stats_label = Label(popup, text="Enable Deck Stats:", font='Helvetica 9 bold', anchor="w")
            deck_stats_checkbox = Checkbutton(popup,
                                              variable=self.deck_stats_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)
            missing_cards_label = Label(popup, text="Enable Missing Cards:", font='Helvetica 9 bold', anchor="w")
            missing_cards_checkbox = Checkbutton(popup,
                                                 variable=self.missing_cards_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0)
                                                 
            auto_highest_label = Label(popup, text="Enable Highest Rated:", font='Helvetica 9 bold', anchor="w")
            auto_highest_checkbox = Checkbutton(popup,
                                                 variable=self.auto_highest_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0)
                                                 
            curve_bonus_label = Label(popup, text="Enable Curve Bonus:", font='Helvetica 9 bold', anchor="w")
            curve_bonus_checkbox = Checkbutton(popup,
                                               variable=self.curve_bonus_checkbox_value,
                                               onvalue=1,
                                               offvalue=0)
            color_bonus_label = Label(popup, text="Enable Color Bonus:", font='Helvetica 9 bold', anchor="w")
            color_bonus_checkbox = Checkbutton(popup,
                                                 variable=self.color_bonus_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0)     
            bayesian_average_label = Label(popup, text="Enable Bayesian Average:", font='Helvetica 9 bold', anchor="w")
            bayesian_average_checkbox = Checkbutton(popup,
                                                 variable=self.bayesian_average_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0) 

            draft_log_label = Label(popup, text="Enable Draft Log:", font='Helvetica 9 bold', anchor="w")
            draft_log_checkbox = Checkbutton(popup,
                                             variable=self.draft_log_checkbox_value,
                                             onvalue=1,
                                             offvalue=0)                                                    
            optionsStyle = Style()
            optionsStyle.configure('my.TMenubutton', font=('Helvetica', 9))
            
            column_2_options = OptionMenu(popup, self.column_2_selection, self.column_2_selection.get(), *self.column_2_list, style="my.TMenubutton")
            column_2_options.config(width=10)
            
            column_3_options = OptionMenu(popup, self.column_3_selection, self.column_3_selection.get(), *self.column_3_list, style="my.TMenubutton")
            column_3_options.config(width=10)
            
            column_4_options = OptionMenu(popup, self.column_4_selection, self.column_4_selection.get(), *self.column_4_list, style="my.TMenubutton")
            column_4_options.config(width=10)
            
            default_button = Button(popup, command=self.DefaultSettingsCallback, text="Default Settings");
            
            column_2_label.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_3_label.grid(row=1, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_4_label.grid(row=2, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_2_options.grid(row=0, column=1, columnspan=1, sticky="nsew")
            column_3_options.grid(row=1, column=1, columnspan=1, sticky="nsew")
            column_4_options.grid(row=2, column=1, columnspan=1, sticky="nsew")
            deck_stats_label.grid(row=3, column=0, columnspan=1, sticky="nsew", padx=(10,))
            deck_stats_checkbox.grid(row=3, column=1, columnspan=1, sticky="nsew", padx=(5,))
            missing_cards_label.grid(row=4, column=0, columnspan=1, sticky="nsew", padx=(10,))
            missing_cards_checkbox.grid(row=4, column=1, columnspan=1, sticky="nsew", padx=(5,)) 
            auto_highest_label.grid(row=5, column=0, columnspan=1, sticky="nsew", padx=(10,))
            auto_highest_checkbox.grid(row=5, column=1, columnspan=1, sticky="nsew", padx=(5,))
            curve_bonus_label.grid(row=6, column=0, columnspan=1, sticky="nsew", padx=(10,))
            curve_bonus_checkbox.grid(row=6, column=1, columnspan=1, sticky="nsew", padx=(5,))
            color_bonus_label.grid(row=7, column=0, columnspan=1, sticky="nsew", padx=(10,))
            color_bonus_checkbox.grid(row=7, column=1, columnspan=1, sticky="nsew", padx=(5,))
            bayesian_average_label.grid(row=8, column=0, columnspan=1, sticky="nsew", padx=(10,))
            bayesian_average_checkbox.grid(row=8, column=1, columnspan=1, sticky="nsew", padx=(5,))
            draft_log_label.grid(row=9, column=0, columnspan=1, sticky="nsew", padx=(10,))
            draft_log_checkbox.grid(row=9, column=1, columnspan=1, sticky="nsew", padx=(5,))
            default_button.grid(row=10, column=0, columnspan=2, sticky="nsew")
            
            self.ControlTrace(True)
            
            popup.attributes("-topmost", True)
        except Exception as error:
            ui_logger.info(f"SettingsPopup Error: {error}")
        
    def AddSet(self, extractor, set, draft, start, end, button, progress, list_box, sets, version):
        result = True
        result_string = ""
        while(True):
            try:
                message_box = MessageBox.askyesno(title="Download", message=f"17Lands updates their card data once a day at 01:30 UTC. Are you sure that you want to download {set.get()} {draft.get()} data?")
                if not message_box:
                    break
                    
                extractor.ClearData()
                button['state'] = 'disabled'
                progress['value'] = 0
                self.root.update()
                extractor.Sets(sets[set.get()])
                extractor.DraftType(draft.get())
                if extractor.StartDate(start.get()) == False:
                    result = False
                    result_string = "Invalid Start Date (YYYY-MM-DD)"
                    break
                if extractor.EndDate(end.get()) == False:
                    result = False
                    result_string = "Invalid End Date (YYYY-MM-DD)"
                    break
                extractor.Version(version)
                extractor.SessionColorRatings()
                result, result_string = extractor.RetrieveLocalArenaData()
                if result == False:
                    result, result_string = extractor.SessionScryfallData()
                    if result == False:
                        break
                progress['value']=10
                self.root.update()
                if extractor.Session17Lands(self.root, progress, progress['value']) == False:
                    result = False
                    result_string = "Couldn't Collect 17Lands Data"
                    break
                if extractor.ExportData() == False:
                    result = False
                    result_string = "File Write Failure"
                    break
                progress['value']=100
                button['state'] = 'normal'
                self.root.update()
                self.DataViewUpdate(list_box, sets)
                self.DraftReset(True)
                self.UpdateCallback(True)

            except Exception as error:
                result = False
                result_string = error
                print(error)
            break
        
        if result == False:
            button['state'] = 'normal'
            message_string = "Download Failed: %s" % result_string
            message_box = MessageBox.showwarning(title="Error", message=message_string)
        
    def DataViewUpdate(self, list_box, sets):
        #Delete the content of the list box
        for row in list_box.get_children():
                list_box.delete(row)
        self.root.update()
        file_list = FE.RetrieveLocalSetList(sets)
        
        for file in file_list:
            list_box.insert("", index = 0, values = file)
            
    def OnClickTable(self, event, table, card_list, selected_color):
        color_dict = {}
        for item in table.selection():
            card_name = table.item(item, "value")[0]
            for card in card_list:
                card_name = card_name if card_name[0] != '*' else card_name[1:]
                if card_name == card["name"]:
                    try:
                        non_color_options = ["All GIHWR", "All IWD", "All ALSA", "Tier"]
                        if set(selected_color).issubset(non_color_options):
                            color_list = ["All Decks"]
                        else:
                            color_list = selected_color
                        for count, color in enumerate(color_list):
                            try:
                                color_dict[color] = {}
                                
                                gihwr = card["deck_colors"][color]["gihwr"]
                                
                                if "gih" in card["deck_colors"][color]:
                                    gih = card["deck_colors"][color]["gih"]
                                    gihwr = CL.CalculateWinRate(card["deck_colors"][color], self.configuration.bayesian_average_enabled)
                                    color_dict[color]["gih"] = gih
                                
                                color_dict[color]["alsa"] = card["deck_colors"][color]["alsa"]
                                color_dict[color]["iwd"] = card["deck_colors"][color]["iwd"]
                                color_dict[color]["gihwr"] = gihwr
                                
                                if "curve_bonus" in card.keys() and len(card["curve_bonus"]):
                                    color_dict[color]["curve_bonus"] = card["curve_bonus"][count]
                                    
                                if "color_bonus" in card.keys()  and len(card["color_bonus"]):
                                    color_dict[color]["color_bonus"] = card["color_bonus"][count]
                                    
                            except Exception as error:
                                color_dict[color] = {"alsa" : 0,
                                                     "iwd" : 0,
                                                     "gihwr" : 0}
                            
                        tooltip = CreateCardToolTip(table, event,
                                                           card["name"],
                                                           color_dict,
                                                           card["image"],
                                                           self.configuration.images_enabled)
                    except Exception as error:
                        tooltip = CreateCardToolTip(table, event,
                                                           card["name"],
                                                           color_dict,
                                                           card["image"],
                                                           self.configuration.images_enabled)
                    break
    def FileOpen(self):
        filename = filedialog.askopenfilename(filetypes=(("Log Files", "*.log"),
                                                         ("All files", "*.*") ))
                                              
        if filename:
            self.filename = filename
            self.DraftReset(True)
            self.draft.ArenaFile(filename)
            self.draft.LogSuspend(True)
            self.UpdateCallback(True)
            self.draft.LogSuspend(False)
        
    def ControlTrace(self, enabled):
        if enabled:
            if len(self.trace_ids) == 0:
                self.trace_ids.append(self.column_2_selection.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.column_3_selection.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.column_4_selection.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.deck_stats_checkbox_value.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.missing_cards_checkbox_value.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.auto_highest_checkbox_value.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.curve_bonus_checkbox_value.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.color_bonus_checkbox_value.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.bayesian_average_checkbox_value.trace("w", self.UpdateSettingsCallback))
                self.trace_ids.append(self.data_source_selection.trace("w", self.UpdateSourceCallback))
                self.trace_ids.append(self.stat_options_selection.trace("w", self.UpdateDeckStatsCallback))
                self.trace_ids.append(self.draft_log_checkbox_value.trace("w", self.UpdateSettingsCallback))
        elif len(self.trace_ids):
           self.column_2_selection.trace_vdelete("w", self.trace_ids[0]) 
           self.column_3_selection.trace_vdelete("w", self.trace_ids[1]) 
           self.column_4_selection.trace_vdelete("w", self.trace_ids[2])
           self.deck_stats_checkbox_value.trace_vdelete("w", self.trace_ids[3])
           self.missing_cards_checkbox_value.trace_vdelete("w", self.trace_ids[4])
           self.auto_highest_checkbox_value.trace_vdelete("w", self.trace_ids[5])
           self.curve_bonus_checkbox_value.trace_vdelete("w", self.trace_ids[6])
           self.color_bonus_checkbox_value.trace_vdelete("w", self.trace_ids[7])
           self.bayesian_average_checkbox_value.trace_vdelete("w", self.trace_ids[8])
           self.data_source_selection.trace_vdelete("w", self.trace_ids[9])
           self.stat_options_selection.trace_vdelete("w", self.trace_ids[10])
           self.draft_log_checkbox_value.trace_vdelete("w", self.trace_ids[11])
           self.trace_ids = []
    def DraftReset(self, full_reset):
        self.draft.ClearDraft(full_reset)
        
    def VersionCheck(self):
        #Version Check
        update_flag = False
        if sys.platform == FE.PLATFORM_ID_WINDOWS:
            try:
                import win32api
                extractor = FE.FileExtractor()
                
                new_version_found, new_version = CheckVersion(extractor, __version__)
                if new_version_found:
                    message_string = "Update client %.2f to version %.2f" % (__version__, new_version)
                    message_box = MessageBox.askyesno(title="Update", message=message_string)
                    if message_box == True:
                        extractor.SessionRepositoryDownload("setup.exe")
                        self.root.destroy()
                        win32api.ShellExecute(0, "open", "setup.exe", None, None, 10)
    
                    else:
                        update_flag = True
                else:
                    update_flag = True
    
            except Exception as error:
                print(error)
                update_flag = True
        else:
            update_flag = True

        if update_flag:
           self.UpdateUI()
           self.ControlTrace(True)
    def EnableDeckStates(self, enable):
        try:
            if enable:
                self.stat_frame.grid(row=10, column = 0, columnspan = 2, sticky = 'nsew') 
                self.stat_table.grid(row=11, column = 0, columnspan = 2, sticky = 'nsew')
            else:
                self.stat_frame.grid_remove()
                self.stat_table.grid_remove()
        except Exception as error:
            self.stat_frame.grid(row=10, column = 0, columnspan = 2, sticky = 'nsew') 
            self.stat_table.grid(row=11, column = 0, columnspan = 2, sticky = 'nsew')
    def EnableMissingCards(self, enable):
        try:
            if enable:
                self.missing_frame.grid(row = 8, column = 0, columnspan = 2, sticky = 'nsew')
                self.missing_table_frame.grid(row = 9, column = 0, columnspan = 2, sticky = 'nsew')
            else:
                self.missing_frame.grid_remove()
                self.missing_table_frame.grid_remove()
        except Exception as error:
            self.missing_frame.grid(row = 8, column = 0, columnspan = 2, sticky = 'nsew')
            self.missing_table_frame.grid(row = 9, column = 0, columnspan = 2, sticky = 'nsew')
    
class CreateCardToolTip(object):
    def __init__(self, widget, event, card_name, color_dict, image, images_enabled):
        self.waittime = 1     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.card_name = card_name
        self.color_dict = color_dict
        self.image = image
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
            if sys.platform == FE.PLATFORM_ID_OSX:
               self.tw.wm_overrideredirect(False) 
            self.tw.wm_geometry("+%d+%d" % (x, y))
   
            tt_frame = Frame(self.tw, borderwidth=5,relief="solid")
            
            #Add scryfall image
            if self.images_enabled:
                from PIL import Image, ImageTk
                size = 280, 390
                self.images = []
                for count, picture in enumerate(self.image):
                    raw_data = urllib.request.urlopen(picture).read()
                    im = Image.open(io.BytesIO(raw_data))
                    im.thumbnail(size, Image.ANTIALIAS)
                    image = ImageTk.PhotoImage(im)
                    image_label = Label(tt_frame, image=image)
                    columnspan = 1 if len(self.image) == 2 else 2
                    image_label.grid(column=count, row=8, columnspan=columnspan)
                    self.images.append(image)
            

            card_label = Label(tt_frame, justify="left", text=self.card_name, font=("Consolas", 12, "bold"))

            filter_label = Label(tt_frame, justify="left", text="Filter:", font=("Consolas", 10, "bold"))
            filter_value = Label(tt_frame, text="/".join(self.color_dict.keys()), font=("Consolas", 10))

            alsa_values = [str(x['alsa']) for x in self.color_dict.values()]
            alsa_label = Label(tt_frame, justify="left", text="Average Last Seen At:", font=("Consolas", 10, "bold"))
            alsa_value = Label(tt_frame, text="/".join(alsa_values), font=("Consolas", 10))
            
            iwd_values = [str(x['iwd']) for x in self.color_dict.values()]
            iwd_label = Label(tt_frame, text="Improvement When Drawn:", font=("Consolas", 10, "bold"))
            iwd_value = Label(tt_frame, text="/".join(iwd_values) + "pp", font=("Consolas", 10))

            gihwr_values = [str(x['gihwr']) for x in self.color_dict.values()]
            gihwr_label = Label(tt_frame, text="Games In Hand Win Rate:", font=("Consolas", 10, "bold"))
            gihwr_value = Label(tt_frame, text="/".join(gihwr_values)+ "%", font=("Consolas", 10))
            
            if any("gih" in x for x in self.color_dict.values()):
                gih_values = [str(x['gih']) for x in self.color_dict.values()]
                gih_label = Label(tt_frame, text="Number of Games In Hand:", font=("Consolas", 10, "bold"))
                gih_value = Label(tt_frame, text="/".join(gih_values), font=("Consolas", 10))    
                gih_label.grid(column=0, row=5, columnspan=1)
                gih_value.grid(column=1, row=5, columnspan=1)
            
            if any("curve_bonus" in x for x in self.color_dict.values()):
                curve_bonus_values = [str(x['curve_bonus']) for x in self.color_dict.values()]
                curve_bonus_label = Label(tt_frame, text="Curve Bonus:", font=("Consolas", 10, "bold"))
                curve_bonus_value = Label(tt_frame, text="+" + "/".join(curve_bonus_values), font=("Consolas", 10))
                curve_bonus_label.grid(column=0, row=6, columnspan=1)
                curve_bonus_value.grid(column=1, row=6, columnspan=1)
                
            if any("color_bonus" in x for x in self.color_dict.values()):
                color_bonus_values = [str(x['color_bonus']) for x in self.color_dict.values()]
                color_bonus_label = Label(tt_frame, text="Color Bonus:", font=("Consolas", 10, "bold"))
                color_bonus_value = Label(tt_frame, text="+" + "/".join(color_bonus_values), font=("Consolas", 10))
                color_bonus_label.grid(column=0, row=7, columnspan=1)
                color_bonus_value.grid(column=1, row=7, columnspan=1)
                
            card_label.grid(column=0, row=0, columnspan=2)
            filter_label.grid(column=0, row=1, columnspan=1)
            filter_value.grid(column=1, row=1, columnspan=1)
            alsa_label.grid(column=0, row=2, columnspan=1)
            alsa_value.grid(column=1, row=2, columnspan=1)
            iwd_label.grid(column=0, row=3, columnspan=1)
            iwd_value.grid(column=1, row=3, columnspan=1)
            gihwr_label.grid(column=0, row=4, columnspan=1)
            gihwr_value.grid(column=1, row=4, columnspan=1)
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
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-f','--file')
    parser.add_argument('--step', action='store_true')
    
    args = parser.parse_args()
    
    window = Tk()
    window.title("Magic Draft %.2f" % __version__)
    
    if args.file is None:
        file_location = FE.ArenaLogLocation()
    else:
        file_location = args.file
        
    config = CL.ReadConfig()
    
    if sys.platform == FE.PLATFORM_ID_OSX:
        config.hotkey_enabled = False
        window.resizable(width = True, height = True)
    else:
        window.resizable(False, False) 
    
    ui = WindowUI(window, file_location, args.step, config)
    
    if config.hotkey_enabled:
        KeyListener(ui)    
    
    window.mainloop()
    
    
def main(argv):
    Startup(argv)
if __name__ == "__main__":
    main(sys.argv[1:])
  