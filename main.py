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
import json
import os
import time 
import getopt
import sys
import io
import functools
import file_extractor as FE
import card_logic as CL
import log_scanner as LS
from ttkwidgets.autocomplete import AutocompleteEntry

__version__= 2.61


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
    if key == KeyCode.from_char('\x06'): #CTRL+F
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
                            file_path = user_directory + user + LS.os_log_dict[os_type]
                            
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
    return file_location
    
def ReadConfig():
    hotkey_enabled = True
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
        config["card_logic"]["deck_types"]["Aggro"] = {"distribution" : [0,1,4,4,1,0,0], "maximum_card_count" : 24, "recommended_creature_count" : 17, "cmc_average" : 2.40}
        config["card_logic"]["deck_types"]["Control"] = {}
        config["card_logic"]["deck_types"]["Control"] = {"distribution" : [0,0,3,3,3,1,1], "maximum_card_count" : 22, "recommended_creature_count" : 14, "cmc_average" : 3.68}
    
        with open('config.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)
    except Exception as error:
        print("ResetConfig Error: %s" % error)

def TableFilterOptions(table, filter_a, filter_b, filter_c):
    non_color_options = ["All GIHWR", "All IWD", "All ALSA"]
    if filter_a == "All Decks":
        table.heading("FilterA", text = "All")
    elif filter_a in non_color_options:
        color, type = filter_a.split(" ")
        table.heading("FilterA", text = type)
    else:
        table.heading("FilterA", text = filter_a)
    if filter_b == "All Decks":
        table.heading("FilterB", text = "All")
    elif filter_b in non_color_options:
        color, type = filter_b.split(" ")
        table.heading("FilterB", text = type)
    else:
        table.heading("FilterB", text = filter_b)
    if filter_c == "All Decks":
        table.heading("FilterC", text = "All")
    elif filter_c in non_color_options:
        color, type = filter_c.split(" ")
        table.heading("FilterC", text = type)
    else:
        table.heading("FilterC", text = filter_c)

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
        
class WindowUI:
    def __init__(self, root, filename, step_through, diag_log_enabled, os, themes, images, table_width):
        self.root = root
        self.images_enabled = images
            
        self.filename = filename
        self.step_through = step_through
        self.diag_log_enabled = diag_log_enabled
        self.os = os
        self.draft = LS.LogScanner(self.filename, self.step_through, self.diag_log_enabled, self.os)
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
        self.datamenu.add_command(label="Settings", command=self.SettingsPopup)
        log_value_string = "Disable Log" if self.diag_log_enabled else "Enable Log"

        self.datamenu.add_command(label=log_value_string, command=self.ToggleLog)
        self.datamenu.add_command(label="Reset Config", command=ResetConfig)
        self.cardmenu = Menu(self.menubar, tearoff=0)
        self.cardmenu.add_command(label="Taken Cards", command=self.TakenCardsPopup)
        self.cardmenu.add_command(label="Suggest Decks", command=self.SuggestDeckPopup)
        self.cardmenu.add_command(label="Compare Cards", command=self.CardComparePopup)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.menubar.add_cascade(label="Data", menu=self.datamenu)
        self.menubar.add_cascade(label="Cards", menu=self.cardmenu)
        self.root.config(menu=self.menubar)
        
        style = Style()
        style.map("Treeview", 
                foreground=FixedMap(style, "foreground"),
                background=FixedMap(style, "background"))
                
        #self.current_draft_frame = Frame(self.root)
        self.current_draft_label = Label(self.root, text="Current Draft:", font='Helvetica 9 bold', anchor="e", width = 15)
        
        self.current_draft_value_label = Label(self.root, text="", font='Helvetica 9', anchor="w", width=17)
        
        #self.deck_colors_frame = Frame(self.root)
        self.deck_colors_label = Label(self.root, text="Deck Filter:", font='Helvetica 9 bold', anchor="e", width = 15)
        
        #self.deck_colors_options_selection = StringVar(self.root)
        #self.deck_colors_options_list = []
        self.column_2_selection = StringVar(self.root)
        self.column_2_list = self.draft.deck_colors
        self.column_2_selection.set("All ALSA")
        self.column_3_selection = StringVar(self.root)
        self.column_3_list = self.draft.deck_colors
        self.column_3_selection.set("All Decks")
        self.column_4_selection = StringVar(self.root)
        self.column_4_list = self.draft.deck_colors
        self.column_4_selection.set("Auto")
        optionsStyle = Style()
        optionsStyle.configure('my.TMenubutton', font=('Helvetica', 9))
        
        self.deck_colors_options = OptionMenu(self.root, self.column_4_selection, self.column_4_selection.get(), *self.column_4_list, style="my.TMenubutton")
        self.deck_colors_options.config(width=10)
        
        self.refresh_button_frame = Frame(self.root)
        self.refresh_button = Button(self.refresh_button_frame, command=self.UpdateCallback, text="Refresh");
        
        self.status_frame = Frame(self.root)
        self.pack_pick_label = Label(self.status_frame, text="Pack: 0, Pick: 0", font='Helvetica 9 bold')
        
        self.pack_table_frame = Frame(self.root, width=10)

        headers = {"Card"    : {"width" : .46, "anchor" : W},
                  "FilterA"  : {"width" : .18, "anchor" : CENTER},
                  "FilterB"  : {"width" : .18, "anchor" : CENTER},
                  "FilterC"  : {"width" : .18, "anchor" : CENTER}}
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
        
        #self.current_draft_frame.grid(row = 0, column = 0, columnspan = 2)
        #self.deck_colors_frame.grid(row = 1, column = 0, columnspan = 2)
        self.refresh_button_frame.grid(row = 2, column = 0, columnspan = 2, sticky = 'nsew')
        self.status_frame.grid(row = 3, column = 0, columnspan = 2, sticky = 'nsew')
        self.pack_table_frame.grid(row = 4, column = 0, columnspan = 2, sticky = 'nsew')
        self.missing_frame.grid(row = 5, column = 0, columnspan = 2, sticky = 'nsew')
        self.missing_table_frame.grid(row = 6, column = 0, columnspan = 2, sticky = 'nsew')
        self.stat_frame.grid(row=7, column = 0, columnspan = 2, sticky = 'nsew') 
        self.stat_table.grid(row=8, column = 0, columnspan = 2, sticky = 'nsew') 
        self.current_draft_label.grid(row = 0, column = 0, columnspan = 1, sticky = 'nsew')
        self.current_draft_value_label.grid(row = 0, column = 1, columnspan = 1, sticky = 'nsew')
        self.deck_colors_label.grid(row = 1, column = 0, columnspan = 1, sticky = 'nsew')
        self.deck_colors_options.grid(row = 1, column = 1, columnspan = 1, sticky = 'nsw')
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
        
        self.root.attributes("-topmost", True)
        
        #Version Check
        update_flag = False
        if self.os == "PC":
            try:
                import win32api
                DP = FE.DataPlatform(self.diag_log_file, self.diag_log_enabled)
                
                new_version_found, new_version = CheckVersion(DP, __version__)
                if new_version_found:
                    message_string = "Update client %.2f to version %.2f" % (__version__, new_version)
                    message_box = MessageBox.askyesno(title="Update", message=message_string)
                    if message_box == True:
                        DP.SessionRepositoryDownload("setup.exe")
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
           #self.deck_colors_options_selection.trace("w", self.UpdateCallback)  
           self.column_2_selection.trace("w", self.UpdateCallback) 
           self.column_3_selection.trace("w", self.UpdateCallback) 
           self.column_4_selection.trace("w", self.UpdateCallback) 


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
            error_string = "CreateHeader Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        return list_box

    def UpdatePackTable(self, card_list, taken_cards, filtered_a, filtered_b, filtered_c, color_options, limits):
        try:
            filtered_list = CL.CardFilter(card_list,
                                          taken_cards,
                                          filtered_a,
                                          filtered_b,
                                          filtered_c,
                                          color_options,
                                          limits)
                                          
            filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
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
            TableFilterOptions(self.pack_table, filtered_a, filtered_b, filtered_c)
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                
                self.pack_table.insert("",index = count, iid = count, values = (card["name"], card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
            self.pack_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.pack_table, card_list=card_list, selected_color=filtered_c))
        except Exception as error:
            error_string = "UpdatePackTable Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateMissingTable(self, current_pack, previous_pack, picked_cards, taken_cards, filtered_a, filtered_b, filtered_c, color_options, limits):
        try:
            for row in self.missing_table.get_children():
                self.missing_table.delete(row)
            self.root.update()
            
            #Update the filtered column header with the filtered colors
            TableFilterOptions(self.missing_table, filtered_a, filtered_b, filtered_c)

            if previous_pack != None:
                missing_cards = [x for x in previous_pack if x not in current_pack]
                
                list_length = len(missing_cards)
                
                if list_length:
                    self.missing_table.config(height = list_length)
                else:
                    self.missing_table.config(height=1) 
                
                if list_length:
                    filtered_list = CL.CardFilter(missing_cards,
                                                  taken_cards,
                                                  filtered_a,
                                                  filtered_b,
                                                  filtered_c,
                                                  color_options,
                                                  limits)
                    
                    filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
                    for count, card in enumerate(filtered_list):
                        row_tag = CL.RowColorTag(card["colors"])
                        card_name = "*" + card["name"] if card["name"] in picked_cards else card["name"]
                        
                        self.missing_table.insert("",index = count, iid = count, values = (card_name, card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
                    self.missing_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.missing_table, card_list=missing_cards, selected_color=filtered_c))
        except Exception as error:
            error_string = "UpdateMissingTable Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)

    def ClearCompareTable(self, compare_table, matching_cards):
        matching_cards.clear()
        compare_table.delete(*compare_table.get_children())

    def UpdateCompareTable(self, compare_table, matching_cards, entry_box, card_list, filtered_a, filtered_b, filtered_c, color_options,limits):
        try:
            added_card = entry_box.get()
            if len(added_card):
                cards = [card_list[x] for x in card_list if card_list[x]["name"] == added_card and card_list[x] not in matching_cards]
                matching_cards.extend(cards)
                entry_box.delete(0,END)

            filtered_list = CL.CardFilter(matching_cards,
                                          matching_cards,
                                          filtered_a,
                                          filtered_b,
                                          filtered_c,
                                          color_options,
                                          limits)
                    
            filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
            compare_table.delete(*compare_table.get_children())
            
            #Update the filtered column header with the filtered colors
            TableFilterOptions(compare_table, filtered_a, filtered_b, filtered_c)
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                compare_table.insert("",index = count, iid = count, values = (card["name"], card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
            compare_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=compare_table, card_list=matching_cards, selected_color=filtered_c))
        except Exception as error:
            error_string = "UpdateCompareTable Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled) 

    def UpdateTakenTable(self, taken_table, taken_cards, filtered_a, filtered_b, filtered_c, color_options,limits):
        try:
            
            filtered_list = CL.CardFilter(taken_cards,
                                          taken_cards,
                                          filtered_a,
                                          filtered_b,
                                          filtered_c,
                                          color_options,
                                          limits)
                    
            filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
            list_length = len(filtered_list)
            
            #Update the filtered column header with the filtered colors
            TableFilterOptions(taken_table, filtered_a, filtered_b, filtered_c)
                
            for count, card in enumerate(filtered_list):
                row_tag = CL.RowColorTag(card["colors"])
                taken_table.insert("",index = count, iid = count, values = (card["name"], card["rating_filter_a"], card["rating_filter_b"], card["rating_filter_c"]), tag = (row_tag,))
            taken_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=taken_table, card_list=taken_cards, selected_color=filtered_c))
        except Exception as error:
            error_string = "UpdateTakenTable Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
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
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
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
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdatePackPick(self, pack, pick):
        try:
            new_label = "Pack: %u, Pick: %u" % (pack, pick)
            self.pack_pick_label.config(text = new_label)
        
        except Exception as error:
            error_string = "UpdatePackPick Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)   
     
    def UpdateCurrentDraft(self, set, draft_type):
        try: 
            draft_type_string = ''
            
            for key, value in LS.draft_types_dict.items():
                if LS.draft_types_dict[key] == draft_type:
                    draft_type_string = key
                    
            new_label = "%s %s" % (set, draft_type_string)
            self.current_draft_value_label.config(text = new_label)
        
        except Exception as error:
            error_string = "UpdateCurrentDraft Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateOptions(self, options_list):
        try: 
            
            menu = self.deck_colors_options["menu"]
            menu.delete(0, "end")
            self.column_2_list = []
            self.column_3_list = []
            self.column_4_list = []

            for key, data in options_list.items():
                if len(data):
                    menu.add_command(label=data, 
                                    command=lambda value=data: self.column_4_selection.set(value))
                    #self.deck_colors_options_list.append(data)
                    self.column_2_list.append(data)
                    self.column_3_list.append(data)
                    self.column_4_list.append(data)
                
        except Exception as error:
            error_string = "UpdateOptions Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def UpdateCallback(self, *args):
        self.draft.DraftSearch()
        
        self.UpdateOptions(self.draft.deck_colors)
                
        filtered_a = CL.ColorFilter(self.draft.taken_cards, self.column_2_selection.get(), self.draft.deck_colors)
        filtered_b = CL.ColorFilter(self.draft.taken_cards, self.column_3_selection.get(), self.draft.deck_colors)
        filtered_c = CL.ColorFilter(self.draft.taken_cards, self.column_4_selection.get(), self.draft.deck_colors)

        self.UpdateCurrentDraft(self.draft.draft_set, self.draft.draft_type)
        self.UpdatePackPick(self.draft.current_pack, self.draft.current_pick)
        pack_index = (self.draft.current_pick - 1) % 8

        self.UpdatePackTable(self.draft.pack_cards[pack_index], 
                             self.draft.taken_cards,
                             filtered_a,
                             filtered_b,
                             filtered_c,
                             self.draft.deck_colors,
                             self.draft.deck_limits)
                             
        self.UpdateMissingTable(self.draft.pack_cards[pack_index],
                                self.draft.initial_pack[pack_index],
                                self.draft.picked_cards[pack_index],
                                self.draft.taken_cards,
                                filtered_a,
                                filtered_b,
                                filtered_c,
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
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
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
            DP = FE.DataPlatform(self.diag_log_file, self.diag_log_enabled)
            sets = DP.SessionSets()
        
            column_headers = ('Set', 'Draft', 'Start Date', 'End Date')
            list_box = Treeview(popup, columns = column_headers, show = 'headings')
            list_box.tag_configure('gray', background='#cccccc')
            list_box.tag_configure('bold', font=('Arial Bold', 10))
            
            set_label = Label(popup, text="Set:")
            draft_label = Label(popup, text="Draft:")
            start_label = Label(popup, text="Start Date:")
            end_label = Label(popup, text="End Date:")
            color_label = Label(popup, text="Color Rating:")
            id_label = Label(popup, text="Id:")
            draft_choices = ["QuickDraft", "PremierDraft", "TradDraft"]
            
            draft_value = StringVar(self.root)
            draft_value.set('QuickDraft')
            draft_entry = OptionMenu(popup, draft_value, draft_choices[0], *draft_choices)
            
            set_choices = [k for k, v in sets.items()]
            
            set_value = StringVar(self.root)
            set_value.set('QuickDraft')
            set_entry = OptionMenu(popup, set_value, set_choices[0], *set_choices)
            
            start_entry = Entry(popup)
            start_entry.insert(END, '2019-1-1')
            end_entry = Entry(popup)
            end_entry.insert(END, str(date.today()))
            id_entry = Entry(popup)
            id_entry.insert(END, 0)
            
            progress = Progressbar(popup,orient=HORIZONTAL,length=100,mode='determinate')
            
            color_checkbox_value = IntVar(value=1)
            color_checkbox = Checkbutton(popup,
                                         variable=color_checkbox_value,
                                         onvalue=1,
                                         offvalue=0)
            
            add_button = Button(popup, command=lambda: self.AddSet(DP,
                                                                   sets[set_value.get()],
                                                                   draft_value,
                                                                   start_entry,
                                                                   end_entry,
                                                                   add_button,
                                                                   progress,
                                                                   list_box,
                                                                   id_entry,
                                                                   color_checkbox_value,
                                                                   sets,
                                                                   2.00), text="ADD SET")
            
            
            for count, column in enumerate(column_headers):
                list_box.column(column, anchor = CENTER, stretch = YES, width = 100)
                list_box.heading(column, text = column, anchor = CENTER)
        except Exception as error:
            error_string = "SetViewPopup Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
        
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

        self.DataViewUpdate(list_box, sets)
        
        popup.attributes("-topmost", True)
        
    def CardComparePopup(self):
        popup = Toplevel()
        popup.wm_title("Card Compare")
        
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            
            filtered_a = CL.ColorFilter(self.draft.taken_cards, self.column_2_selection.get(), self.draft.deck_colors)
            filtered_b = CL.ColorFilter(self.draft.taken_cards, self.column_3_selection.get(), self.draft.deck_colors)
            filtered_c = CL.ColorFilter(self.draft.taken_cards, self.column_4_selection.get(), self.draft.deck_colors)
            
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
            compare_table = self.CreateHeader(compare_table_frame, 20, headers, self.table_width)
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
                                                                              filtered_a,
                                                                              filtered_b,
                                                                              filtered_c,
                                                                              self.draft.deck_colors,
                                                                              self.draft.deck_limits))
            
            popup.attributes("-topmost", True)
        except Exception as error:
            error_string = "CardComparePopup Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def TakenCardsPopup(self):
        popup = Toplevel()
        popup.wm_title("Taken Cards")
        
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            
            filtered_a = CL.ColorFilter(self.draft.taken_cards, self.column_2_selection.get(), self.draft.deck_colors)
            filtered_b = CL.ColorFilter(self.draft.taken_cards, self.column_3_selection.get(), self.draft.deck_colors)
            filtered_c = CL.ColorFilter(self.draft.taken_cards, self.column_4_selection.get(), self.draft.deck_colors)
            
            copy_button = Button(popup, command=lambda:CopyTaken(self.draft.taken_cards,
                                                                 self.draft.set_data,
                                                                 self.draft.draft_set,
                                                                 filtered_c),
                                                                 text="Copy to Clipboard")
            
            headers = {"Card"    : {"width" : .46, "anchor" : W},
                       "FilterA"  : {"width" : .18, "anchor" : CENTER},
                       "FilterB"  : {"width" : .18, "anchor" : CENTER},
                       "FilterC"  : {"width" : .18, "anchor" : CENTER}}
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
                                  filtered_a,
                                  filtered_b,
                                  filtered_c,
                                  self.draft.deck_colors,
                                  self.draft.deck_limits)
            popup.attributes("-topmost", True)
        except Exception as error:
            error_string = "TakenCards Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
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
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
    def SettingsPopup(self):
        popup = Toplevel()
        popup.wm_title("Settings")
        popup.geometry("210x75")
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            
            column_2_label = Label(popup, text="Column 2:", font='Helvetica 9 bold', anchor="w")
            column_3_label = Label(popup, text="Column 3:", font='Helvetica 9 bold', anchor="w")
            column_4_label = Label(popup, text="Column 4:", font='Helvetica 9 bold', anchor="w")
            
            optionsStyle = Style()
            optionsStyle.configure('my.TMenubutton', font=('Helvetica', 9))
            
            column_2_options = OptionMenu(popup, self.column_2_selection, self.column_2_selection.get(), *self.column_2_list, style="my.TMenubutton")
            column_2_options.config(width=10)
            
            column_3_options = OptionMenu(popup, self.column_3_selection, self.column_3_selection.get(), *self.column_3_list, style="my.TMenubutton")
            column_3_options.config(width=10)
            
            column_4_options = OptionMenu(popup, self.column_4_selection, self.column_4_selection.get(), *self.column_4_list, style="my.TMenubutton")
            column_4_options.config(width=10)
            
            column_2_label.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_3_label.grid(row=1, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_4_label.grid(row=2, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_2_options.grid(row=0, column=1, columnspan=1, sticky="nsew")
            column_3_options.grid(row=1, column=1, columnspan=1, sticky="nsew")
            column_4_options.grid(row=2, column=1, columnspan=1, sticky="nsew")
            
            
            popup.attributes("-topmost", True)
        except Exception as error:
            error_string = "ConfigPopup Error: %s" % error
            print(error_string)
            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled) 
        
    def AddSet(self, platform, set, draft, start, end, button, progress, list_box, id, color_rating, sets, version):
        button['state'] = 'disabled'
        progress['value'] = 0
        self.root.update()
        platform.Sets(set)
        platform.DraftType(draft.get())
        platform.StartDate(start.get())
        platform.EndDate(end.get())
        platform.ID(id.get())
        platform.Version(version)
        if color_rating.get():
            platform.SessionColorRatings()
        platform.SessionCardData()
        progress['value']=10
        self.root.update()
        if(platform.SessionCardRating(self.root, progress, progress['value'])):
            platform.ExportData()
            progress['value']=100
        else:
            progress['value']=0
        button['state'] = 'normal'
        self.root.update()
        self.DataViewUpdate(list_box, sets)
        self.DraftReset(True)
        self.UpdateCallback()
        
    def DataViewUpdate(self, list_box, sets):
        #Delete the content of the list box
        for row in list_box.get_children():
                list_box.delete(row)
        self.root.update()
        for directory, directory_names, filenames in os.walk(os.getcwd()):
            for filename in filenames:
                name_segments = filename.split("_")
                if len(name_segments) == 3:
                    if name_segments[1] in LS.draft_types_dict.keys():
                        #Retrieve the start and end dates
                        try:
                            print(sets.values())
                            main_sets = [v[0] for k, v in sets.items()]
                            print(main_sets)
                            set_name = list(sets.keys())[list(main_sets).index(name_segments[0].lower())]
                            json_data = {}
                            with open(filename, 'r') as json_file:
                                json_data = json_file.read()
                            json_data = json.loads(json_data)
                            if json_data["meta"]["version"] == 1:
                                print(json_data["meta"]["date_range"])
                                start_date, end_date = json_data["meta"]["date_range"].split("->")
                                list_box.insert("", index = 0, values = (set_name, name_segments[1], start_date, end_date))
                            elif json_data["meta"]["version"] == 2:
                                start_date = json_data["meta"]["start_date"] 
                                end_date = json_data["meta"]["end_date"] 
                                list_box.insert("", index = 0, values = (set_name, name_segments[1], start_date, end_date))
                        except Exception as error:
                            error_string = "DataViewUpdate Error: %s" % error
                            print(error_string)
                            LS.LogEntry(self.diag_log_file, error_string, self.diag_log_enabled)
            
            break
            
    def OnClickTable(self, event, table, card_list, selected_color):
        for item in table.selection():
            card_name = table.item(item, "value")[0]
            for card in card_list:
                card_name = card_name if card_name[0] != '*' else card_name[1:]
                if card_name == card["name"]:
                    try:
                        non_color_options = ["All GIHWR", "All IWD", "All ALSA"]
                        if selected_color in non_color_options:
                            color = "All Decks"
                        else:
                            color = selected_color
                        tooltip = CreateCardToolTip(table, event,
                                                           card["name"],
                                                           card["deck_colors"][color]["alsa"],
                                                           card["deck_colors"][color]["iwd"],
                                                           card["deck_colors"][color]["gihwr"],
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
        self.datamenu.entryconfigure(2, label=log_value_string)
        
    def DraftReset(self, full_reset):
        self.draft.ClearDraft(full_reset)
        #self.deck_colors_options_list = []
    
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
    window.title("Magic Draft %.2f" % __version__)
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
  