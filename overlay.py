from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog
from datetime import date
from pynput.keyboard import Key, Listener, KeyCode
import tkinter.messagebox as MessageBox
import urllib
import os
import sys
import io
import logging
import logging.handlers
import constants
import file_extractor as FE
import card_logic as CL
import log_scanner as LS
from ttkwidgets.autocomplete import AutocompleteEntry

if not os.path.exists(constants.DEBUG_LOG_FOLDER):
    os.makedirs(constants.DEBUG_LOG_FOLDER)

overlay_logger = logging.getLogger(constants.LOG_TYPE_DEBUG)
overlay_logger.setLevel(logging.INFO)
handlers = {
    logging.handlers.TimedRotatingFileHandler(constants.DEBUG_LOG_FILE, when='D', interval=1, backupCount=7, utc=True),
    logging.StreamHandler(sys.stdout),
}
formatter = logging.Formatter('%(asctime)s,%(message)s', datefmt='<%m/%d/%Y %H:%M:%S>')
for handler in handlers:
    handler.setFormatter(formatter)
    overlay_logger.addHandler(handler)
        
    
def CheckVersion(platform, version):
    return_value = False
    repository_version = platform.SessionRepositoryVersion()
    repository_version = int(repository_version)
    client_version = round(float(version) * 100)
    if repository_version > client_version:
        return_value = True
        
        
    repository_version = round(float(repository_version) / 100.0, 2)
    return return_value, repository_version

def FixedMap(style, option):
    # Returns the style map for 'option' with any styles starting with
    # ("!disabled", "!selected", ...) filtered out

    # style.map() returns an empty list for missing options, so this should
    # be future-safe
    return [elm for elm in style.map("Treeview", query_opt=option)
            if elm[:2] != ("!disabled", "!selected")]


def CopySuggested(deck_colors, deck, set_data, color_options):
    colors = color_options[deck_colors.get()]
    deck_string = ""
    try:
        deck_string = CL.CopyDeck(deck[colors]["deck_cards"],deck[colors]["sideboard_cards"],set_data["card_ratings"])
        CopyClipboard(deck_string)
    except Exception as error:
        overlay_logger.info(f"CopySuggested Error: {error}")
    return 
    
def CopyTaken(taken_cards, set_data):
    deck_string = ""
    try:
        stacked_cards = CL.StackCards(taken_cards)
        deck_string = CL.CopyDeck(stacked_cards, None, set_data["card_ratings"])
        CopyClipboard(deck_string)

    except Exception as error:
        overlay_logger.info(f"CopyTaken Error: {error}")
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
        overlay_logger.info(f"CopyClipboard Error: {error}")
    return 
    
def CreateHeader(frame, height, font, headers, total_width, include_header, fixed_width, table_style, stretch_enabled):
    header_labels = tuple(headers.keys())
    show_header = "headings" if include_header else ""
    column_stretch = YES if stretch_enabled else NO
    list_box = Treeview(frame, columns = header_labels, show = show_header, style = table_style)
    list_box.config(height=height)

    try:
        for k, v in constants.ROW_TAGS_BW_DICT.items():
            list_box.tag_configure(k, font=(v[0],font, "bold"), background=v[1], foreground=v[2])
            
        for k, v in constants.ROW_TAGS_COLORS_DICT.items():
            list_box.tag_configure(k, font=(v[0],font, "bold"), background=v[1], foreground=v[2])

        for column in header_labels:
            if fixed_width:
                list_box.column(column, stretch = column_stretch, anchor = headers[column]["anchor"], width = int(headers[column]["width"] * total_width))
            else:
                list_box.column(column, stretch = column_stretch, anchor = headers[column]["anchor"])
            list_box.heading(column, text = column, anchor = CENTER, command=lambda _col=column: TableColumnSort(list_box, _col, True))
        list_box["show"] = show_header  # use after setting column's size
    except Exception as error:
        overlay_logger.info(f"CreateHeader Error: {error}")
    return list_box
    
def TableRowTag(colors_enabled, colors, index):
    tag = ""
    
    if colors_enabled:
        tag = CL.RowColorTag(colors)
    else:
        tag = constants.BW_ROW_COLOR_ODD_TAG if index % 2 else constants.BW_ROW_COLOR_EVEN_TAG
    
    return tag
        
def TableColumnSort(table, column, reverse):
    row_colors = False
    
    try:
        row_list = [(float(table.set(k, column)), k) for k in table.get_children('')]
    except ValueError:
        row_list = [(table.set(k, column), k) for k in table.get_children('')]

    row_list.sort(key=lambda x: CL.FieldProcessSort(x[0]), reverse=reverse)

    if len(row_list):
        tags = table.item(row_list[0][1])["tags"][0]
        row_colors = True if tags in constants.ROW_TAGS_COLORS_DICT.keys() else False
    
    for index, (value, k) in enumerate(row_list):
        table.move(k, "", index)
        
        if not row_colors:
            row_tag = TableRowTag(False, "", index)
            table.item(k, tags=row_tag)

    table.heading(column, command=lambda: TableColumnSort(table, column, not reverse))
    
def SafeCoordinates(root, window_width, window_height, offset_x, offset_y):
    x = 0
    y = 0
    
    try:
        pointer_x = root.winfo_pointerx()
        pointer_y = root.winfo_pointery()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        if pointer_x + offset_x + window_width > screen_width:
            x = max(pointer_x - offset_x - window_width, 0)
        else:
            x = pointer_x + offset_x
            
        if pointer_y + offset_y + window_height > screen_height:
            y = max(pointer_y - offset_y - window_height, 0)
        else:
            y = pointer_y + offset_y   
    
    except Exception as error:
        overlay_logger.info(f"SafeCoordinates Error: {error}")
        
    return x, y

class Overlay:
    def __init__(self, version, args):
        self.root = Tk()
        self.version = version
        self.root.title("Magic Draft %.2f" % version)
        self.root.tk.call("source", "dark_mode.tcl")
        self.configuration = CL.ReadConfig()
        self.listener = None
        
        if args.file is None:
            self.arena_file = FE.ArenaLogLocation()
        else:
            self.arena_file = args.file
        overlay_logger.info(f"Player Log Location: {self.arena_file}")
        
        if args.data is None:
            self.data_file = FE.ArenaDirectoryLocation(self.arena_file)
        else:
            self.data_file = args.file
        overlay_logger.info(f"Card Data Location: {self.data_file}")
            
        self.step_through = args.step
        
        platform = sys.platform
        if platform == constants.PLATFORM_ID_OSX:
            self.configuration.hotkey_enabled = False
            self.root.resizable(width = True, height = True)
        else:
            self.root.resizable(False, False)
        overlay_logger.info(f"Platform: {platform}")            
        
        self.extractor = FE.FileExtractor(self.data_file)
        self.draft = LS.ArenaScanner(self.arena_file, self.step_through, self.extractor.SetList())
        
        self.trace_ids = []
        
        self.table_widths_dict = {
            constants.TABLE_MISSING : self.configuration.table_width,
            constants.TABLE_PACK    : self.configuration.table_width,
            constants.TABLE_COMPARE : self.configuration.table_width,
            constants.TABLE_STATS   : self.configuration.table_width,
            constants.TABLE_TAKEN   : 410,
            constants.TABLE_SUGGEST : 450,
            constants.TABLE_SETS    : 500
        }
        
        self.tier_data = {}
        self.main_options_dict = constants.COLUMNS_OPTIONS_EXTRA_DICT.copy()
        self.extra_options_dict = constants.COLUMNS_OPTIONS_EXTRA_DICT.copy()
        self.deck_colors = self.draft.RetrieveColorWinRate(self.configuration.filter_format)
        self.data_sources = self.draft.RetrieveDataSources()
        self.tier_sources = self.draft.RetrieveTierSource()
        self.set_metrics = self.draft.RetrieveSetMetrics(False)
        
        #Grid.rowconfigure(self.root, 9, weight = 1)
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
        self.current_draft_label = Label(current_draft_label_frame, text="Current Draft:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="e")
        
        current_draft_value_frame = Frame(self.root)
        self.current_draft_value_label = Label(current_draft_value_frame, text="", font=f'{constants.FONT_SANS_SERIF} 9', anchor="w")
        
        data_source_label_frame = Frame(self.root)
        self.data_source_label = Label(data_source_label_frame, text="Data Source:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="e")
        
        deck_colors_label_frame = Frame(self.root)
        self.deck_colors_label = Label(deck_colors_label_frame, text="Deck Filter:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="e")
        
        self.data_source_selection = StringVar(self.root)
        self.data_source_list = self.data_sources
        
        self.deck_stats_checkbox_value = IntVar(self.root)
        self.missing_cards_checkbox_value = IntVar(self.root)
        self.auto_highest_checkbox_value = IntVar(self.root)
        self.curve_bonus_checkbox_value = IntVar(self.root)
        self.color_bonus_checkbox_value = IntVar(self.root)
        self.bayesian_average_checkbox_value = IntVar(self.root)
        self.draft_log_checkbox_value = IntVar(self.root)
        self.taken_alsa_checkbox_value = IntVar(self.root)
        self.taken_ata_checkbox_value = IntVar(self.root)
        self.taken_gpwr_checkbox_value = IntVar(self.root)
        self.taken_ohwr_checkbox_value = IntVar(self.root)
        self.taken_gndwr_checkbox_value = IntVar(self.root)
        self.taken_iwd_checkbox_value = IntVar(self.root)
        self.card_colors_checkbox_value = IntVar(self.root)
        self.column_2_selection = StringVar(self.root)
        self.column_2_list = self.main_options_dict.keys()
        self.column_3_selection = StringVar(self.root)
        self.column_3_list = self.main_options_dict.keys()
        self.column_4_selection = StringVar(self.root)
        self.column_4_list = self.main_options_dict.keys()
        self.column_5_selection = StringVar(self.root)
        self.column_5_list = self.extra_options_dict.keys()
        self.column_6_selection = StringVar(self.root)
        self.column_6_list = self.extra_options_dict.keys()
        self.column_7_selection = StringVar(self.root)
        self.column_7_list = self.extra_options_dict.keys()
        self.filter_format_selection = StringVar(self.root)
        self.filter_format_list = constants.DECK_FILTER_FORMAT_LIST
        self.result_format_selection = StringVar(self.root)
        self.result_format_list = constants.RESULT_FORMAT_LIST
        self.deck_filter_selection = StringVar(self.root)
        self.deck_filter_list = self.deck_colors.keys()
        self.taken_filter_selection = StringVar(self.root)
        self.taken_type_selection = StringVar(self.root)

        optionsStyle = Style()
        optionsStyle.configure('my.TMenubutton', font=(constants.FONT_SANS_SERIF, 9))
        
        data_source_option_frame = Frame(self.root)
        self.data_source_options = OptionMenu(data_source_option_frame, self.data_source_selection, self.data_source_selection.get(), *self.data_source_list, style="my.TMenubutton")
        
        self.column_2_options = None
        self.column_3_options = None
        self.column_4_options = None
        self.column_5_options = None
        self.column_6_options = None
        self.column_7_options = None
        self.taken_table = None
        
        deck_colors_option_frame = Frame(self.root)
        self.deck_colors_options = OptionMenu(deck_colors_option_frame, self.deck_filter_selection, self.deck_filter_selection.get(), *self.deck_filter_list, style="my.TMenubutton")
        
        self.refresh_button_frame = Frame(self.root)
        self.refresh_button = Button(self.refresh_button_frame, command= lambda : self.UpdateCallback(True), text="Refresh")
        
        self.status_frame = Frame(self.root)
        self.pack_pick_label = Label(self.status_frame, text="Pack: 0, Pick: 0", font=f'{constants.FONT_SANS_SERIF} 9 bold')
        
        self.pack_table_frame = Frame(self.root, width=10)

        headers = {"Column1"  : {"width" : .46, "anchor" : W},
                   "Column2"  : {"width" : .18, "anchor" : CENTER},
                   "Column3"  : {"width" : .18, "anchor" : CENTER},
                   "Column4"  : {"width" : .18, "anchor" : CENTER},
                   "Column5"  : {"width" : .18, "anchor" : CENTER},
                   "Column6"  : {"width" : .18, "anchor" : CENTER},
                   "Column7"  : {"width" : .18, "anchor" : CENTER}}
        style = Style() 
        style.configure("TButton", foreground="black")  
        style.configure("TEntry", foreground="black") 
        style.configure("Treeview.Heading", font=(constants.FONT_SANS_SERIF, 7), foreground="black")        
                  
        self.pack_table = CreateHeader(self.pack_table_frame, 0, 7, headers, self.table_widths_dict[constants.TABLE_PACK], True, True, constants.TABLE_STYLE, False)
        
        self.missing_frame = Frame(self.root)
        self.missing_cards_label = Label(self.missing_frame, text = "Missing Cards", font=f'{constants.FONT_SANS_SERIF} 9 bold')
       
        self.missing_table_frame = Frame(self.root, width=10)

        self.missing_table = CreateHeader(self.missing_table_frame, 0, 7, headers, self.table_widths_dict[constants.TABLE_MISSING], True, True, constants.TABLE_STYLE, False)
        
        self.stat_frame = Frame(self.root)

        self.stat_table = CreateHeader(self.root, 0, 7, constants.STATS_HEADER_CONFIG, self.table_widths_dict[constants.TABLE_STATS], True, True, constants.TABLE_STYLE, False)
        self.stat_label = Label(self.stat_frame, text = "Draft Stats:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="e", width = 15)

        self.stat_options_selection = StringVar(self.root)
        self.stat_options_list = [constants.CARD_TYPE_SELECTION_CREATURES,constants.CARD_TYPE_SELECTION_NONCREATURES,constants.CARD_TYPE_SELECTION_ALL]
        
        self.stat_options = OptionMenu(self.stat_frame, self.stat_options_selection, self.stat_options_list[0], *self.stat_options_list, style="my.TMenubutton")
        self.stat_options.config(width=11) 
        
        citation_label = Label(self.root, text="Powered by 17Lands*", font=f'{constants.FONT_SANS_SERIF} 9 ', anchor="e", borderwidth=2, relief="groove")
        hotkey_label = Label(self.root, text="CTRL+G to Minimize", font=f'{constants.FONT_SANS_SERIF} 8 ', anchor="e" )
        footnote_label = Label(self.root, text="*This application is not endorsed by 17Lands", font=f'{constants.FONT_SANS_SERIF} 8 ', anchor="e")
        
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
        self.pack_table_frame.grid(row = 7, column = 0, columnspan = 2)
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
        self.InitializeUI()
        self.VersionCheck()
        
        if self.configuration.hotkey_enabled:
            self.HotkeyListener()
        
    def HotkeyListener(self):
        self.listener = Listener(on_press=lambda event: self.HotkeyPress(event)).start()
        
    def HotkeyPress(self, key):
        if key == KeyCode.from_char(constants.HOTKEY_CTRL_G):
            self.WindowLift()
        
    def MainLoop(self):
        self.root.mainloop()
        
    def DeckFilterColors(self, cards, selected_option):
        filtered_colors = [constants.FILTER_OPTION_ALL_DECKS]

        try:
            #selected_option = self.deck_filter_selection.get()
            selected_color = self.deck_colors[selected_option]
            filtered_colors = CL.OptionFilter(cards, selected_color, self.set_metrics, self.configuration)

            if selected_color == constants.FILTER_OPTION_AUTO:
                new_key = f"{constants.FILTER_OPTION_AUTO} ({'/'.join(filtered_colors)})"
                if new_key != selected_option:
                    self.deck_colors.pop(selected_option)
                    new_dict = {new_key : constants.FILTER_OPTION_AUTO}
                    new_dict.update(self.deck_colors)
                    self.deck_colors = new_dict
                    self.UpdateColumnOptions() 

        except Exception as error:
            overlay_logger.info(f"DeckFilterColors Error: {error}")
            
        return filtered_colors
        
    def UpdatePackTable(self, card_list, taken_cards, filtered_colors, fields):
        try:
            filtered_list = CL.CardFilter(card_list,
                                          taken_cards,
                                          filtered_colors,
                                          fields,
                                          self.set_metrics,
                                          self.tier_data,
                                          self.configuration,
                                          self.configuration.curve_bonus_enabled,
                                          self.configuration.color_bonus_enabled)
                                          
            # clear the previous rows
            for row in self.pack_table.get_children():
                self.pack_table.delete(row)
            
            list_length = len(filtered_list)
            
            if list_length:
                self.pack_table.config(height = list_length)
            else:
                self.pack_table.config(height=0)
                
            #Update the filtered column header with the filtered colors
            last_field_index = self.TableColumnControl(self.pack_table, fields, constants.TABLE_PACK)
            
            filtered_list = sorted(filtered_list, key=lambda d: CL.FieldProcessSort(d["results"][last_field_index]), reverse=True) 
                
            for count, card in enumerate(filtered_list):
                row_tag = TableRowTag(self.configuration.card_colors_enabled, card[constants.DATA_FIELD_COLORS], count)
                field_values = tuple(card["results"])
                self.pack_table.insert("",index = count, iid = count, values = field_values, tag = (row_tag,))
            self.pack_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.pack_table, card_list=card_list, selected_color=filtered_colors))
        except Exception as error:
            overlay_logger.info(f"UpdatePackTable Error: {error}")
            
    def UpdateMissingTable(self, current_pack, previous_pack, picked_cards, taken_cards, filtered_colors, fields):
        try:
            for row in self.missing_table.get_children():
                self.missing_table.delete(row)
            
            #Update the filtered column header with the filtered colors
            last_field_index = self.TableColumnControl(self.missing_table, fields, constants.TABLE_MISSING)
            if len(previous_pack) == 0:
                self.missing_table.config(height=0)
            else:
                missing_cards = [x for x in previous_pack if x not in current_pack]
                
                list_length = len(missing_cards)
                
                if list_length:
                    self.missing_table.config(height = list_length)
                else:
                    self.missing_table.config(height=0) 
                
                if list_length:
                    filtered_list = CL.CardFilter(missing_cards,
                                                  taken_cards,
                                                  filtered_colors,
                                                  fields,
                                                  self.set_metrics,
                                                  self.tier_data,
                                                  self.configuration,
                                                  False,
                                                  False)
                    
                    filtered_list = sorted(filtered_list, key=lambda d: CL.FieldProcessSort(d["results"][last_field_index]), reverse=True) 

                    #filtered_list.sort(key = functools.cmp_to_key(CL.CompareRatings))
                    for count, card in enumerate(filtered_list):
                        row_tag = TableRowTag(self.configuration.card_colors_enabled, card[constants.DATA_FIELD_COLORS], count)
                        for index, field in enumerate(fields.values()):
                            if field == constants.DATA_FIELD_NAME:
                                card["results"][index] = f'*{card["results"][index]}' if card["results"][index] in picked_cards else card["results"][index]
                        field_values = tuple(card["results"])
                        self.missing_table.insert("",index = count, iid = count, values = field_values, tag = (row_tag,))
                    self.missing_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.missing_table, card_list=missing_cards, selected_color=filtered_colors))
        except Exception as error:
            overlay_logger.info(f"UpdateMissingTable Error: {error}")

    def ClearCompareTable(self, compare_table, matching_cards):
        matching_cards.clear()
        compare_table.delete(*compare_table.get_children())
        compare_table.config(height=0)

    def UpdateCompareTable(self, compare_table, matching_cards, entry_box, card_list, filtered_colors, fields):
        try:
            added_card = entry_box.get()
            if len(added_card):
                cards = [card_list[x] for x in card_list if card_list[x][constants.DATA_FIELD_NAME] == added_card and card_list[x] not in matching_cards]
                entry_box.delete(0,END)
                if len(cards):
                    matching_cards.append(cards[0])

            filtered_list = CL.CardFilter(matching_cards,
                                          matching_cards,
                                          filtered_colors,
                                          fields,
                                          self.set_metrics,
                                          self.tier_data,
                                          self.configuration,
                                          False,
                                          False)
                    
            compare_table.delete(*compare_table.get_children())

                        #Update the filtered column header with the filtered colors
            last_field_index = self.TableColumnControl(compare_table, fields, constants.TABLE_COMPARE)

            filtered_list = sorted(filtered_list, key=lambda d: CL.FieldProcessSort(d["results"][last_field_index]), reverse=True) 
            
            list_length = len(filtered_list)
            
            if list_length:
                compare_table.config(height = list_length)
            else:
                compare_table.config(height=0)
                
            for count, card in enumerate(filtered_list):
                row_tag = TableRowTag(self.configuration.card_colors_enabled, card[constants.DATA_FIELD_COLORS], count)
                field_values = tuple(card["results"])
                compare_table.insert("",index = count, iid = count, values = field_values, tag = (row_tag,))
            compare_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=compare_table, card_list=matching_cards, selected_color=filtered_colors))
        except Exception as error:
            overlay_logger.info(f"UpdateCompareTable Error: {error}")

    def UpdateTakenTable(self, *args):
        try:
            while(True):
                if self.taken_table == None:
                    break

                fields = {"Column1"    : constants.DATA_FIELD_NAME,
                          "Column2"    : constants.DATA_FIELD_COUNT,
                          "Column3"    : constants.DATA_FIELD_COLORS,
                          "Column4"    : (constants.DATA_FIELD_ALSA if self.taken_alsa_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column5"    : (constants.DATA_FIELD_ATA if self.taken_ata_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column6"    : (constants.DATA_FIELD_IWD if self.taken_iwd_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column7"    : (constants.DATA_FIELD_GPWR if self.taken_gpwr_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column8"    : (constants.DATA_FIELD_OHWR if self.taken_ohwr_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column9"    : (constants.DATA_FIELD_GNDWR if self.taken_gndwr_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column10"   : constants.DATA_FIELD_GIHWR}

                taken_cards = self.draft.TakenCards()
                
                filtered_colors = self.DeckFilterColors(taken_cards, self.taken_filter_selection.get())
                
                #Filter the card types
                #filtered_cards = CL.DeckColorSearch(taken_cards, constants.CARD_COLORS_DICT.values(), constants.CARD_TYPE_DICT[self.taken_type_selection.get()], True, True, True) 
                
                stacked_cards = CL.StackCards(taken_cards)

                for row in self.taken_table.get_children():
                    self.taken_table.delete(row)

                filtered_list = CL.CardFilter(stacked_cards,
                                              taken_cards,
                                              filtered_colors,
                                              fields,
                                              self.set_metrics,
                                              self.tier_data,
                                              self.configuration,
                                              False,
                                              False)

                last_field_index = self.TableColumnControl(self.taken_table, fields, constants.TABLE_TAKEN)

                filtered_list = sorted(filtered_list, key=lambda d: CL.FieldProcessSort(d["results"][last_field_index]), reverse=True)  

                if len(filtered_list):
                    self.taken_table.config(height = min(len(filtered_list), 20))
                else:
                    self.taken_table.config(height=1)

                for count, card in enumerate(filtered_list):
                    field_values = tuple(card["results"])
                    row_tag = TableRowTag(self.configuration.card_colors_enabled, card[constants.DATA_FIELD_COLORS], count)
                    self.taken_table.insert("",index = count, iid = count, values = field_values, tag = (row_tag,))
                self.taken_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=self.taken_table, card_list=filtered_list, selected_color=filtered_colors))
                break
        except Exception as error:
            overlay_logger.info(f"UpdateTakenTable Error: {error}")
            
    def UpdateSuggestDeckTable(self, suggest_table, selected_color, suggested_decks, color_options):
        try:             
            color = color_options[selected_color.get()]
            suggested_deck = suggested_decks[color]["deck_cards"]
            suggested_deck.sort(key=lambda x : x[constants.DATA_FIELD_CMC], reverse = False)
            for row in suggest_table.get_children():
                suggest_table.delete(row)

            list_length = len(suggested_deck)
            if list_length:
                suggest_table.config(height = list_length)
            else:
                suggest_table.config(height=0)
            
            for count, card in enumerate(suggested_deck):
                row_tag = TableRowTag(self.configuration.card_colors_enabled, card[constants.DATA_FIELD_COLORS], count)
                suggest_table.insert("",index = count, values = (card[constants.DATA_FIELD_NAME],
                                                                 "%d" % card[constants.DATA_FIELD_COUNT],
                                                                 card[constants.DATA_FIELD_COLORS],
                                                                 card[constants.DATA_FIELD_CMC],
                                                                 card[constants.DATA_FIELD_TYPES]), tag = (row_tag,))
            suggest_table.bind("<<TreeviewSelect>>", lambda event: self.OnClickTable(event, table=suggest_table, card_list=suggested_deck, selected_color=[color]))
    
        except Exception as error:
            overlay_logger.info(f"UpdateSuggestTable Error: {error}")
            
    def UpdateDeckStatsTable(self, taken_cards, filter_type, total_width):
        try:             
            filter = constants.CARD_TYPE_DICT[filter_type]

            #colors = {constants.CARD_COLOR_LABEL_BLACK:constants.CARD_COLOR_SYMBOL_BLACK,constants.CARD_COLOR_LABEL_BLUE:constants.CARD_COLOR_SYMBOL_BLUE, constants.CARD_COLOR_LABEL_GREEN:constants.CARD_COLOR_SYMBOL_GREEN, constants.CARD_COLOR_LABEL_RED:constants.CARD_COLOR_SYMBOL_RED, constants.CARD_COLOR_LABEL_WHITE:constants.CARD_COLOR_SYMBOL_WHITE, constants.CARD_COLOR_SYMBOL_NONE:""}
            colors_filtered = {}
            for color,symbol in constants.CARD_COLORS_DICT.items():
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

            #Adjust the width for each column
            for column in self.stat_table["columns"]:
                self.stat_table.column(column, width = int(constants.STATS_HEADER_CONFIG[column]["width"] * total_width))

            list_length = len(colors_filtered)
            if list_length:
                self.stat_table.config(height = list_length)
            else:
                self.stat_table.config(height=0)
            
            count = 0
            for count, (color, values) in enumerate(colors_filtered.items()):
                #row_tag = CL.RowColorTag(values["symbol"])
                row_tag = TableRowTag(self.configuration.card_colors_enabled, values["symbol"], count)
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
            overlay_logger.info(f"UpdateDeckStats Error: {error}")
            
    def UpdatePackPick(self, pack, pick):
        try:
            new_label = "Pack: %u, Pick: %u" % (pack, pick)
            self.pack_pick_label.config(text = new_label)
        
        except Exception as error:
            overlay_logger.info(f"UpdatePackPick Error: {error}")
     
    def UpdateCurrentDraft(self, set, draft_type):
        try: 
            draft_type_string = ''
            
            for key, value in constants.LIMITED_TYPES_DICT.items():
                if constants.LIMITED_TYPES_DICT[key] == draft_type:
                    draft_type_string = key
                    
            new_label = f" {set[0]} {draft_type_string}" if set else " None"
            self.current_draft_value_label.config(text = new_label)
        except Exception as error:
            overlay_logger.info(f"UpdateCurrentDraft Error: {error}")
     
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
            overlay_logger.info(f"UpdateSourceOptions Error: {error}")
            
        self.ControlTrace(True)
     
    def UpdateColumnOptions(self):
        self.ControlTrace(False)
        try: 
            if self.filter_format_selection.get() not in self.filter_format_list:
                self.filter_format_selection.set(constants.DECK_FILTER_FORMAT_COLORS)
            if self.result_format_selection.get() not in self.result_format_list:
                self.result_format_selection.set(constants.RESULT_FORMAT_WIN_RATE)
            if self.column_2_selection.get() not in self.main_options_dict.keys():
                self.column_2_selection.set(constants.COLUMN_2_DEFAULT)
            if self.column_3_selection.get() not in self.main_options_dict.keys():
                self.column_3_selection.set(constants.COLUMN_3_DEFAULT)
            if self.column_4_selection.get() not in self.main_options_dict.keys():
                self.column_4_selection.set(constants.COLUMN_4_DEFAULT)
            if self.column_5_selection.get() not in self.extra_options_dict.keys():
                self.column_5_selection.set(constants.COLUMN_5_DEFAULT)
            if self.column_6_selection.get() not in self.extra_options_dict.keys():
                self.column_6_selection.set(constants.COLUMN_6_DEFAULT)
            if self.column_7_selection.get() not in self.extra_options_dict.keys():
                self.column_7_selection.set(constants.COLUMN_7_DEFAULT)
            if self.deck_filter_selection.get() not in self.deck_colors.keys():
                selection = [k for k in self.deck_colors.keys() if constants.DECK_FILTER_DEFAULT in k]
                self.deck_filter_selection.set(selection[0] if len(selection) else constants.DECK_FILTER_DEFAULT)
            if self.taken_filter_selection.get() not in self.deck_colors.keys():
                selection = [k for k in self.deck_colors.keys() if constants.DECK_FILTER_DEFAULT in k]
                self.taken_filter_selection.set(selection[0] if len(selection) else constants.DECK_FILTER_DEFAULT)       
            if self.taken_type_selection.get() not in constants.CARD_TYPE_DICT.keys():
                self.taken_type_selection.set(constants.CARD_TYPE_SELECTION_ALL)                   
            
            deck_colors_menu = self.deck_colors_options["menu"]
            deck_colors_menu.delete(0, "end")
            column_2_menu = None
            column_3_menu = None
            column_4_menu = None
            column_5_menu = None
            column_6_menu = None
            column_7_menu = None
            if self.column_2_options:
                column_2_menu = self.column_2_options["menu"]
                column_2_menu.delete(0, "end")
            if self.column_3_options:
                column_3_menu = self.column_3_options["menu"]
                column_3_menu.delete(0, "end")
            if self.column_4_options:
                column_4_menu = self.column_4_options["menu"]
                column_4_menu.delete(0, "end")
            if self.column_5_options:
                column_5_menu = self.column_5_options["menu"]
                column_5_menu.delete(0, "end")
            if self.column_6_options:
                column_6_menu = self.column_6_options["menu"]
                column_6_menu.delete(0, "end")
            if self.column_7_options:
                column_7_menu = self.column_7_options["menu"]
                column_7_menu.delete(0, "end")
            self.column_2_list = []
            self.column_3_list = []
            self.column_4_list = []
            self.column_5_list = []
            self.column_6_list = []
            self.column_7_list = []
            self.deck_filter_list = []

            for key in self.main_options_dict.keys():
                if column_2_menu:
                    column_2_menu.add_command(label=key, 
                                    command=lambda value=key: self.column_2_selection.set(value))
                if column_3_menu:
                    column_3_menu.add_command(label=key, 
                                    command=lambda value=key: self.column_3_selection.set(value))
                if column_4_menu:
                    column_4_menu.add_command(label=key, 
                                    command=lambda value=key: self.column_4_selection.set(value))

                #self.deck_colors_options_list.append(data)
                self.column_2_list.append(key)
                self.column_3_list.append(key)
                self.column_4_list.append(key)
                
            for key in self.extra_options_dict.keys():
                if column_5_menu:
                    column_5_menu.add_command(label=key, 
                                    command=lambda value=key: self.column_5_selection.set(value))
                if column_6_menu:
                    column_6_menu.add_command(label=key, 
                                    command=lambda value=key: self.column_6_selection.set(value))

                if column_7_menu:
                    column_7_menu.add_command(label=key, 
                                    command=lambda value=key: self.column_7_selection.set(value))
                                    
                self.column_5_list.append(key)
                self.column_6_list.append(key)
                self.column_7_list.append(key)
                
            for key in self.deck_colors.keys():
                deck_colors_menu.add_command(label=key, 
                                command=lambda value=key: self.deck_filter_selection.set(value))
                self.deck_filter_list.append(key)
                
        except Exception as error:
            overlay_logger.info(f"UpdateColumnOptions Error: {error}")
            
        self.ControlTrace(True)
        
    def DefaultSettingsCallback(self, *args):
        CL.ResetConfig()
        self.configuration = CL.ReadConfig()
        self.UpdateSettingsData()
        self.UpdateDraftData()
        self.UpdateCallback(False)            

    def UpdateSourceCallback(self, *args):
        self.UpdateSettingsStorage()
        self.UpdateDraftData()
        self.UpdateSettingsData()
        self.UpdateCallback(False) 

    def UpdateSettingsCallback(self, *args):
        self.UpdateSettingsStorage()
        self.UpdateSettingsData()
        self.UpdateCallback(False)     
        
    def UpdateDraftData(self):
        self.draft.RetrieveSetData(self.data_sources[self.data_source_selection.get()])
        self.set_metrics = self.draft.RetrieveSetMetrics(False)
        self.deck_colors = self.draft.RetrieveColorWinRate(self.filter_format_selection.get())
        self.tier_data, tier_dict = self.draft.RetrieveTierData(self.tier_sources)
        self.main_options_dict = constants.COLUMNS_OPTIONS_EXTRA_DICT.copy()
        self.extra_options_dict = constants.COLUMNS_OPTIONS_EXTRA_DICT.copy()
        for key, value in tier_dict.items():
            self.main_options_dict[key] = value
            self.extra_options_dict[key] = value
        
    def UpdateDraft(self):
        update = False
        if self.draft.DraftStartSearch():
            update = True
            self.data_sources = self.draft.RetrieveDataSources()
            self.tier_sources = self.draft.RetrieveTierSource()
            self.UpdateSourceOptions(True)
            self.UpdateDraftData()

        if self.draft.DraftDataSearch():
            update = True
        return update

    def UpdateSettingsStorage(self):
        try:
            selection = self.column_2_selection.get()
            self.configuration.column_2 = self.main_options_dict[selection] if selection in self.main_options_dict else self.main_options_dict[constants.COLUMN_2_DEFAULT]
            selection = self.column_3_selection.get()
            self.configuration.column_3 = self.main_options_dict[selection] if selection in self.main_options_dict else self.main_options_dict[constants.COLUMN_3_DEFAULT]
            selection = self.column_4_selection.get()
            self.configuration.column_4 = self.main_options_dict[selection] if selection in self.main_options_dict else self.main_options_dict[constants.COLUMN_4_DEFAULT]
            selection = self.column_5_selection.get()
            self.configuration.column_5 = self.extra_options_dict[selection] if selection in self.extra_options_dict else self.extra_options_dict[constants.COLUMN_5_DEFAULT]
            selection = self.column_6_selection.get()
            self.configuration.column_6 = self.extra_options_dict[selection] if selection in self.extra_options_dict else self.extra_options_dict[constants.COLUMN_6_DEFAULT]
            selection = self.column_7_selection.get()
            self.configuration.column_7 = self.extra_options_dict[selection] if selection in self.extra_options_dict else self.extra_options_dict[constants.COLUMN_7_DEFAULT]
            selection = self.deck_filter_selection.get()
            self.configuration.deck_filter = self.deck_colors[selection] if selection in self.deck_colors else self.deck_colors[constants.DECK_FILTER_DEFAULT]
            self.configuration.filter_format = self.filter_format_selection.get()
            self.configuration.result_format = self.result_format_selection.get()

            self.configuration.missing_enabled = bool(self.missing_cards_checkbox_value.get())
            self.configuration.stats_enabled = bool(self.deck_stats_checkbox_value.get())
            self.configuration.auto_highest_enabled = bool(self.auto_highest_checkbox_value.get())
            self.configuration.curve_bonus_enabled = bool(self.curve_bonus_checkbox_value.get())
            self.configuration.color_bonus_enabled = bool(self.color_bonus_checkbox_value.get())
            self.configuration.bayesian_average_enabled = bool(self.bayesian_average_checkbox_value.get())
            self.configuration.draft_log_enabled = bool(self.draft_log_checkbox_value.get())
            self.configuration.taken_alsa_enabled = bool(self.taken_alsa_checkbox_value.get())
            self.configuration.taken_ata_enabled = bool(self.taken_ata_checkbox_value.get())
            self.configuration.taken_gpwr_enabled = bool(self.taken_gpwr_checkbox_value.get())
            self.configuration.taken_ohwr_enabled = bool(self.taken_ohwr_checkbox_value.get())
            self.configuration.taken_iwd_enabled = bool(self.taken_iwd_checkbox_value.get())
            self.configuration.taken_gndwr_enabled = bool(self.taken_gndwr_checkbox_value.get())
            self.configuration.card_colors_enabled = bool(self.card_colors_checkbox_value.get())
            CL.WriteConfig(self.configuration)
        except Exception as error:
            overlay_logger.info(f"UpdateSettingsStorage Error: {error}")
            
    def UpdateSettingsData(self):
        self.ControlTrace(False)
        try:
            selection = [k for k,v in self.main_options_dict.items() if v == self.configuration.column_2]
            self.column_2_selection.set(selection[0] if len(selection) else constants.COLUMN_2_DEFAULT)
            selection = [k for k,v in self.main_options_dict.items() if v == self.configuration.column_3]
            self.column_3_selection.set(selection[0] if len(selection) else constants.COLUMN_3_DEFAULT)
            selection = [k for k,v in self.main_options_dict.items() if v == self.configuration.column_4]
            self.column_4_selection.set(selection[0] if len(selection) else constants.COLUMN_4_DEFAULT)
            selection = [k for k,v in self.extra_options_dict.items() if v == self.configuration.column_5]
            self.column_5_selection.set(selection[0] if len(selection) else constants.COLUMN_5_DEFAULT)
            selection = [k for k,v in self.extra_options_dict.items() if v == self.configuration.column_6]
            self.column_6_selection.set(selection[0] if len(selection) else constants.COLUMN_6_DEFAULT)
            selection = [k for k,v in self.extra_options_dict.items() if v == self.configuration.column_7]
            self.column_7_selection.set(selection[0] if len(selection) else constants.COLUMN_7_DEFAULT)
            selection = [k for k,v in self.deck_colors.items() if v == self.configuration.deck_filter]
            self.deck_filter_selection.set(selection[0] if len(selection) else constants.DECK_FILTER_DEFAULT)
            self.filter_format_selection.set(self.configuration.filter_format)
            self.result_format_selection.set(self.configuration.result_format)
            self.deck_stats_checkbox_value.set(self.configuration.stats_enabled)
            self.missing_cards_checkbox_value.set(self.configuration.missing_enabled)
            self.auto_highest_checkbox_value.set(self.configuration.auto_highest_enabled)
            self.curve_bonus_checkbox_value.set(self.configuration.curve_bonus_enabled)
            self.color_bonus_checkbox_value.set(self.configuration.color_bonus_enabled)
            self.bayesian_average_checkbox_value.set(self.configuration.bayesian_average_enabled)
            self.draft_log_checkbox_value.set(self.configuration.draft_log_enabled)
            self.taken_alsa_checkbox_value.set(self.configuration.taken_alsa_enabled)
            self.taken_ata_checkbox_value.set(self.configuration.taken_ata_enabled)
            self.taken_gpwr_checkbox_value.set(self.configuration.taken_gpwr_enabled)
            self.taken_ohwr_checkbox_value.set(self.configuration.taken_ohwr_enabled)
            self.taken_gndwr_checkbox_value.set(self.configuration.taken_gndwr_enabled)
            self.taken_iwd_checkbox_value.set(self.configuration.taken_iwd_enabled)
            self.card_colors_checkbox_value.set(self.configuration.card_colors_enabled)
        except Exception as error:
            self.column_2_selection.set(constants.COLUMN_2_DEFAULT) 
            self.column_3_selection.set(constants.COLUMN_3_DEFAULT)
            self.column_4_selection.set(constants.COLUMN_4_DEFAULT)
            self.column_5_selection.set(constants.COLUMN_5_DEFAULT)
            self.column_6_selection.set(constants.COLUMN_6_DEFAULT)
            self.column_7_selection.set(constants.COLUMN_7_DEFAULT)
            self.deck_filter_selection.set(constants.DECK_FILTER_DEFAULT)
            self.deck_stats_checkbox_value.set(False)
            self.missing_cards_checkbox_value.set(False)
            self.auto_highest_checkbox_value.set(False)
            self.curve_bonus_checkbox_value.set(False)
            self.color_bonus_checkbox_value.set(False)
            self.bayesian_average_checkbox_value.set(False)
            self.draft_log_checkbox_value.set(False)
            self.taken_alsa_checkbox_value.set(True)
            self.taken_ata_checkbox_value.set(True)
            self.taken_gpwr_checkbox_value.set(True)
            self.taken_ohwr_checkbox_value.set(True)
            self.taken_gndwr_checkbox_value.set(True)
            self.taken_iwd_checkbox_value.set(True)
            self.card_colors_checkbox_value.set(True)
            overlay_logger.info(f"UpdateSettingsData Error: {error}")
        self.ControlTrace(True) 
        
        self.draft.LogEnable(self.configuration.draft_log_enabled)
    
    def InitializeUI(self):
        self.UpdateSourceOptions(False)
        self.UpdateColumnOptions()
        
        self.EnableDeckStates(self.deck_stats_checkbox_value.get())
        self.EnableMissingCards(self.missing_cards_checkbox_value.get())
        self.UpdateCurrentDraft(self.draft.draft_sets, self.draft.draft_type)
        self.UpdatePackPick(self.draft.current_pack, self.draft.current_pick)

        fields = {"Column1"    : constants.DATA_FIELD_NAME,
                  "Column2"    : self.main_options_dict[self.column_2_selection.get()],
                  "Column3"    : self.main_options_dict[self.column_3_selection.get()],
                  "Column4"    : self.main_options_dict[self.column_4_selection.get()],
                  "Column5"    : self.extra_options_dict[self.column_5_selection.get()],
                  "Column6"    : self.extra_options_dict[self.column_6_selection.get()],
                  "Column7"    : self.extra_options_dict[self.column_7_selection.get()],}
        self.UpdatePackTable([], [], self.deck_filter_selection.get(), fields)
                             
        self.UpdateMissingTable([],[],[],[],self.deck_filter_selection.get(),fields)   

        self.UpdateDeckStatsCallback()

        self.root.update()

    def UpdateCallback(self, enable_draft_search):
        update = True
        if enable_draft_search:
            update = self.UpdateDraft()
        
        if not update:
            return

        self.UpdateSourceOptions(False)
        self.UpdateColumnOptions()
        
        self.EnableDeckStates(self.deck_stats_checkbox_value.get())
        self.EnableMissingCards(self.missing_cards_checkbox_value.get())
              
        taken_cards = self.draft.TakenCards()
        
        filtered = self.DeckFilterColors(taken_cards, self.deck_filter_selection.get())
        fields = {"Column1"    : constants.DATA_FIELD_NAME,
                  "Column2"    : self.main_options_dict[self.column_2_selection.get()],
                  "Column3"    : self.main_options_dict[self.column_3_selection.get()],
                  "Column4"    : self.main_options_dict[self.column_4_selection.get()],
                  "Column5"    : self.extra_options_dict[self.column_5_selection.get()],
                  "Column6"    : self.extra_options_dict[self.column_6_selection.get()],
                  "Column7"    : self.extra_options_dict[self.column_7_selection.get()],}

        self.UpdateCurrentDraft(self.draft.draft_sets, self.draft.draft_type)
        self.UpdatePackPick(self.draft.current_pack, self.draft.current_pick)
        pack_index = (self.draft.current_pick - 1) % 8

        pack_cards = self.draft.PackCards(pack_index)
        self.UpdatePackTable(pack_cards, 
                             taken_cards,
                             filtered,
                             fields)
                             
        self.UpdateMissingTable(pack_cards,
                                self.draft.InitialPackCards(pack_index),
                                self.draft.PickedCards(pack_index),
                                taken_cards,
                                filtered,
                                fields)   

        self.UpdateDeckStatsCallback()
        self.UpdateTakenTable()

    def UpdateDeckStatsCallback(self, *args):
        self.root.update_idletasks() 
        self.UpdateDeckStatsTable(self.draft.TakenCards(), self.stat_options_selection.get(), self.pack_table.winfo_width())

    def UpdateUI(self):
        try:
            self.current_timestamp = os.stat(self.arena_file).st_mtime
            
            if self.current_timestamp != self.previous_timestamp:
                self.previous_timestamp = self.current_timestamp
                
                while(True):

                    self.UpdateCallback(True)
                    if self.draft.step_through:
                        input("Continue?")
                    else:
                        break
        except Exception as error:
            overlay_logger.info(f"UpdateUI Error: {error}")
            self.DraftReset(True)
            
        self.root.after(1000, self.UpdateUI)
        
    def WindowLift(self):
        if self.root.state()=="iconic":
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
        else:
            self.root.attributes("-topmost", False)
            self.root.iconify()
            
    def UpdateSetStartDate(self, start, selection, set_list, *args):
        try:
            set_data = set_list[selection.get()]
            
            if constants.SET_START_DATE in set_data:
                start.delete(0,END)
                start.insert(END, set_data[constants.SET_START_DATE])
                
            self.root.update()
        except Exception as error:
            overlay_logger.info(f"UpdateSetStartDate Error: {error}")
            
    def SetViewPopup(self):
        popup = Toplevel()
        popup.wm_title("Set Data")
        popup.resizable(width = False, height = True)
        popup.attributes("-topmost", True)

        x, y = SafeCoordinates(self.root, 1000, 170, 250, 20)
        popup.wm_geometry("+%d+%d" % (x, y))
        
        Grid.rowconfigure(popup, 1, weight = 1)
        try:
            sets = self.extractor.SetList()
        
            headers = {"SET"        : {"width" : .40, "anchor" : W},
                       "DRAFT"      : {"width" : .20, "anchor" : CENTER},
                       "START DATE" : {"width" : .20, "anchor" : CENTER},
                       "END DATE"   : {"width" : .20, "anchor" : CENTER}}

            style = Style() 
            style.configure("Set.Treeview", rowheight=25)  
            
            list_box_frame = Frame(popup)
            list_box_scrollbar = Scrollbar(list_box_frame, orient=VERTICAL)
            list_box_scrollbar.pack(side=RIGHT, fill=Y)
            
            list_box = CreateHeader(list_box_frame, 0, 10, headers, self.table_widths_dict[constants.TABLE_SETS], True, True, "Set.Treeview", True)
            
            list_box.config(yscrollcommand=list_box_scrollbar.set)
            list_box_scrollbar.config(command=list_box.yview)
            
            notice_label = Label(popup, text="17Lands has an embargo period of 12 days for new sets on Magic Arena. Visit https://www.17lands.com for more details.", font=f'{constants.FONT_SANS_SERIF} 9', anchor="c")
            set_label = Label(popup, text="Set:", font=f'{constants.FONT_SANS_SERIF} 10 bold')
            draft_label = Label(popup, text="Draft:", font=f'{constants.FONT_SANS_SERIF} 10 bold')
            start_label = Label(popup, text="Start Date:", font=f'{constants.FONT_SANS_SERIF} 10 bold')
            end_label = Label(popup, text="End Date:", font=f'{constants.FONT_SANS_SERIF} 10 bold')
            draft_choices = constants.LIMITED_TYPE_LIST

            status_text = StringVar()
            status_label = Label(popup, textvariable=status_text, font=f'{constants.FONT_SANS_SERIF} 12 bold', anchor="c")
            
            draft_value = StringVar(self.root)
            draft_entry = OptionMenu(popup, draft_value, draft_choices[0], *draft_choices)
            
            start_entry = Entry(popup)
            start_entry.insert(END, constants.SET_START_DATE_DEFAULT)
            end_entry = Entry(popup)
            end_entry.insert(END, str(date.today()))
            
            set_choices = list(sets.keys())
            
            set_value = StringVar(self.root)
            set_entry = OptionMenu(popup, set_value, set_choices[0], *set_choices)
            set_value.trace("w", lambda *args, start=start_entry, selection=set_value, set_list=sets : self.UpdateSetStartDate(start, selection, set_list, *args))
            
            progress = Progressbar(popup,orient=HORIZONTAL,length=100,mode='determinate')
            
            add_button = Button(popup, command=lambda: self.AddSet(popup,
                                                                   set_value,
                                                                   draft_value,
                                                                   start_entry,
                                                                   end_entry,
                                                                   add_button,
                                                                   progress,
                                                                   list_box,
                                                                   sets,
                                                                   status_text,
                                                                   constants.DATA_SET_VERSION_3), text="ADD SET")
            
                
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
            status_label.grid(row=5, column=0, columnspan=8, sticky = 'nsew')

            list_box.pack(expand = True, fill = "both")
    
            self.DataViewUpdate(list_box, sets)
        except Exception as error:
            overlay_logger.info(f"SetViewPopup Error: {error}")
        
    def CardComparePopup(self):
        popup = Toplevel()
        popup.wm_title("Card Compare")
        popup.resizable(width = False, height = True)
        popup.attributes("-topmost", True)
        x, y = SafeCoordinates(self.root, 400, 170, 250, 0)
        popup.wm_geometry("+%d+%d" % (x, y))
        
        try:
            Grid.rowconfigure(popup, 2, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)

            taken_cards = self.draft.TakenCards()
            
            filtered = self.DeckFilterColors(taken_cards, self.deck_filter_selection.get())
            fields = {"Column1"    : constants.DATA_FIELD_NAME,
                      "Column2"    : self.main_options_dict[self.column_2_selection.get()],
                      "Column3"    : self.main_options_dict[self.column_3_selection.get()],
                      "Column4"    : self.main_options_dict[self.column_4_selection.get()],
                      "Column5"    : self.extra_options_dict[self.column_5_selection.get()],
                      "Column6"    : self.extra_options_dict[self.column_6_selection.get()],
                      "Column7"    : self.extra_options_dict[self.column_7_selection.get()],}
            
            matching_cards = []
            
            card_frame = Frame(popup)

            set_card_names = [v[constants.DATA_FIELD_NAME] for k,v in self.draft.set_data["card_ratings"].items()]
            card_entry = AutocompleteEntry(
                         card_frame, 
                         completevalues=set_card_names
                         )
            
            headers = {"Column1"  : {"width" : .46, "anchor" : W},
                       "Column2"  : {"width" : .18, "anchor" : CENTER},
                       "Column3"  : {"width" : .18, "anchor" : CENTER},
                       "Column4"  : {"width" : .18, "anchor" : CENTER},
                       "Column5"  : {"width" : .18, "anchor" : CENTER},
                       "Column6"  : {"width" : .18, "anchor" : CENTER},
                       "Column7"  : {"width" : .18, "anchor" : CENTER}}

            compare_table_frame = Frame(popup)
            compare_scrollbar = Scrollbar(compare_table_frame, orient=VERTICAL)
            compare_scrollbar.pack(side=RIGHT, fill=Y)
            compare_table = CreateHeader(compare_table_frame, 0, 8, headers, self.table_widths_dict[constants.TABLE_COMPARE], True, True, constants.TABLE_STYLE, False)
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
                                                                              filtered,
                                                                              fields))

            self.UpdateCompareTable(compare_table,
                                    matching_cards,
                                    card_entry,
                                    self.draft.set_data["card_ratings"],
                                    filtered,
                                    fields)
            
        except Exception as error:
            overlay_logger.info(f"CardComparePopup Error: {error}")

    def TakenCardsExit(self, popup):
        self.taken_table = None
        
        popup.destroy()  

    def TakenCardsPopup(self):
        popup = Toplevel()
        popup.wm_title("Taken Cards")
        popup.attributes("-topmost", True)
        popup.resizable(width = False, height = True)
        x, y = SafeCoordinates(self.root, 400, 170, 250, 0)
        popup.wm_geometry("+%d+%d" % (x, y))
        
        popup.protocol("WM_DELETE_WINDOW", lambda window=popup: self.TakenCardsExit(window))
        try:
            Grid.rowconfigure(popup, 3, weight = 1)
            Grid.columnconfigure(popup, 6, weight = 1)

            taken_cards = self.draft.TakenCards()
            copy_button = Button(popup, command=lambda:CopyTaken(taken_cards,
                                                                 self.draft.set_data),
                                                                 text="Copy to Clipboard")
            
            headers = {"Column1" : {"width" : .40, "anchor" : W},
                       "Column2" : {"width" : .20, "anchor" : CENTER},
                       "Column3" : {"width" : .20, "anchor" : CENTER},
                       "Column4" : {"width" : .20, "anchor" : CENTER},
                       "Column5" : {"width" : .20, "anchor" : CENTER},
                       "Column6" : {"width" : .20, "anchor" : CENTER},
                       "Column7" : {"width" : .20, "anchor" : CENTER},
                       "Column8" : {"width" : .20, "anchor" : CENTER},
                       "Column9" : {"width" : .20, "anchor" : CENTER},
                       "Column10": {"width" : .20, "anchor" : CENTER},
            }

            style = Style() 
            style.configure("Taken.Treeview", rowheight=25)  

            taken_table_frame = Frame(popup)
            taken_scrollbar = Scrollbar(taken_table_frame, orient=VERTICAL)
            taken_scrollbar.pack(side=RIGHT, fill=Y)
            self.taken_table = CreateHeader(taken_table_frame, 0, 8, headers, self.table_widths_dict[constants.TABLE_TAKEN], True, True, "Taken.Treeview", False)
            self.taken_table.config(yscrollcommand=taken_scrollbar.set)
            taken_scrollbar.config(command=self.taken_table.yview)
            
            option_frame = Frame(popup)
            taken_filter_label = Label(option_frame, text="Deck Filter:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            self.taken_filter_selection.set(self.deck_filter_selection.get())
            taken_filter_list = self.deck_filter_list
            
            taken_option = OptionMenu(option_frame, self.taken_filter_selection, self.taken_filter_selection.get(), *taken_filter_list, style="my.TMenubutton")
            
            #type_label = Label(option_frame, text="Type Filter:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            #self.taken_type_selection.set(next(iter(constants.CARD_TYPE_DICT)))
            #taken_type_list = constants.CARD_TYPE_DICT.keys()
            #
            #type_option = OptionMenu(option_frame, self.taken_type_selection, self.taken_type_selection.get(), *taken_type_list, style="my.TMenubutton")

            checkbox_frame = Frame(popup)
            taken_alsa_checkbox = Checkbutton(checkbox_frame,
                                              text = "ALSA",
                                              variable=self.taken_alsa_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)  
            taken_ata_checkbox = Checkbutton(checkbox_frame,
                                              text = "ATA",
                                              variable=self.taken_ata_checkbox_value,
                                              onvalue=1,
                                              offvalue=0) 
            taken_gpwr_checkbox = Checkbutton(checkbox_frame,
                                              text = "GPWR",
                                              variable=self.taken_gpwr_checkbox_value,
                                              onvalue=1,
                                              offvalue=0) 
            taken_ohwr_checkbox = Checkbutton(checkbox_frame,
                                              text = "OHWR",
                                              variable=self.taken_ohwr_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)  
            taken_gndwr_checkbox = Checkbutton(checkbox_frame,
                                              text = "GNDWR",
                                              variable=self.taken_gndwr_checkbox_value,
                                              onvalue=1,
                                              offvalue=0) 
            taken_iwd_checkbox = Checkbutton(checkbox_frame,
                                              text = "IWD",
                                              variable=self.taken_iwd_checkbox_value,
                                              onvalue=1,
                                              offvalue=0) 

            option_frame.grid(row=0, column=0, columnspan=7, sticky="nsew")
            checkbox_frame.grid(row=1, column=0, columnspan = 7, sticky="nsew")
            copy_button.grid(row=2, column=0, columnspan = 7, sticky="nsew")
            taken_table_frame.grid(row=3, column=0, columnspan = 7, sticky = "nsew")
            self.taken_table.pack(side=LEFT, expand = True, fill = "both")
            taken_alsa_checkbox.pack(side=LEFT, expand = True, fill = "both")
            taken_ata_checkbox.pack(side=LEFT, expand = True, fill = "both")
            taken_gpwr_checkbox.pack(side=LEFT, expand = True, fill = "both")
            taken_ohwr_checkbox.pack(side=LEFT, expand = True, fill = "both")
            taken_gndwr_checkbox.pack(side=LEFT, expand = True, fill = "both")
            taken_iwd_checkbox.pack(side=LEFT, expand = True, fill = "both")
            
            taken_filter_label.pack(side=LEFT, expand = True, fill = None)
            taken_option.pack(side=LEFT, expand = True, fill = "both")
            #type_label.pack(side=LEFT, expand = True, fill = None)
            #type_option.pack(side=LEFT, expand = True, fill = "both")
            
            self.UpdateTakenTable()
            popup.update()
        except Exception as error:
            overlay_logger.info(f"TakenCardsPopup Error: {error}")
            
    def SuggestDeckPopup(self):
        popup = Toplevel()
        popup.wm_title("Suggested Decks")
        popup.attributes("-topmost", True)
        popup.resizable(width = False, height = True)
        
        x, y = SafeCoordinates(self.root, 400, 170, 250, 0)
        popup.wm_geometry("+%d+%d" % (x, y))
        
        try:
            Grid.rowconfigure(popup, 3, weight = 1)
            
            suggested_decks = CL.SuggestDeck(self.draft.TakenCards(), self.set_metrics, self.configuration)
            
            choices = ["None"]
            deck_color_options = {}
            
            if len(suggested_decks):
                choices = []
                for color in suggested_decks:
                    rating_label = "%s %s (Rating:%d)" % (color, suggested_decks[color]["type"], suggested_decks[color]["rating"])
                    deck_color_options[rating_label] = color
                    choices.append(rating_label)
                
            deck_colors_label = Label(popup, text="Deck Colors:", anchor = 'e', font=f'{constants.FONT_SANS_SERIF} 9 bold')
            
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
                                                                     deck_color_options),
                                                                     text="Copy to Clipboard")
            
            headers = {"CARD"  : {"width" : .35, "anchor" : W},
                       "COUNT" : {"width" : .14, "anchor" : CENTER},
                       "COLOR" : {"width" : .12, "anchor" : CENTER},
                       "COST"  : {"width" : .10, "anchor" : CENTER},
                       "TYPE"  : {"width" : .29, "anchor" : CENTER}}

            style = Style() 
            style.configure("Suggest.Treeview", rowheight=25) 

            suggest_table_frame = Frame(popup)
            suggest_scrollbar = Scrollbar(suggest_table_frame, orient=VERTICAL)
            suggest_scrollbar.pack(side=RIGHT, fill=Y)
            suggest_table = CreateHeader(suggest_table_frame, 0, 8, headers, self.table_widths_dict[constants.TABLE_SUGGEST], True, True, "Suggest.Treeview", False)
            suggest_table.config(yscrollcommand=suggest_scrollbar.set)
            suggest_scrollbar.config(command=suggest_table.yview)
            
            deck_colors_label.grid(row=0,column=0,columnspan=1,sticky="nsew")
            deck_colors_entry.grid(row=0,column=1,columnspan=1,sticky="nsew")
            deck_colors_button.grid(row=1,column=0,columnspan=2,sticky="nsew")
            copy_button.grid(row=2,column=0,columnspan=2,sticky="nsew")
            suggest_table_frame.grid(row=3, column=0, columnspan = 2, sticky = 'nsew')
            
            suggest_table.pack(expand = True, fill = 'both')
            
            self.UpdateSuggestDeckTable(suggest_table, deck_colors_value, suggested_decks, deck_color_options)
        except Exception as error:
            overlay_logger.info(f"SuggestDeckPopup Error: {error}")      

    def SettingsExit(self, popup):
        self.column_2_options = None
        self.column_3_options = None
        self.column_4_options = None
        self.column_5_options = None
        self.column_6_options = None
        self.column_7_options = None
        popup.destroy()
        
    def SettingsPopup(self):
        popup = Toplevel()
        popup.wm_title("Settings")
        popup.protocol("WM_DELETE_WINDOW", lambda window=popup: self.SettingsExit(window))
        popup.attributes("-topmost", True)
        x, y = SafeCoordinates(self.root, 400, 170, 250, 0)
        popup.wm_geometry("+%d+%d" % (x, y))
        
        try:
            Grid.rowconfigure(popup, 1, weight = 1)
            Grid.columnconfigure(popup, 0, weight = 1)
            
            self.ControlTrace(False)
            
            column_2_label = Label(popup, text="Column 2:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            column_3_label = Label(popup, text="Column 3:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            column_4_label = Label(popup, text="Column 4:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            column_5_label = Label(popup, text="Column 5:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            column_6_label = Label(popup, text="Column 6:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            column_7_label = Label(popup, text="Column 7:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            filter_format_label = Label(popup, text="Deck Filter Format:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            result_format_label = Label(popup, text="Win Rate Format:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            deck_stats_label = Label(popup, text="Enable Draft Stats:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            deck_stats_checkbox = Checkbutton(popup,
                                              variable=self.deck_stats_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)
            missing_cards_label = Label(popup, text="Enable Missing Cards:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            missing_cards_checkbox = Checkbutton(popup,
                                                 variable=self.missing_cards_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0)
                                                 
            auto_highest_label = Label(popup, text="Enable Highest Rated:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            auto_highest_checkbox = Checkbutton(popup,
                                                 variable=self.auto_highest_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0)
                                                 
            #curve_bonus_label = Label(popup, text="Enable Curve Bonus:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            #curve_bonus_checkbox = Checkbutton(popup,
            #                                   variable=self.curve_bonus_checkbox_value,
            #                                   onvalue=1,
            #                                   offvalue=0)
            #color_bonus_label = Label(popup, text="Enable Color Bonus:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            #color_bonus_checkbox = Checkbutton(popup,
            #                                     variable=self.color_bonus_checkbox_value,
            #                                     onvalue=1,
            #                                     offvalue=0)    
            
            bayesian_average_label = Label(popup, text="Enable Bayesian Average:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            bayesian_average_checkbox = Checkbutton(popup,
                                                 variable=self.bayesian_average_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0) 

            draft_log_label = Label(popup, text="Enable Draft Log:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            draft_log_checkbox = Checkbutton(popup,
                                             variable=self.draft_log_checkbox_value,
                                             onvalue=1,
                                             offvalue=0)  

            card_colors_label = Label(popup, text="Enable Card Colors:", font=f'{constants.FONT_SANS_SERIF} 9 bold', anchor="w")
            card_colors_checkbox = Checkbutton(popup,
                                               variable=self.card_colors_checkbox_value,
                                               onvalue=1,
                                               offvalue=0) 
                                                 
            optionsStyle = Style()
            optionsStyle.configure('my.TMenubutton', font=(constants.FONT_SANS_SERIF, 9))
            
            self.column_2_options = OptionMenu(popup, self.column_2_selection, self.column_2_selection.get(), *self.column_2_list, style="my.TMenubutton")
            #self.column_2_options.config(width=15)
            
            self.column_3_options = OptionMenu(popup, self.column_3_selection, self.column_3_selection.get(), *self.column_3_list, style="my.TMenubutton")
            #self.column_3_options.config(width=15)
            
            self.column_4_options = OptionMenu(popup, self.column_4_selection, self.column_4_selection.get(), *self.column_4_list, style="my.TMenubutton")
            #self.column_4_options.config(width=15)

            self.column_5_options = OptionMenu(popup, self.column_5_selection, self.column_5_selection.get(), *self.column_5_list, style="my.TMenubutton")
            #self.column_5_options.config(width=15)

            self.column_6_options = OptionMenu(popup, self.column_6_selection, self.column_6_selection.get(), *self.column_6_list, style="my.TMenubutton")
            #self.column_6_options.config(width=15)

            self.column_7_options = OptionMenu(popup, self.column_7_selection, self.column_7_selection.get(), *self.column_7_list, style="my.TMenubutton")
            #self.column_7_options.config(width=15)
            
            filter_format_options = OptionMenu(popup, self.filter_format_selection, self.filter_format_selection.get(), *self.filter_format_list, style="my.TMenubutton")
            #filter_format_options.config(width=15)
            
            result_format_options = OptionMenu(popup, self.result_format_selection, self.result_format_selection.get(), *self.result_format_list, style="my.TMenubutton")
            #result_format_options.config(width=15)
            
            default_button = Button(popup, command=self.DefaultSettingsCallback, text="Default Settings")
            
            column_2_label.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_3_label.grid(row=1, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_4_label.grid(row=2, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_5_label.grid(row=3, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_6_label.grid(row=4, column=0, columnspan=1, sticky="nsew", padx=(10,))
            column_7_label.grid(row=5, column=0, columnspan=1, sticky="nsew", padx=(10,))
            filter_format_label.grid(row=6, column=0, columnspan=1, sticky="nsew", padx=(10,)) 
            result_format_label.grid(row=7, column=0, columnspan=1, sticky="nsew", padx=(10,))
            self.column_2_options.grid(row=0, column=1, columnspan=1, sticky="nsew")
            self.column_3_options.grid(row=1, column=1, columnspan=1, sticky="nsew")
            self.column_4_options.grid(row=2, column=1, columnspan=1, sticky="nsew")
            self.column_5_options.grid(row=3, column=1, columnspan=1, sticky="nsew")
            self.column_6_options.grid(row=4, column=1, columnspan=1, sticky="nsew")
            self.column_7_options.grid(row=5, column=1, columnspan=1, sticky="nsew")
            filter_format_options.grid(row=6, column=1, columnspan=1, sticky="nsew")
            result_format_options.grid(row=7, column=1, columnspan=1, sticky="nsew")
            card_colors_label.grid(row=8, column=0, columnspan=1, sticky="nsew", padx=(10,)) 
            card_colors_checkbox.grid(row=8, column=1, columnspan=1, sticky="nsew", padx=(5,))
            deck_stats_label.grid(row=9, column=0, columnspan=1, sticky="nsew", padx=(10,))
            deck_stats_checkbox.grid(row=9, column=1, columnspan=1, sticky="nsew", padx=(5,))
            missing_cards_label.grid(row=10, column=0, columnspan=1, sticky="nsew", padx=(10,))
            missing_cards_checkbox.grid(row=10, column=1, columnspan=1, sticky="nsew", padx=(5,)) 
            auto_highest_label.grid(row=11, column=0, columnspan=1, sticky="nsew", padx=(10,))
            auto_highest_checkbox.grid(row=11, column=1, columnspan=1, sticky="nsew", padx=(5,))
            #curve_bonus_label.grid(row=12, column=0, columnspan=1, sticky="nsew", padx=(10,))
            #curve_bonus_checkbox.grid(row=12, column=1, columnspan=1, sticky="nsew", padx=(5,))
            #color_bonus_label.grid(row=14, column=0, columnspan=1, sticky="nsew", padx=(10,))
            #color_bonus_checkbox.grid(row=14, column=1, columnspan=1, sticky="nsew", padx=(5,))
            bayesian_average_label.grid(row=15, column=0, columnspan=1, sticky="nsew", padx=(10,))
            bayesian_average_checkbox.grid(row=15, column=1, columnspan=1, sticky="nsew", padx=(5,))
            draft_log_label.grid(row=16, column=0, columnspan=1, sticky="nsew", padx=(10,))
            draft_log_checkbox.grid(row=16, column=1, columnspan=1, sticky="nsew", padx=(5,))
            default_button.grid(row=17, column=0, columnspan=2, sticky="nsew")
            
            self.ControlTrace(True)

        except Exception as error:
            overlay_logger.info(f"SettingsPopup Error: {error}")
            
        
    def AddSet(self, popup, set, draft, start, end, button, progress, list_box, sets, status, version):
        result = True
        result_string = ""
        return_size = 0
        while(True):
            try:
                message_box = MessageBox.askyesno(title="Download", message=f"17Lands updates their card data once a day at 01:30 UTC. Are you sure that you want to download {set.get()} {draft.get()} data?")
                if not message_box:
                    break
                    
                status.set("Starting Download Process")
                self.extractor.ClearData()
                button['state'] = 'disabled'
                progress['value'] = 0
                popup.update()
                self.extractor.Sets(sets[set.get()])
                self.extractor.DraftType(draft.get())
                if self.extractor.StartDate(start.get()) == False:
                    result = False
                    result_string = "Invalid Start Date (YYYY-MM-DD)"
                    break
                if self.extractor.EndDate(end.get()) == False:
                    result = False
                    result_string = "Invalid End Date (YYYY-MM-DD)"
                    break
                self.extractor.Version(version)
                status.set("Downloading Color Ratings")
                self.extractor.SessionColorRatings()
                
                result, result_string, temp_size = self.extractor.DownloadCardData(popup, progress, status, self.configuration.database_size)
                
                if result == False:
                    break  
                    
                if self.extractor.ExportData() == False:
                    result = False
                    result_string = "File Write Failure"
                    break
                progress['value']=100
                button['state'] = 'normal'
                return_size = temp_size
                popup.update()
                status.set("Updating Set List")
                self.DataViewUpdate(list_box, sets)
                self.DraftReset(True)
                self.UpdateCallback(True)
                status.set("Download Complete")
            except Exception as error:
                result = False
                result_string = error
                
            break
        
        if result == False:
            status.set("Download Failed")
            popup.update()
            button['state'] = 'normal'
            message_string = "Download Failed: %s" % result_string
            message_box = MessageBox.showwarning(title="Error", message=message_string)
        else:
            self.configuration.database_size = return_size
            CL.WriteConfig(self.configuration)
        popup.update()
        return
        
    def DataViewUpdate(self, list_box, sets):
        #Delete the content of the list box
        for row in list_box.get_children():
                list_box.delete(row)
        self.root.update()
        file_list = FE.RetrieveLocalSetList(sets)
        
        if len(file_list):
            list_box.config(height = len(file_list))
        else:
            list_box.config(height=0)
        
        for count, file in enumerate(file_list):
            row_tag = TableRowTag(False, "", count)
            list_box.insert("",index = count, iid = count, values = file, tag = (row_tag,))
            
    def OnClickTable(self, event, table, card_list, selected_color):
        color_dict = {}
        for item in table.selection():
            card_name = table.item(item, "value")[0]
            for card in card_list:
                card_name = card_name if card_name[0] != '*' else card_name[1:]
                if card_name == card[constants.DATA_FIELD_NAME]:
                    try:
                        for count, color in enumerate(selected_color):
                            color_dict[color] = {x : "NA" for x in constants.DATA_FIELDS_LIST}
                            for k in color_dict[color].keys():
                                if k in card[constants.DATA_FIELD_DECK_COLORS][color]:
                                    if k in constants.WIN_RATE_FIELDS_DICT.keys():
                                        winrate_count = constants.WIN_RATE_FIELDS_DICT[k]
                                        color_dict[color][k] = CL.CalculateWinRate(card[constants.DATA_FIELD_DECK_COLORS][color][k],
                                                                                   card[constants.DATA_FIELD_DECK_COLORS][color][winrate_count],
                                                                                   self.configuration.bayesian_average_enabled)
                                    else:
                                        color_dict[color][k] = card[constants.DATA_FIELD_DECK_COLORS][color][k]

                            if "curve_bonus" in card.keys() and len(card["curve_bonus"]):
                                color_dict[color]["curve_bonus"] = card["curve_bonus"][count]
                                
                            if "color_bonus" in card.keys()  and len(card["color_bonus"]):
                                color_dict[color]["color_bonus"] = card["color_bonus"][count]
                            
                        CreateCardToolTip(table, 
                                          event,
                                          card[constants.DATA_FIELD_NAME],
                                          color_dict,
                                          card[constants.DATA_SECTION_IMAGES],
                                          self.configuration.images_enabled)
                    except Exception as error:
                        overlay_logger.info(f"OnClickTable Error: {error}")
                    break
    def FileOpen(self):
        filename = filedialog.askopenfilename(filetypes=(("Log Files", "*.log"),
                                                         ("All files", "*.*") ))
                                              
        if filename:
            self.arena_file = filename
            self.DraftReset(True)
            self.draft.ArenaFile(filename)
            self.draft.LogSuspend(True)
            self.UpdateCallback(True)
            self.draft.LogSuspend(False)
        
    def ControlTrace(self, enabled):
        try:
            trace_list = [
                (self.column_2_selection, lambda : self.column_2_selection.trace("w", self.UpdateSettingsCallback)),
                (self.column_3_selection, lambda : self.column_3_selection.trace("w", self.UpdateSettingsCallback)),
                (self.column_4_selection, lambda : self.column_4_selection.trace("w", self.UpdateSettingsCallback)),
                (self.column_5_selection, lambda : self.column_5_selection.trace("w", self.UpdateSettingsCallback)),
                (self.column_6_selection, lambda : self.column_6_selection.trace("w", self.UpdateSettingsCallback)),
                (self.column_7_selection, lambda : self.column_7_selection.trace("w", self.UpdateSettingsCallback)),
                (self.deck_stats_checkbox_value, lambda : self.deck_stats_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.missing_cards_checkbox_value, lambda : self.missing_cards_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.auto_highest_checkbox_value, lambda : self.auto_highest_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.curve_bonus_checkbox_value, lambda : self.curve_bonus_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.color_bonus_checkbox_value, lambda : self.color_bonus_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.bayesian_average_checkbox_value, lambda : self.bayesian_average_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.data_source_selection, lambda : self.data_source_selection.trace("w", self.UpdateSourceCallback)),
                (self.stat_options_selection, lambda : self.stat_options_selection.trace("w", self.UpdateDeckStatsCallback)),
                (self.draft_log_checkbox_value, lambda : self.draft_log_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.filter_format_selection, lambda : self.filter_format_selection.trace("w", self.UpdateSourceCallback)),
                (self.result_format_selection, lambda : self.result_format_selection.trace("w", self.UpdateSourceCallback)),
                (self.deck_filter_selection, lambda : self.deck_filter_selection.trace("w", self.UpdateSourceCallback)),
                (self.taken_alsa_checkbox_value, lambda : self.taken_alsa_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.taken_ata_checkbox_value, lambda : self.taken_ata_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.taken_gpwr_checkbox_value, lambda : self.taken_gpwr_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.taken_ohwr_checkbox_value, lambda : self.taken_ohwr_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.taken_gndwr_checkbox_value, lambda : self.taken_gndwr_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.taken_iwd_checkbox_value, lambda : self.taken_iwd_checkbox_value.trace("w", self.UpdateSettingsCallback)),
                (self.taken_filter_selection, lambda : self.taken_filter_selection.trace("w", self.UpdateSettingsCallback)),
                (self.taken_type_selection, lambda : self.taken_type_selection.trace("w", self.UpdateSettingsCallback)),
                (self.card_colors_checkbox_value, lambda : self.card_colors_checkbox_value.trace("w", self.UpdateSettingsCallback)),
            ]

            if enabled:
                if len(self.trace_ids) == 0:
                    for (x,y) in trace_list:
                        self.trace_ids.append(y())
            elif len(self.trace_ids):
                for count, (x,y) in enumerate(trace_list):
                    x.trace_vdelete("w", self.trace_ids[count]) 
                self.trace_ids = []
        except Exception as error:
            overlay_logger.info(f"ControlTrace Error: {error}")

    def DraftReset(self, full_reset):
        self.draft.ClearDraft(full_reset)
        
    def VersionCheck(self):
        #Version Check
        update_flag = False
        if sys.platform == constants.PLATFORM_ID_WINDOWS:
            try:
                import win32api

                new_version_found, new_version = CheckVersion(self.extractor, self.version)
                if new_version_found:
                    message_string = "Update client %.2f to version %.2f" % (self.version, new_version)
                    message_box = MessageBox.askyesno(title="Update", message=message_string)
                    if message_box == True:
                        self.extractor.SessionRepositoryDownload("setup.exe")
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
                self.missing_table_frame.grid(row = 9, column = 0, columnspan = 2)
            else:
                self.missing_frame.grid_remove()
                self.missing_table_frame.grid_remove()
        except Exception as error:
            self.missing_frame.grid(row = 8, column = 0, columnspan = 2, sticky = 'nsew')
            self.missing_table_frame.grid(row = 9, column = 0, columnspan = 2)

    def TableColumnControl(self, table, column_fields, table_id):
        visible_columns = []
        last_field_index = 0
        try:
            for count, (key, value) in enumerate(column_fields.items()):
                if value != constants.DATA_FIELD_DISABLED:
                    table.heading(key, text = value.upper())
                    visible_columns.append(key)
                    last_field_index = count
        
            visible_length = len(visible_columns)
            if visible_length < len(constants.TABLE_PROPORTIONS) + 1:
                #full_length = self.table_length_dict[table_id]
                full_length = self.table_widths_dict[table_id]
                proportions = constants.TABLE_PROPORTIONS[visible_length - 1]
                for count, column in enumerate(visible_columns):
                    table.column(column, width=int(proportions[count]*full_length))
            table["displaycolumns"] = visible_columns
        except Exception as error:
            overlay_logger.info(f"TableColumnControl Error: {error}")
        return last_field_index

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
            tt_width = 400
            # creates a toplevel window
            self.tw = Toplevel(self.widget)
            # Leaves only the label and removes the app window
            self.tw.wm_overrideredirect(True)
            if sys.platform == constants.PLATFORM_ID_OSX:
               self.tw.wm_overrideredirect(False) 
   
            tt_frame = Frame(self.tw, borderwidth=5,relief="solid")

            Grid.rowconfigure(tt_frame, 2, weight = 1)

            card_label = Label(tt_frame, text=self.card_name, font=(constants.FONT_SANS_SERIF, 15, "bold", ), background = "#3d3d3d", foreground = "#e6ecec", relief="groove",anchor="c",)
            
            if len(self.color_dict) == 2:
                headers = {"Label"    : {"width" : .70, "anchor" : W},
                           "Value1"   : {"width" : .15, "anchor" : CENTER},
                           "Value2"   : {"width" : .15, "anchor" : CENTER}}
                width = 400
                tt_width += 150
            else:
                headers = {"Label"    : {"width"  : .80, "anchor" : W},
                           "Value1"    : {"width" : .20, "anchor" : CENTER}}
                width = 340
                
            style = Style() 
            style.configure("Tooltip.Treeview", rowheight=23)      
            
            stats_main_table = CreateHeader(tt_frame, 0, 8, headers, width, False, True, "Tooltip.Treeview", False)
            main_field_list = []
            
            values = ["Filter:"] + list(self.color_dict.keys())
            main_field_list.append(tuple(values))

            values = ["Average Taken At:"] + [f"{x[constants.DATA_FIELD_ATA]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))
            
            values = ["Average Last Seen At:"] + [f"{x[constants.DATA_FIELD_ALSA]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))
            
            values = ["Improvement When Drawn:"] + [f"{x[constants.DATA_FIELD_IWD]}pp" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))
            
            values = ["Games In Hand Win Rate:"] + [f"{x[constants.DATA_FIELD_GIHWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))
            
            values = ["Opening Hand Win Rate:"] + [f"{x[constants.DATA_FIELD_OHWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Games Played Win Rate:"] + [f"{x[constants.DATA_FIELD_GPWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Games Not Drawn Win Rate:"] + [f"{x[constants.DATA_FIELD_GNDWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            main_field_list.append(tuple(["",""]))
            
            values = ["Number of Games In Hand:"] + [f"{x[constants.DATA_FIELD_GIH]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))
                
            values = ["Number of Games in Opening Hand:"] + [f"{x[constants.DATA_FIELD_NGOH]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))
                
            values = ["Number of Games Played:"] + [f"{x[constants.DATA_FIELD_NGP]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Number of Games Not Drawn:"] + [f"{x[constants.DATA_FIELD_NGND]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            for x in range(4):
                main_field_list.append(tuple(["",""]))

            #if any("curve_bonus" in x for x in self.color_dict.values()):
            #    values = ["Curve Bonus:"] + [f"+{x['curve_bonus']}" for x in self.color_dict.values()]
            #    main_field_list.append(tuple(values))
            #else:
            #    main_field_list.append(tuple(["",""]))
            #
            #if any("color_bonus" in x for x in self.color_dict.values()):  
            #    values = ["Color Bonus:"] + [f"+{x['color_bonus']}" for x in self.color_dict.values()]
            #    main_field_list.append(tuple(values))
            #else:
            #    main_field_list.append(tuple(["",""]))

            #main_field_list.append(tuple(["",""]))

            if len(main_field_list):
                stats_main_table.config(height = len(main_field_list))
            else:
                stats_main_table.config(height=1)

            column_offset = 0
            #Add scryfall image
            if self.images_enabled:
                from PIL import Image, ImageTk
                size = 280, 390
                self.images = []
                for count, picture in enumerate(self.image):
                    try:
                        if picture:
                            raw_data = urllib.request.urlopen(picture).read()
                            im = Image.open(io.BytesIO(raw_data))
                            im.thumbnail(size, Image.ANTIALIAS)
                            image = ImageTk.PhotoImage(im)
                            image_label = Label(tt_frame, image=image)
                            image_label.grid(column=count, row=1, columnspan=1, rowspan=3)
                            self.images.append(image)
                            column_offset += 1
                            tt_width += 300
                    except Exception as error:
                        overlay_logger.info(f"ShowTip Image Error: {error}")
            
            card_label.grid(column=0, row=0, columnspan=column_offset + 2, sticky=NSEW)

            for count, row_values in enumerate(main_field_list):
                row_tag = TableRowTag(False, "", count)
                stats_main_table.insert("",index = count, iid = count, values = row_values, tag = (row_tag,))


            stats_main_table.grid(row = 1, column = column_offset, sticky=NSEW)
            
            x, y = SafeCoordinates(self.widget, tt_width, 500, 25, 20)
            self.tw.wm_geometry("+%d+%d" % (x, y))
                
            tt_frame.pack()
            
            self.tw.attributes("-topmost", True)
        except Exception as error:
            print("Showtip Error: %s" % error)

    def HideTip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()