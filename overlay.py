"""This module contains the functions and classes that are used for building and handling the application UI"""
import tkinter
from tkinter.ttk import Progressbar, Treeview, Style, OptionMenu, Button, Checkbutton, Label
from tkinter import filedialog
from datetime import date
import urllib
import os
import sys
import io
import logging
import logging.handlers
import math
import argparse
from dataclasses import dataclass
from ttkwidgets.autocomplete import AutocompleteEntry
from pynput.keyboard import Listener, KeyCode
from PIL import Image, ImageTk
import file_extractor as FE
import card_logic as CL
import log_scanner as LS
import constants


@dataclass
class TableInfo:
    reverse: bool = True
    column: str = ""


__version__ = 3.06


if not os.path.exists(constants.DEBUG_LOG_FOLDER):
    os.makedirs(constants.DEBUG_LOG_FOLDER)

overlay_logger = logging.getLogger(constants.LOG_TYPE_DEBUG)
overlay_logger.setLevel(logging.INFO)
handlers = {
    logging.handlers.TimedRotatingFileHandler(
        constants.DEBUG_LOG_FILE, when='D', interval=1, backupCount=7, utc=True),
    logging.StreamHandler(sys.stdout),
}
formatter = logging.Formatter(
    '%(asctime)s,%(message)s', datefmt='<%m/%d/%Y %H:%M:%S>')
for handler in handlers:
    handler.setFormatter(formatter)
    overlay_logger.addHandler(handler)


def start_overlay():
    """Retrieve arguments, create overlay object, and run overlay"""
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--file')
    parser.add_argument('-d', '--data')
    parser.add_argument('--step', action='store_true')

    args = parser.parse_args()

    overlay = Overlay(__version__, args)

    overlay.main_loop()


def restart_overlay(root):
    """Close/destroy the current overlay object and create a new instance"""
    root.close_overlay()
    start_overlay()


def check_version(platform, version):
    """Compare the application version and the latest version in the repository"""
    return_value = False
    repository_version = platform.retrieve_repository_version()
    if repository_version:
        repository_version = int(repository_version)
        client_version = round(float(version) * 100)
        if repository_version > client_version:
            return_value = True

        repository_version = round(float(repository_version) / 100.0, 2)
    return return_value, repository_version


def fixed_map(style, option):
    ''' Returns the style map for 'option' with any styles starting with
     ("!disabled", "!selected", ...) filtered out
     style.map() returns an empty list for missing options, so this should
     be future-safe'''
    return [elm for elm in style.map("Treeview", query_opt=option)
            if elm[:2] != ("!disabled", "!selected")]


def control_table_column(table, column_fields):
    """Hide disabled table columns"""
    visible_columns = {}
    last_field_index = 0
    for count, (key, value) in enumerate(column_fields.items()):
        if value != constants.DATA_FIELD_DISABLED:
            table.heading(key, text=value.upper())
            # visible_columns.append(key)
            visible_columns[key] = count
            last_field_index = count

    table["displaycolumns"] = list(visible_columns.keys())
    return last_field_index, visible_columns


def copy_suggested(deck_colors, deck, color_options):
    """Copy the deck and sideboard list from the Suggest Deck window"""
    colors = color_options[deck_colors.get()]
    deck_string = ""
    try:
        deck_string = CL.copy_deck(
            deck[colors]["deck_cards"], deck[colors]["sideboard_cards"])
        copy_clipboard(deck_string)
    except Exception as error:
        overlay_logger.info("copy_suggested Error: %s", error)
    return


def copy_taken(taken_cards):
    """Copy the card list from the Taken Cards window"""
    deck_string = ""
    try:
        stacked_cards = CL.stack_cards(taken_cards)
        deck_string = CL.copy_deck(
            stacked_cards, None)
        copy_clipboard(deck_string)

    except Exception as error:
        overlay_logger.info("copy_taken Error: %s", error)
    return


def copy_clipboard(copy):
    """Send the copied data to the clipboard"""
    try:
        # Attempt to copy to clipboard
        clip = tkinter.Tk()
        clip.withdraw()
        clip.clipboard_clear()
        clip.clipboard_append(copy)
        clip.update()
        clip.destroy()
    except Exception as error:
        overlay_logger.info("copy_clipboard Error: %s", error)
    return


def identify_table_row_tag(colors_enabled, colors, index):
    """Return the row color (black/white or card color) depending on the application settings"""
    tag = ""

    if colors_enabled:
        tag = CL.row_color_tag(colors)
    else:
        tag = constants.BW_ROW_COLOR_ODD_TAG if index % 2 else constants.BW_ROW_COLOR_EVEN_TAG

    return tag


def identify_safe_coordinates(root, window_width, window_height, offset_x, offset_y):
    '''Return x,y coordinates that fall within the bounds of the screen'''
    location_x = 0
    location_y = 0

    try:
        pointer_x = root.winfo_pointerx()
        pointer_y = root.winfo_pointery()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        if pointer_x + offset_x + window_width > screen_width:
            location_x = max(pointer_x - offset_x - window_width, 0)
        else:
            location_x = pointer_x + offset_x

        if pointer_y + offset_y + window_height > screen_height:
            location_y = max(pointer_y - offset_y - window_height, 0)
        else:
            location_y = pointer_y + offset_y

    except Exception as error:
        overlay_logger.info("identify_safe_coordinates Error: %s", error)

    return location_x, location_y


class ScaledWindow:
    def __init__(self):
        self.scale_factor = 1
        self.fonts_dict = {}
        self.table_info = {}

    def _scale_value(self, value):
        scaled_value = int(value * self.scale_factor)

        return scaled_value

    def _create_header(self, table_label, frame, height, font, headers, total_width, include_header, fixed_width, table_style, stretch_enabled):
        """Configure the tkinter Treeview widget tables that are used to list draft data"""
        header_labels = tuple(headers.keys())
        show_header = "headings" if include_header else ""
        column_stretch = tkinter.YES if stretch_enabled else tkinter.NO
        list_box = Treeview(frame, columns=header_labels,
                            show=show_header, style=table_style, height=height)

        try:
            for key, value in constants.ROW_TAGS_BW_DICT.items():
                list_box.tag_configure(
                    key, font=(value[0], font, "bold"), background=value[1], foreground=value[2])

            for key, value in constants.ROW_TAGS_COLORS_DICT.items():
                list_box.tag_configure(
                    key, font=(value[0], font, "bold"), background=value[1], foreground=value[2])

            for column in header_labels:
                if fixed_width:
                    column_width = int(
                        math.ceil(headers[column]["width"] * total_width))
                    list_box.column(column,
                                    stretch=column_stretch,
                                    anchor=headers[column]["anchor"],
                                    width=column_width)
                else:
                    list_box.column(column, stretch=column_stretch,
                                    anchor=headers[column]["anchor"])
                list_box.heading(column, text=column, anchor=tkinter.CENTER,
                                 command=lambda _col=column: self._sort_table_column(table_label, list_box, _col, True))
            list_box["show"] = show_header  # use after setting column's
            self.table_info[table_label] = TableInfo()
        except Exception as error:
            overlay_logger.info("create_header Error: %s", error)
        return list_box

    def _sort_table_column(self, table_label, table, column, reverse):
        """Sort the table columns when clicked"""
        row_colors = False

        try:
            # Sort column that contains numeric values
            row_list = [(float(table.set(k, column)), k)
                        for k in table.get_children('')]
        except ValueError:
            # Sort column that contains string values
            row_list = [(table.set(k, column), k)
                        for k in table.get_children('')]

        row_list.sort(key=lambda x: CL.field_process_sort(
            x[0]), reverse=reverse)

        if row_list:
            tags = table.item(row_list[0][1])["tags"][0]
            row_colors = True if tags in constants.ROW_TAGS_COLORS_DICT else False

        for index, value in enumerate(row_list):
            table.move(value[1], "", index)

            # Reset the black/white shades for sorted rows
            if not row_colors:
                row_tag = identify_table_row_tag(False, "", index)
                table.item(value[1], tags=row_tag)

        if table_label in self.table_info:
            self.table_info[table_label].reverse = reverse
            self.table_info[table_label].column = column

        table.heading(column, command=lambda: self._sort_table_column(
            table_label, table, column, not reverse))


class Overlay(ScaledWindow):
    '''Class that handles all of the UI widgets'''

    def __init__(self, version, args):
        super().__init__()
        self.root = tkinter.Tk()
        self.version = version
        self.root.title(f"Magic Draft {version}")
        self.configuration = CL.read_config()
        self.root.resizable(False, False)

        self._set_os_configuration()

        self.configuration.table_width = self._scale_value(
            self.configuration.table_width)

        self.listener = None

        if args.file is None:
            self.arena_file = FE.retrieve_arena_log_location()
        else:
            self.arena_file = args.file
        overlay_logger.info("Player Log Location: %s", self.arena_file)

        if args.data is None:
            self.data_file = FE.retrieve_arena_directory(self.arena_file)
        else:
            self.data_file = args.file
        overlay_logger.info("Card Data Location: %s", self.data_file)

        self.step_through = args.step

        self.extractor = FE.FileExtractor(self.data_file)
        self.draft = LS.ArenaScanner(
            self.arena_file, self.step_through, self.extractor.return_set_list())

        self.trace_ids = []
        self.tier_data = {}

        self.main_options_dict = constants.COLUMNS_OPTIONS_MAIN_DICT.copy()
        self.extra_options_dict = constants.COLUMNS_OPTIONS_EXTRA_DICT.copy()
        self.deck_colors = self.draft.retrieve_color_win_rate(
            self.configuration.filter_format)
        self.data_sources = self.draft.retrieve_data_sources()
        self.tier_sources = self.draft.retrieve_tier_source()
        self.set_metrics = self.draft.retrieve_set_metrics(False)

        tkinter.Grid.columnconfigure(self.root, 0, weight=1)
        tkinter.Grid.columnconfigure(self.root, 1, weight=1)
        # Menu Bar
        self.menubar = tkinter.Menu(self.root)
        self.filemenu = tkinter.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open", command=self._open_draft_log)
        self.datamenu = tkinter.Menu(self.menubar, tearoff=0)
        self.datamenu.add_command(
            label="View Sets", command=self._open_set_view_window)

        self.cardmenu = tkinter.Menu(self.menubar, tearoff=0)
        self.cardmenu.add_command(
            label="Taken Cards", command=self._open_taken_cards_window)
        self.cardmenu.add_command(
            label="Suggest Decks", command=self._open_suggest_deck_window)
        self.cardmenu.add_command(
            label="Compare Cards", command=self._open_card_compare_window)

        self.settingsmenu = tkinter.Menu(self.menubar, tearoff=0)
        self.settingsmenu.add_command(
            label="Settings", command=self._open_settings_window)

        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.menubar.add_cascade(label="Data", menu=self.datamenu)
        self.menubar.add_cascade(label="Cards", menu=self.cardmenu)
        self.menubar.add_cascade(label="Settings", menu=self.settingsmenu)
        self.root.config(menu=self.menubar)

        current_draft_label_frame = tkinter.Frame(self.root)
        self.current_draft_label = Label(
            current_draft_label_frame, text="Current Draft:", style="MainSections.TLabel", anchor="e")
        current_draft_value_frame = tkinter.Frame(self.root)
        self.current_draft_value_label = Label(
            current_draft_value_frame, text="", style="CurrentDraft.TLabel", anchor="w")

        data_source_label_frame = tkinter.Frame(self.root)
        self.data_source_label = Label(
            data_source_label_frame, text="Data Source:", style="MainSections.TLabel", anchor="e")

        deck_colors_label_frame = tkinter.Frame(self.root)
        self.deck_colors_label = Label(
            deck_colors_label_frame, text="Deck Filter:", style="MainSections.TLabel", anchor="e")

        self.data_source_selection = tkinter.StringVar(self.root)
        self.data_source_list = self.data_sources

        self.deck_stats_checkbox_value = tkinter.IntVar(self.root)
        self.missing_cards_checkbox_value = tkinter.IntVar(self.root)
        self.auto_highest_checkbox_value = tkinter.IntVar(self.root)
        self.curve_bonus_checkbox_value = tkinter.IntVar(self.root)
        self.color_bonus_checkbox_value = tkinter.IntVar(self.root)
        self.bayesian_average_checkbox_value = tkinter.IntVar(self.root)
        self.draft_log_checkbox_value = tkinter.IntVar(self.root)
        self.taken_alsa_checkbox_value = tkinter.IntVar(self.root)
        self.taken_ata_checkbox_value = tkinter.IntVar(self.root)
        self.taken_gpwr_checkbox_value = tkinter.IntVar(self.root)
        self.taken_ohwr_checkbox_value = tkinter.IntVar(self.root)
        self.taken_gndwr_checkbox_value = tkinter.IntVar(self.root)
        self.taken_iwd_checkbox_value = tkinter.IntVar(self.root)
        self.taken_gdwr_checkbox_value = tkinter.IntVar(self.root)
        self.card_colors_checkbox_value = tkinter.IntVar(self.root)
        self.color_identity_checkbox_value = tkinter.IntVar(self.root)
        self.taken_type_creature_checkbox_value = tkinter.IntVar(self.root)
        self.taken_type_creature_checkbox_value.set(True)
        self.taken_type_land_checkbox_value = tkinter.IntVar(self.root)
        self.taken_type_land_checkbox_value.set(True)
        self.taken_type_instant_sorcery_checkbox_value = tkinter.IntVar(
            self.root)
        self.taken_type_instant_sorcery_checkbox_value.set(True)
        self.taken_type_other_checkbox_value = tkinter.IntVar(self.root)
        self.taken_type_other_checkbox_value.set(True)

        self.column_2_selection = tkinter.StringVar(self.root)
        self.column_2_list = self.main_options_dict.keys()
        self.column_3_selection = tkinter.StringVar(self.root)
        self.column_3_list = self.main_options_dict.keys()
        self.column_4_selection = tkinter.StringVar(self.root)
        self.column_4_list = self.main_options_dict.keys()
        self.column_5_selection = tkinter.StringVar(self.root)
        self.column_5_list = self.extra_options_dict.keys()
        self.column_6_selection = tkinter.StringVar(self.root)
        self.column_6_list = self.extra_options_dict.keys()
        self.column_7_selection = tkinter.StringVar(self.root)
        self.column_7_list = self.extra_options_dict.keys()
        self.filter_format_selection = tkinter.StringVar(self.root)
        self.filter_format_list = constants.DECK_FILTER_FORMAT_LIST
        self.result_format_selection = tkinter.StringVar(self.root)
        self.result_format_list = constants.RESULT_FORMAT_LIST
        self.deck_filter_selection = tkinter.StringVar(self.root)
        self.deck_filter_list = self.deck_colors.keys()
        self.taken_filter_selection = tkinter.StringVar(self.root)
        self.taken_type_selection = tkinter.StringVar(self.root)
        self.ui_size_selection = tkinter.StringVar(self.root)
        self.ui_size_list = constants.UI_SIZE_DICT.keys()

        data_source_option_frame = tkinter.Frame(self.root)
        self.data_source_options = OptionMenu(data_source_option_frame, self.data_source_selection,
                                              self.data_source_selection.get(), *self.data_source_list, style="All.TMenubutton")
        menu = self.root.nametowidget(self.data_source_options['menu'])
        menu.config(font=self.fonts_dict["All.TMenubutton"])

        self.column_2_options = None
        self.column_3_options = None
        self.column_4_options = None
        self.column_5_options = None
        self.column_6_options = None
        self.column_7_options = None
        self.taken_table = None

        deck_colors_option_frame = tkinter.Frame(self.root)
        self.deck_colors_options = OptionMenu(deck_colors_option_frame, self.deck_filter_selection,
                                              self.deck_filter_selection.get(), *self.deck_filter_list, style="All.TMenubutton")
        menu = self.root.nametowidget(self.deck_colors_options['menu'])
        menu.config(font=self.fonts_dict["All.TMenubutton"])

        self.refresh_button_frame = tkinter.Frame(self.root)
        self.refresh_button = Button(
            self.refresh_button_frame, command=lambda: self._update_overlay_callback(True), text="Refresh")

        self.status_frame = tkinter.Frame(self.root)
        self.pack_pick_label = Label(
            self.status_frame, text="Pack: 0, Pick: 0", style="MainSections.TLabel")

        self.pack_table_frame = tkinter.Frame(self.root, width=10)

        headers = {"Column1": {"width": .46, "anchor": tkinter.W},
                   "Column2": {"width": .18, "anchor": tkinter.CENTER},
                   "Column3": {"width": .18, "anchor": tkinter.CENTER},
                   "Column4": {"width": .18, "anchor": tkinter.CENTER},
                   "Column5": {"width": .18, "anchor": tkinter.CENTER},
                   "Column6": {"width": .18, "anchor": tkinter.CENTER},
                   "Column7": {"width": .18, "anchor": tkinter.CENTER}}

        self.pack_table = self._create_header("pack_table", self.pack_table_frame, 0, self.fonts_dict["All.TableRow"], headers,
                                              self.configuration.table_width, True, True, constants.TABLE_STYLE, False)

        self.missing_frame = tkinter.Frame(self.root)
        self.missing_cards_label = Label(
            self.missing_frame, text="Missing Cards", style="MainSections.TLabel")

        self.missing_table_frame = tkinter.Frame(self.root, width=10)

        self.missing_table = self._create_header("missing_table", self.missing_table_frame, 0, self.fonts_dict["All.TableRow"], headers,
                                                 self.configuration.table_width, True, True, constants.TABLE_STYLE, False)

        self.stat_frame = tkinter.Frame(self.root)

        self.stat_table = self._create_header("stat_table", self.root, 0, self.fonts_dict["All.TableRow"], constants.STATS_HEADER_CONFIG,
                                              self.configuration.table_width, True, True, constants.TABLE_STYLE, False)
        self.stat_label = Label(self.stat_frame, text="Draft Stats:",
                                style="MainSections.TLabel", anchor="e", width=15)

        self.stat_options_selection = tkinter.StringVar(self.root)
        self.stat_options_list = [constants.CARD_TYPE_SELECTION_CREATURES,
                                  constants.CARD_TYPE_SELECTION_NONCREATURES,
                                  constants.CARD_TYPE_SELECTION_ALL]

        self.stat_options = OptionMenu(self.stat_frame, self.stat_options_selection,
                                       self.stat_options_list[0], *self.stat_options_list, style="All.TMenubutton")
        # self.stat_options.config(width=11)
        menu = self.root.nametowidget(self.stat_options['menu'])
        menu.config(font=self.fonts_dict["All.TMenubutton"])

        citation_label = Label(self.root, text="Powered by 17Lands*",
                               anchor="e", borderwidth=2, relief="groove")

        hotkey_label = Label(self.root, text="CTRL+G to Minimize",
                             style="Notes.TLabel", anchor="e")
        footnote_label = Label(self.root, text="*This application is not endorsed by 17Lands",
                               style="Notes.TLabel", anchor="e")

        citation_label.grid(row=0, column=0, columnspan=2)
        row_padding = (self._scale_value(3), self._scale_value(3))
        current_draft_label_frame.grid(
            row=1, column=0, columnspan=1, sticky='nsew', pady=row_padding)
        current_draft_value_frame.grid(
            row=1, column=1, columnspan=1, sticky='nsew')
        data_source_label_frame.grid(
            row=2, column=0, columnspan=1, sticky='nsew', pady=row_padding)
        data_source_option_frame.grid(
            row=2, column=1, columnspan=1, sticky='nsew')
        deck_colors_label_frame.grid(
            row=3, column=0, columnspan=1, sticky='nsew', pady=row_padding)
        deck_colors_option_frame.grid(
            row=3, column=1, columnspan=1, sticky='nsw')
        hotkey_label.grid(row=4, column=0, columnspan=2)
        self.refresh_button_frame.grid(
            row=5, column=0, columnspan=2, sticky='nsew')
        self.status_frame.grid(row=6, column=0, columnspan=2, sticky='nsew')
        self.pack_table_frame.grid(row=7, column=0, columnspan=2)
        footnote_label.grid(row=12, column=0, columnspan=2)
        self._enable_deck_stats_table(self.deck_stats_checkbox_value.get())
        self._enable_missing_cards_table(
            self.missing_cards_checkbox_value.get())

        self.refresh_button.pack(expand=True, fill="both")

        self.pack_pick_label.pack(expand=False, fill=None)
        self.pack_table.pack(expand=True, fill='both')
        self.missing_cards_label.pack(expand=False, fill=None)
        self.missing_table.pack(expand=True, fill='both')
        self.stat_label.pack(side=tkinter.LEFT, expand=True, fill=None)
        self.stat_options.pack(side=tkinter.RIGHT, expand=True, fill=None)
        self.current_draft_label.pack(expand=True, fill=None, anchor="e")
        self.current_draft_value_label.pack(expand=True, fill=None, anchor="w")
        self.data_source_label.pack(expand=True, fill=None, anchor="e")
        self.data_source_options.pack(expand=True, fill=None, anchor="w")
        self.deck_colors_label.pack(expand=True, fill=None, anchor="e")
        self.deck_colors_options.pack(expand=True, fill=None, anchor="w")
        self.current_timestamp = 0
        self.previous_timestamp = 0
        self.log_check_id = None

        self._update_settings_data()

        self.root.attributes("-topmost", True)
        self._initialize_overlay_widgets()
        self._update_overlay_build()

        if self.configuration.hotkey_enabled:
            self._start_hotkey_listener()

    def close_overlay(self):
        if self.log_check_id is not None:
            self.root.after_cancel(self.log_check_id)
            self.log_check_id = None
        self.root.destroy()

    def _set_os_configuration(self):
        '''Configure the overlay based on the operating system'''
        platform = sys.platform

        overlay_logger.info("Platform: %s", platform)

        if platform == constants.PLATFORM_ID_OSX:
            self.configuration.hotkey_enabled = False
        else:
            self.root.tk.call("source", "dark_mode.tcl")
        self._adjust_overlay_scale()
        self._configure_fonts(platform)

    def _adjust_overlay_scale(self):
        '''Adjust widget and font scale based on the scale_factor value in config.json'''
        self.scale_factor = 1
        try:
            self.scale_factor = constants.UI_SIZE_DICT[self.configuration.ui_size]

            if self.configuration.override_scale_factor > 0.0:
                self.scale_factor = self.configuration.override_scale_factor

            overlay_logger.info("Scale Factor %.1f",
                                self.scale_factor)
        except Exception as error:
            overlay_logger.info("_adjust_overlay_scale Error: %s", error)

        return

    def _configure_fonts(self, platform):
        '''Set size and family for the overlay fonts
            - Negative font values are in pixels and positive font values are
              in points (1/72 inch = 1 point)
        '''
        try:
            default_font = tkinter.font.nametofont("TkDefaultFont")
            default_font.configure(size=self._scale_value(-12),
                                   family=constants.FONT_SANS_SERIF)

            text_font = tkinter.font.nametofont("TkTextFont")
            text_font.configure(size=self._scale_value(-12),
                                family=constants.FONT_SANS_SERIF)

            fixed_font = tkinter.font.nametofont("TkFixedFont")
            fixed_font.configure(size=self._scale_value(-12),
                                 family=constants.FONT_SANS_SERIF)

            menu_font = tkinter.font.nametofont("TkMenuFont")
            menu_font.configure(size=self._scale_value(-12),
                                family=constants.FONT_SANS_SERIF)

            style = Style()

            style.configure("MainSections.TLabel", font=(constants.FONT_SANS_SERIF,
                                                         self._scale_value(-12),
                                                         "bold"))

            style.configure("CurrentDraft.TLabel", font=(constants.FONT_SANS_SERIF,
                                                         self._scale_value(-12)))

            style.configure("Notes.TLabel", font=(constants.FONT_SANS_SERIF,
                                                  self._scale_value(-11)))

            # style.configure("MainValues.TLabel", font=(constants.FONT_SANS_SERIF,
            #                                            self._scale_value(9)))

            style.configure("TooltipHeader.TLabel", font=(constants.FONT_SANS_SERIF,
                                                          self._scale_value(-17),
                                                          "bold"))

            style.configure("Status.TLabel", font=(constants.FONT_SANS_SERIF,
                                                   self._scale_value(-15),
                                                   "bold"))

            style.configure("SetOptions.TLabel", font=(constants.FONT_SANS_SERIF,
                                                       self._scale_value(-13),
                                                       "bold"))

            style.configure("All.TMenubutton", font=(constants.FONT_SANS_SERIF,
                                                     self._scale_value(-12)))
            self.fonts_dict["All.TMenubutton"] = (constants.FONT_SANS_SERIF,
                                                  self._scale_value(-12))

            self.fonts_dict["All.TableRow"] = self._scale_value(-11)
            self.fonts_dict["Sets.TableRow"] = self._scale_value(-13)

            style.configure("Taken.TCheckbutton", font=(constants.FONT_SANS_SERIF,
                                                        self._scale_value(-11)))

            style.map("Treeview",
                      foreground=fixed_map(style, "foreground"),
                      background=fixed_map(style, "background"))

            style.configure("Treeview", rowheight=self._scale_value(25))

            style.configure("Taken.Treeview", rowheight=self._scale_value(25))

            style.configure("Suggest.Treeview",
                            rowheight=self._scale_value(25))

            style.configure("Set.Treeview", rowheight=self._scale_value(25))

            style.configure("Treeview.Heading", font=(constants.FONT_SANS_SERIF,
                                                      self._scale_value(-9)))

            if platform == constants.PLATFORM_ID_WINDOWS:
                style.configure("TButton", foreground="black")
                style.configure("Treeview.Heading", foreground="black")
                style.configure("TEntry", foreground="black")

        except Exception as error:
            overlay_logger.info("_configure_fonts Error: %s", error)

    def _start_hotkey_listener(self):
        '''Start listener that detects the minimize hotkey'''
        self.listener = Listener(
            on_press=lambda event: self._process_hotkey_press(event)).start()

    def _process_hotkey_press(self, key):
        '''Determine if the minimize hotkey was pressed'''
        if key == KeyCode.from_char(constants.HOTKEY_CTRL_G):
            self.lift_window()

    def main_loop(self):
        '''Run the TKinter overlay'''
        self.root.mainloop()

    def _identify_auto_colors(self, cards, selected_option):
        '''Update the Deck Filter option menu when the Auto option is selected'''
        filtered_colors = [constants.FILTER_OPTION_ALL_DECKS]

        try:
            #selected_option = self.deck_filter_selection.get()
            selected_color = self.deck_colors[selected_option]
            filtered_colors = CL.option_filter(
                cards, selected_color, self.set_metrics, self.configuration)

            if selected_color == constants.FILTER_OPTION_AUTO:
                new_key = f"{constants.FILTER_OPTION_AUTO} ({'/'.join(filtered_colors)})"
                if new_key != selected_option:
                    self.deck_colors.pop(selected_option)
                    new_dict = {new_key: constants.FILTER_OPTION_AUTO}
                    new_dict.update(self.deck_colors)
                    self.deck_colors = new_dict
                    self._update_column_options()

        except Exception as error:
            overlay_logger.info("__identify_auto_colors Error: %s", error)

        return filtered_colors

    def _update_pack_table(self, card_list, filtered_colors, fields):
        '''Update the table that lists the cards within the current pack'''
        try:
            result_class = CL.CardResult(
                self.set_metrics, self.tier_data, self.configuration, self.draft.current_pick)
            result_list = result_class.return_results(
                card_list, filtered_colors, fields)

            # clear the previous rows
            for row in self.pack_table.get_children():
                self.pack_table.delete(row)

            list_length = len(result_list)

            if list_length:
                self.pack_table.config(height=list_length)
            else:
                self.pack_table.config(height=0)

            # Update the filtered column header with the filtered colors
            last_field_index, visible_columns = control_table_column(
                self.pack_table, fields)

            if self.table_info["pack_table"].column in visible_columns:
                column_index = visible_columns[self.table_info["pack_table"].column]
                direction = self.table_info["pack_table"].reverse
                result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                    d["results"][column_index]), reverse=direction)
            else:
                result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                    d["results"][last_field_index]), reverse=True)

            for count, card in enumerate(result_list):
                row_tag = identify_table_row_tag(
                    self.configuration.card_colors_enabled,
                    card[constants.DATA_FIELD_MANA_COST],
                    count)
                field_values = tuple(card["results"])
                self.pack_table.insert(
                    "", index=count, iid=count, values=field_values, tag=(row_tag,))
            self.pack_table.bind("<<TreeviewSelect>>", lambda event: self._process_table_click(
                event, table=self.pack_table, card_list=card_list, selected_color=filtered_colors))
        except Exception as error:
            overlay_logger.info("__update_pack_table Error: %s", error)

    def _update_missing_table(self, current_pack, previous_pack, picked_cards, filtered_colors, fields):
        '''Update the table that lists the cards that are missing from the current pack'''
        try:
            for row in self.missing_table.get_children():
                self.missing_table.delete(row)

            # Update the filtered column header with the filtered colors
            last_field_index, visible_columns = control_table_column(
                self.missing_table, fields)
            if not previous_pack:
                self.missing_table.config(height=0)
            else:
                missing_cards = [
                    x for x in previous_pack if x not in current_pack]

                list_length = len(missing_cards)

                if list_length:
                    self.missing_table.config(height=list_length)
                else:
                    self.missing_table.config(height=0)

                if list_length:
                    result_class = CL.CardResult(
                        self.set_metrics, self.tier_data, self.configuration, self.draft.current_pick)
                    result_list = result_class.return_results(
                        missing_cards, filtered_colors, fields)

                    if self.table_info["missing_table"].column in visible_columns:
                        column_index = visible_columns[self.table_info["missing_table"].column]
                        direction = self.table_info["missing_table"].reverse
                        result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                            d["results"][column_index]), reverse=direction)
                    else:
                        result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                            d["results"][last_field_index]), reverse=True)

                    for count, card in enumerate(result_list):
                        row_tag = identify_table_row_tag(
                            self.configuration.card_colors_enabled,
                            card[constants.DATA_FIELD_MANA_COST],
                            count)
                        for index, field in enumerate(fields.values()):
                            if field == constants.DATA_FIELD_NAME:
                                card["results"][index] = f'*{card["results"][index]}' if card[
                                    "results"][index] in picked_cards else card["results"][index]
                        field_values = tuple(card["results"])
                        self.missing_table.insert(
                            "", index=count, iid=count, values=field_values, tag=(row_tag,))
                    self.missing_table.bind("<<TreeviewSelect>>", lambda event: self._process_table_click(
                        event, table=self.missing_table, card_list=missing_cards, selected_color=filtered_colors))
        except Exception as error:
            overlay_logger.info("__update_missing_table Error: %s", error)

    def _clear_compare_table(self, compare_table, matching_cards):
        '''Clear the rows within the Card Compare table'''
        matching_cards.clear()
        compare_table.delete(*compare_table.get_children())
        compare_table.config(height=0)

    def _update_compare_table(self, compare_table, matching_cards, entry_box, card_list, filtered_colors, fields):
        '''Update the Card Compare table that lists the searched cards'''
        try:
            added_card = entry_box.get()
            if added_card:
                cards = [card_list[x] for x in card_list if card_list[x]
                         [constants.DATA_FIELD_NAME] == added_card and card_list[x] not in matching_cards]
                entry_box.delete(0, tkinter.END)
                if cards:
                    matching_cards.append(cards[0])

            result_class = CL.CardResult(
                self.set_metrics, self.tier_data, self.configuration, self.draft.current_pick)
            result_list = result_class.return_results(
                matching_cards, filtered_colors, fields)

            compare_table.delete(*compare_table.get_children())

            # Update the filtered column header with the filtered colors
            last_field_index, visible_columns = control_table_column(
                compare_table, fields)

            if self.table_info["compare_table"].column in visible_columns:
                column_index = visible_columns[self.table_info["compare_table"].column]
                direction = self.table_info["compare_table"].reverse
                result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                    d["results"][column_index]), reverse=direction)
            else:
                result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                    d["results"][last_field_index]), reverse=True)

            list_length = len(result_list)

            if list_length:
                compare_table.config(height=list_length)
            else:
                compare_table.config(height=0)

            for count, card in enumerate(result_list):
                row_tag = identify_table_row_tag(
                    self.configuration.card_colors_enabled,
                    card[constants.DATA_FIELD_MANA_COST],
                    count)
                field_values = tuple(card["results"])
                compare_table.insert(
                    "", index=count, iid=count, values=field_values, tag=(row_tag,))
            compare_table.bind("<<TreeviewSelect>>", lambda event: self._process_table_click(
                event, table=compare_table, card_list=matching_cards, selected_color=filtered_colors))
        except Exception as error:
            overlay_logger.info("__update_compare_table Error: %s", error)

    def _update_taken_table(self, *args):
        '''Update the table that lists the taken cards'''
        try:
            while True:
                if self.taken_table is None:
                    break

                fields = {"Column1": constants.DATA_FIELD_NAME,
                          "Column2": constants.DATA_FIELD_COUNT,
                          "Column3": constants.DATA_FIELD_COLORS,
                          "Column4": (constants.DATA_FIELD_ALSA if self.taken_alsa_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column5": (constants.DATA_FIELD_ATA if self.taken_ata_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column6": (constants.DATA_FIELD_IWD if self.taken_iwd_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column7": (constants.DATA_FIELD_GPWR if self.taken_gpwr_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column8": (constants.DATA_FIELD_OHWR if self.taken_ohwr_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column9": (constants.DATA_FIELD_GDWR if self.taken_gdwr_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column10": (constants.DATA_FIELD_GNSWR if self.taken_gndwr_checkbox_value.get() else constants.DATA_FIELD_DISABLED),
                          "Column11": constants.DATA_FIELD_GIHWR}

                taken_cards = self.draft.retrieve_taken_cards()

                filtered_colors = self._identify_auto_colors(
                    taken_cards, self.taken_filter_selection.get())

                # Apply the card type filters
                if not (self.taken_type_creature_checkbox_value.get() and
                        self.taken_type_land_checkbox_value.get() and
                        self.taken_type_instant_sorcery_checkbox_value.get() and
                        self.taken_type_other_checkbox_value.get()):
                    card_types = []

                    if self.taken_type_creature_checkbox_value.get():
                        card_types.append(constants.CARD_TYPE_CREATURE)

                    if self.taken_type_land_checkbox_value.get():
                        card_types.append(constants.CARD_TYPE_LAND)

                    if self.taken_type_instant_sorcery_checkbox_value.get():
                        card_types.extend(
                            [constants.CARD_TYPE_INSTANT, constants.CARD_TYPE_SORCERY])

                    if self.taken_type_other_checkbox_value.get():
                        card_types.extend([constants.CARD_TYPE_ARTIFACT,
                                           constants.CARD_TYPE_ENCHANTMENT,
                                           constants.CARD_TYPE_PLANESWALKER])

                    taken_cards = CL.deck_card_search(taken_cards,
                                                      constants.CARD_COLORS,
                                                      card_types,
                                                      True,
                                                      True,
                                                      True)

                stacked_cards = CL.stack_cards(taken_cards)

                for row in self.taken_table.get_children():
                    self.taken_table.delete(row)

                result_class = CL.CardResult(
                    self.set_metrics, self.tier_data, self.configuration, self.draft.current_pick)
                result_list = result_class.return_results(
                    stacked_cards, filtered_colors, fields)

                last_field_index, visible_columns = control_table_column(
                    self.taken_table, fields)

                if self.table_info["taken_table"].column in visible_columns:
                    column_index = visible_columns[self.table_info["taken_table"].column]
                    direction = self.table_info["taken_table"].reverse
                    result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                        d["results"][column_index]), reverse=direction)
                else:
                    result_list = sorted(result_list, key=lambda d: CL.field_process_sort(
                        d["results"][last_field_index]), reverse=True)

                if result_list:
                    self.taken_table.config(height=min(len(result_list), 20))
                else:
                    self.taken_table.config(height=1)

                for count, card in enumerate(result_list):
                    field_values = tuple(card["results"])
                    row_tag = identify_table_row_tag(
                        self.configuration.card_colors_enabled,
                        card[constants.DATA_FIELD_MANA_COST],
                        count)
                    self.taken_table.insert(
                        "", index=count, iid=count, values=field_values, tag=(row_tag,))
                self.taken_table.bind("<<TreeviewSelect>>", lambda event: self._process_table_click(
                    event, table=self.taken_table, card_list=result_list, selected_color=filtered_colors))
                break
        except Exception as error:
            overlay_logger.info("__update_taken_table Error: %s", error)

    def _update_suggest_table(self, suggest_table, selected_color, suggested_decks, color_options):
        '''Update the table that lists the suggested decks'''
        try:
            color = color_options[selected_color.get()]
            suggested_deck = suggested_decks[color]["deck_cards"]
            suggested_deck.sort(
                key=lambda x: x[constants.DATA_FIELD_CMC], reverse=False)
            for row in suggest_table.get_children():
                suggest_table.delete(row)

            list_length = len(suggested_deck)
            if list_length:
                suggest_table.config(height=list_length)
            else:
                suggest_table.config(height=0)

            for count, card in enumerate(suggested_deck):
                row_tag = identify_table_row_tag(
                    self.configuration.card_colors_enabled,
                    card[constants.DATA_FIELD_MANA_COST],
                    count)

                if constants.CARD_TYPE_LAND in card[constants.DATA_FIELD_TYPES]:
                    card_colors = "".join(card[constants.DATA_FIELD_COLORS])
                else:
                    card_colors = "".join(list(CL.card_colors(card[constants.DATA_FIELD_MANA_COST]).keys())
                                          if not self.configuration.color_identity_enabled
                                          else card[constants.DATA_FIELD_COLORS])

                suggest_table.insert("", index=count, values=(card[constants.DATA_FIELD_NAME],
                                                              f"{card[constants.DATA_FIELD_COUNT]}",
                                                              card_colors,
                                                              card[constants.DATA_FIELD_CMC],
                                                              card[constants.DATA_FIELD_TYPES]), tag=(row_tag,))
            suggest_table.bind("<<TreeviewSelect>>", lambda event: self._process_table_click(
                event, table=suggest_table, card_list=suggested_deck, selected_color=[color]))

        except Exception as error:
            overlay_logger.info("_update_suggest_table Error: %s", error)

    def _update_deck_stats_table(self, taken_cards, filter_type, total_width):
        '''Update the table that lists the draft stats'''
        try:
            card_types = constants.CARD_TYPE_DICT[filter_type]

            colors_filtered = {}
            for color, symbol in constants.CARD_COLORS_DICT.items():
                if symbol:
                    card_colors_sorted = CL.deck_card_search(
                        taken_cards, symbol, card_types[0], card_types[1], card_types[2], card_types[3])
                else:
                    card_colors_sorted = CL.deck_card_search(
                        taken_cards, symbol, card_types[0], card_types[1], True, False)
                card_metrics = CL.deck_metrics(card_colors_sorted)
                colors_filtered[color] = {}
                colors_filtered[color]["symbol"] = symbol
                colors_filtered[color]["total"] = card_metrics.total_cards
                colors_filtered[color]["distribution"] = card_metrics.distribution_all

            # Sort list by total
            colors_filtered = dict(sorted(colors_filtered.items(
            ), key=lambda item: item[1]["total"], reverse=True))

            for row in self.stat_table.get_children():
                self.stat_table.delete(row)

            if total_width == 1:
                self.stat_table.config(height=0)
                self._enable_deck_stats_table(False)
                return

            # Adjust the width for each column
            width = total_width - 5
            for column in self.stat_table["columns"]:
                column_width = min(int(math.ceil(
                    constants.STATS_HEADER_CONFIG[column]["width"] * total_width)), width)
                width -= column_width
                self.stat_table.column(column, width=column_width)

            list_length = len(colors_filtered)
            if list_length:
                self.stat_table.config(height=list_length)
            else:
                self.stat_table.config(height=0)
                # return

            for count, (color, values) in enumerate(colors_filtered.items()):
                row_tag = identify_table_row_tag(
                    self.configuration.card_colors_enabled, values["symbol"], count)
                self.stat_table.insert("", index=count, values=(color,
                                                                values["distribution"][1],
                                                                values["distribution"][2],
                                                                values["distribution"][3],
                                                                values["distribution"][4],
                                                                values["distribution"][5],
                                                                values["distribution"][6],
                                                                values["total"]), tag=(row_tag,))
        except Exception as error:
            overlay_logger.info("__update_deck_stats_table Error: %s", error)

    def _update_pack_pick_label(self, pack, pick):
        '''Update the label that lists the pack and pick numbers'''
        try:
            new_label = f"Pack: {pack} / Pick: {pick}"
            self.pack_pick_label.config(text=new_label)

        except Exception as error:
            overlay_logger.info("__update_pack_pick_label Error: %s", error)

    def _update_current_draft_label(self, card_set, draft_type):
        '''Update the label that lists the current draft set and type (e.g., DMU PremierDraft)'''
        try:
            draft_type_string = ''

            for key, value in constants.LIMITED_TYPES_DICT.items():
                if value == draft_type:
                    draft_type_string = key
                    break

            new_label = f" {card_set[0]} {draft_type_string}" if card_set else " None"
            self.current_draft_value_label.config(text=new_label)
        except Exception as error:
            overlay_logger.info(
                "__update_current_draft_label Error: %s", error)

    def _update_data_source_options(self, new_list):
        '''Update the option menu that lists the available data sets for the current draft set (i.e., QuickDraft, PremierDraft, TradDraft, etc.)'''
        self._control_trace(False)
        try:
            if new_list:
                self.data_source_selection.set(next(iter(self.data_sources)))
                menu = self.data_source_options["menu"]
                menu.delete(0, "end")

                self.data_source_list = []

                for key in self.data_sources:
                    menu.add_command(label=key,
                                     command=lambda value=key: self.data_source_selection.set(value))
                    self.data_source_list.append(key)

            elif self.data_source_selection.get() not in self.data_sources:
                self.data_source_selection.set(next(iter(self.data_sources)))

        except Exception as error:
            overlay_logger.info(
                "__update_data_source_options Error: %s", error)

        self._control_trace(True)

    def _update_column_options(self):
        '''Update the option menus whenever the application settings change'''
        self._control_trace(False)
        try:
            if self.filter_format_selection.get() not in self.filter_format_list:
                self.filter_format_selection.set(
                    constants.DECK_FILTER_FORMAT_COLORS)
            if self.result_format_selection.get() not in self.result_format_list:
                self.result_format_selection.set(
                    constants.RESULT_FORMAT_WIN_RATE)
            if self.ui_size_selection.get() not in self.ui_size_list:
                self.ui_size_selection.set(
                    constants.UI_SIZE_DEFAULT)
            if self.column_2_selection.get() not in self.main_options_dict:
                self.column_2_selection.set(constants.COLUMN_2_DEFAULT)
            if self.column_3_selection.get() not in self.main_options_dict:
                self.column_3_selection.set(constants.COLUMN_3_DEFAULT)
            if self.column_4_selection.get() not in self.main_options_dict:
                self.column_4_selection.set(constants.COLUMN_4_DEFAULT)
            if self.column_5_selection.get() not in self.extra_options_dict:
                self.column_5_selection.set(constants.COLUMN_5_DEFAULT)
            if self.column_6_selection.get() not in self.extra_options_dict:
                self.column_6_selection.set(constants.COLUMN_6_DEFAULT)
            if self.column_7_selection.get() not in self.extra_options_dict:
                self.column_7_selection.set(constants.COLUMN_7_DEFAULT)
            if self.deck_filter_selection.get() not in self.deck_colors:
                selection = [k for k in self.deck_colors.keys(
                ) if constants.DECK_FILTER_DEFAULT in k]
                self.deck_filter_selection.set(selection[0] if len(
                    selection) else constants.DECK_FILTER_DEFAULT)
            if self.taken_filter_selection.get() not in self.deck_colors:
                selection = [k for k in self.deck_colors.keys(
                ) if constants.DECK_FILTER_DEFAULT in k]
                self.taken_filter_selection.set(selection[0] if len(
                    selection) else constants.DECK_FILTER_DEFAULT)
            if self.taken_type_selection.get() not in constants.CARD_TYPE_DICT:
                self.taken_type_selection.set(
                    constants.CARD_TYPE_SELECTION_ALL)

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

            for key in self.main_options_dict:
                if column_2_menu:
                    column_2_menu.add_command(label=key,
                                              command=lambda value=key: self.column_2_selection.set(value))
                if column_3_menu:
                    column_3_menu.add_command(label=key,
                                              command=lambda value=key: self.column_3_selection.set(value))
                if column_4_menu:
                    column_4_menu.add_command(label=key,
                                              command=lambda value=key: self.column_4_selection.set(value))

                # self.deck_colors_options_list.append(data)
                self.column_2_list.append(key)
                self.column_3_list.append(key)
                self.column_4_list.append(key)

            for key in self.extra_options_dict:
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

            for key in self.deck_colors:
                deck_colors_menu.add_command(label=key,
                                             command=lambda value=key: self.deck_filter_selection.set(value))
                self.deck_filter_list.append(key)

        except Exception as error:
            overlay_logger.info("__update_column_options Error: %s", error)

        self._control_trace(True)

    def _default_settings_callback(self, *args):
        '''Callback function that's called when the Default Settings button is pressed'''
        CL.reset_config()
        self.configuration = CL.read_config()
        self._update_settings_data()
        self._update_draft_data()
        self._update_overlay_callback(False)

    def _update_source_callback(self, *args):
        '''Callback function that collects the set data a new data source is selected'''
        self._update_settings_storage()
        self._update_draft_data()
        self._update_settings_data()
        self._update_overlay_callback(False)

    def _update_settings_callback(self, *args):
        '''Callback function reconfigures the application whenever the settings change'''
        self._update_settings_storage()
        self._update_settings_data()
        self._update_overlay_callback(False)

    def _ui_size_callback(self, *args):
        '''Callback function updates the settings and opens a restart prompt'''
        self._update_settings_storage()
        self._update_settings_data()
        message_box = tkinter.messagebox.askyesno(
            title="Restart", message="A restart is required for this setting to take effect. Restart the application?")

        if message_box:
            restart_overlay(self)

    def _update_draft_data(self):
        '''Function that collects pertinent draft data from the LogScanner class'''
        self.draft.retrieve_set_data(
            self.data_sources[self.data_source_selection.get()])
        self.set_metrics = self.draft.retrieve_set_metrics(False)
        self.deck_colors = self.draft.retrieve_color_win_rate(
            self.filter_format_selection.get())
        self.tier_data, tier_dict = self.draft.retrieve_tier_data(
            self.tier_sources)
        self.main_options_dict = constants.COLUMNS_OPTIONS_MAIN_DICT.copy()
        self.extra_options_dict = constants.COLUMNS_OPTIONS_EXTRA_DICT.copy()
        for key, value in tier_dict.items():
            self.main_options_dict[key] = value
            self.extra_options_dict[key] = value

    def _update_draft(self):
        '''Function that that triggers a search of the Arena log for draft data'''
        update = False

        if self.draft.draft_start_search():
            update = True
            self.data_sources = self.draft.retrieve_data_sources()
            self.tier_sources = self.draft.retrieve_tier_source()
            self._update_data_source_options(True)
            self._update_draft_data()
            overlay_logger.info("%s, Mean: %.2f, Standard Deviation: %.2f",
                                self.draft.draft_sets,
                                self.set_metrics.mean,
                                self.set_metrics.standard_deviation)

        if self.draft.draft_data_search():
            update = True

        return update

    def _update_settings_storage(self):
        '''Function that transfers settings data from the overlay widgets to a data class'''
        try:
            selection = self.column_2_selection.get()
            self.configuration.column_2 = self.main_options_dict[
                selection] if selection in self.main_options_dict else self.main_options_dict[constants.COLUMN_2_DEFAULT]
            selection = self.column_3_selection.get()
            self.configuration.column_3 = self.main_options_dict[
                selection] if selection in self.main_options_dict else self.main_options_dict[constants.COLUMN_3_DEFAULT]
            selection = self.column_4_selection.get()
            self.configuration.column_4 = self.main_options_dict[
                selection] if selection in self.main_options_dict else self.main_options_dict[constants.COLUMN_4_DEFAULT]
            selection = self.column_5_selection.get()
            self.configuration.column_5 = self.extra_options_dict[
                selection] if selection in self.extra_options_dict else self.extra_options_dict[constants.COLUMN_5_DEFAULT]
            selection = self.column_6_selection.get()
            self.configuration.column_6 = self.extra_options_dict[
                selection] if selection in self.extra_options_dict else self.extra_options_dict[constants.COLUMN_6_DEFAULT]
            selection = self.column_7_selection.get()
            self.configuration.column_7 = self.extra_options_dict[
                selection] if selection in self.extra_options_dict else self.extra_options_dict[constants.COLUMN_7_DEFAULT]
            selection = self.deck_filter_selection.get()
            self.configuration.deck_filter = self.deck_colors[
                selection] if selection in self.deck_colors else self.deck_colors[constants.DECK_FILTER_DEFAULT]
            self.configuration.filter_format = self.filter_format_selection.get()
            self.configuration.result_format = self.result_format_selection.get()
            self.configuration.ui_size = self.ui_size_selection.get()

            self.configuration.missing_enabled = bool(
                self.missing_cards_checkbox_value.get())
            self.configuration.stats_enabled = bool(
                self.deck_stats_checkbox_value.get())
            self.configuration.auto_highest_enabled = bool(
                self.auto_highest_checkbox_value.get())
            self.configuration.curve_bonus_enabled = bool(
                self.curve_bonus_checkbox_value.get())
            self.configuration.color_bonus_enabled = bool(
                self.color_bonus_checkbox_value.get())
            self.configuration.bayesian_average_enabled = bool(
                self.bayesian_average_checkbox_value.get())
            self.configuration.color_identity_enabled = bool(
                self.color_identity_checkbox_value.get())
            self.configuration.draft_log_enabled = bool(
                self.draft_log_checkbox_value.get())
            self.configuration.taken_alsa_enabled = bool(
                self.taken_alsa_checkbox_value.get())
            self.configuration.taken_ata_enabled = bool(
                self.taken_ata_checkbox_value.get())
            self.configuration.taken_gpwr_enabled = bool(
                self.taken_gpwr_checkbox_value.get())
            self.configuration.taken_ohwr_enabled = bool(
                self.taken_ohwr_checkbox_value.get())
            self.configuration.taken_iwd_enabled = bool(
                self.taken_iwd_checkbox_value.get())
            self.configuration.taken_gndwr_enabled = bool(
                self.taken_gndwr_checkbox_value.get())
            self.configuration.taken_gdwr_enabled = bool(
                self.taken_gdwr_checkbox_value.get())
            self.configuration.card_colors_enabled = bool(
                self.card_colors_checkbox_value.get())
            CL.write_config(self.configuration)
        except Exception as error:
            overlay_logger.info("__update_settings_storage Error: %s", error)

    def _update_settings_data(self):
        '''Function that transfers settings data from a data class to the overlay widgets'''
        self._control_trace(False)
        try:
            selection = [k for k, v in self.main_options_dict.items(
            ) if v == self.configuration.column_2]
            self.column_2_selection.set(selection[0] if len(
                selection) else constants.COLUMN_2_DEFAULT)
            selection = [k for k, v in self.main_options_dict.items(
            ) if v == self.configuration.column_3]
            self.column_3_selection.set(selection[0] if len(
                selection) else constants.COLUMN_3_DEFAULT)
            selection = [k for k, v in self.main_options_dict.items(
            ) if v == self.configuration.column_4]
            self.column_4_selection.set(selection[0] if len(
                selection) else constants.COLUMN_4_DEFAULT)
            selection = [k for k, v in self.extra_options_dict.items(
            ) if v == self.configuration.column_5]
            self.column_5_selection.set(selection[0] if len(
                selection) else constants.COLUMN_5_DEFAULT)
            selection = [k for k, v in self.extra_options_dict.items(
            ) if v == self.configuration.column_6]
            self.column_6_selection.set(selection[0] if len(
                selection) else constants.COLUMN_6_DEFAULT)
            selection = [k for k, v in self.extra_options_dict.items(
            ) if v == self.configuration.column_7]
            self.column_7_selection.set(selection[0] if len(
                selection) else constants.COLUMN_7_DEFAULT)
            selection = [k for k, v in self.deck_colors.items(
            ) if v == self.configuration.deck_filter]
            self.deck_filter_selection.set(selection[0] if len(
                selection) else constants.DECK_FILTER_DEFAULT)
            self.filter_format_selection.set(self.configuration.filter_format)
            self.result_format_selection.set(self.configuration.result_format)
            self.ui_size_selection.set(self.configuration.ui_size)
            self.deck_stats_checkbox_value.set(
                self.configuration.stats_enabled)
            self.missing_cards_checkbox_value.set(
                self.configuration.missing_enabled)
            self.auto_highest_checkbox_value.set(
                self.configuration.auto_highest_enabled)
            self.curve_bonus_checkbox_value.set(
                self.configuration.curve_bonus_enabled)
            self.color_bonus_checkbox_value.set(
                self.configuration.color_bonus_enabled)
            self.bayesian_average_checkbox_value.set(
                self.configuration.bayesian_average_enabled)
            self.color_identity_checkbox_value.set(
                self.configuration.color_identity_enabled)
            self.draft_log_checkbox_value.set(
                self.configuration.draft_log_enabled)
            self.taken_alsa_checkbox_value.set(
                self.configuration.taken_alsa_enabled)
            self.taken_ata_checkbox_value.set(
                self.configuration.taken_ata_enabled)
            self.taken_gpwr_checkbox_value.set(
                self.configuration.taken_gpwr_enabled)
            self.taken_ohwr_checkbox_value.set(
                self.configuration.taken_ohwr_enabled)
            self.taken_gdwr_checkbox_value.set(
                self.configuration.taken_gdwr_enabled)
            self.taken_gndwr_checkbox_value.set(
                self.configuration.taken_gndwr_enabled)
            self.taken_iwd_checkbox_value.set(
                self.configuration.taken_iwd_enabled)
            self.card_colors_checkbox_value.set(
                self.configuration.card_colors_enabled)
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
            self.color_identity_checkbox_value.set(False)
            self.bayesian_average_checkbox_value.set(False)
            self.draft_log_checkbox_value.set(False)
            self.taken_alsa_checkbox_value.set(True)
            self.taken_ata_checkbox_value.set(True)
            self.taken_gpwr_checkbox_value.set(True)
            self.taken_ohwr_checkbox_value.set(True)
            self.taken_gdwr_checkbox_value.set(True)
            self.taken_gndwr_checkbox_value.set(True)
            self.taken_iwd_checkbox_value.set(True)
            self.card_colors_checkbox_value.set(True)
            overlay_logger.info("__update_settings_data Error: %s", error)
        self._control_trace(True)

        if not self.step_through:
            self.draft.log_enable(self.configuration.draft_log_enabled)

    def _initialize_overlay_widgets(self):
        '''Set the overlay widgets in the main window to a known state at startup'''
        self._update_data_source_options(False)
        self._update_column_options()

        self._enable_deck_stats_table(self.deck_stats_checkbox_value.get())
        self._enable_missing_cards_table(
            self.missing_cards_checkbox_value.get())
        self._update_current_draft_label(
            self.draft.draft_sets, self.draft.draft_type)
        self._update_pack_pick_label(
            self.draft.current_pack, self.draft.current_pick)

        fields = {"Column1": constants.DATA_FIELD_NAME,
                  "Column2": self.main_options_dict[self.column_2_selection.get()],
                  "Column3": self.main_options_dict[self.column_3_selection.get()],
                  "Column4": self.main_options_dict[self.column_4_selection.get()],
                  "Column5": self.extra_options_dict[self.column_5_selection.get()],
                  "Column6": self.extra_options_dict[self.column_6_selection.get()],
                  "Column7": self.extra_options_dict[self.column_7_selection.get()], }
        self._update_pack_table([],  self.deck_filter_selection.get(), fields)

        self._update_missing_table(
            [], [], [], self.deck_filter_selection.get(), fields)

        self.root.update()

        self._update_deck_stats_callback()

        self.root.update()

    def _update_overlay_callback(self, enable_draft_search):
        '''Callback function that updates all of the widgets in the main window'''
        update = True
        if enable_draft_search:
            update = self._update_draft()

        if not update:
            return

        self._update_data_source_options(False)
        self._update_column_options()

        self._enable_deck_stats_table(self.deck_stats_checkbox_value.get())
        self._enable_missing_cards_table(
            self.missing_cards_checkbox_value.get())

        taken_cards = self.draft.retrieve_taken_cards()

        filtered = self._identify_auto_colors(
            taken_cards, self.deck_filter_selection.get())
        fields = {"Column1": constants.DATA_FIELD_NAME,
                  "Column2": self.main_options_dict[self.column_2_selection.get()],
                  "Column3": self.main_options_dict[self.column_3_selection.get()],
                  "Column4": self.main_options_dict[self.column_4_selection.get()],
                  "Column5": self.extra_options_dict[self.column_5_selection.get()],
                  "Column6": self.extra_options_dict[self.column_6_selection.get()],
                  "Column7": self.extra_options_dict[self.column_7_selection.get()], }

        self._update_current_draft_label(
            self.draft.draft_sets, self.draft.draft_type)
        self._update_pack_pick_label(
            self.draft.current_pack, self.draft.current_pick)
        pack_index = (self.draft.current_pick - 1) % 8

        pack_cards = self.draft.retrieve_pack_cards(pack_index)
        self._update_pack_table(pack_cards,
                                filtered,
                                fields)

        self._update_missing_table(pack_cards,
                                   self.draft.retrieve_initial_pack_cards(
                                       pack_index),
                                   self.draft.retrieve_picked_cards(
                                       pack_index),
                                   filtered,
                                   fields)

        self._update_deck_stats_callback()
        self._update_taken_table()

    def _update_deck_stats_callback(self, *args):
        '''Callback function that updates the Deck Stats table in the main window'''
        self.root.update_idletasks()
        self._update_deck_stats_table(self.draft.retrieve_taken_cards(
        ), self.stat_options_selection.get(), self.pack_table.winfo_width())

    def _arena_log_check(self):
        '''Function that monitors the Arena log every 1000ms to determine if there's new draft data'''
        try:
            self.current_timestamp = os.stat(self.arena_file).st_mtime

            if self.current_timestamp != self.previous_timestamp:
                self.previous_timestamp = self.current_timestamp

                while True:

                    self._update_overlay_callback(True)
                    if self.draft.step_through:
                        input("Continue?")
                    else:
                        break
        except Exception as error:
            overlay_logger.info("_arena_log_check Error: %s", error)
            self._reset_draft(True)

        self.log_check_id = self.root.after(1000, self._arena_log_check)

    def lift_window(self):
        '''Function that's used to minimize a window or set it as the top most window'''
        if self.root.state() == "iconic":
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
        else:
            self.root.attributes("-topmost", False)
            self.root.iconify()

    def _update_set_start_date(self, start, selection, set_list, *args):
        '''Function that's used to determine if a set in the Set View window has minimum start date
           Example: The user shouldn't download Arena Cube data that's more than a couple of months old
           or else they risk downloading data from multiple separate cubes
        '''
        try:
            set_data = set_list[selection.get()]

            if constants.SET_START_DATE in set_data:
                start.delete(0, tkinter.END)
                start.insert(tkinter.END, set_data[constants.SET_START_DATE])

            self.root.update()
        except Exception as error:
            overlay_logger.info("__update_set_start_date Error: %s", error)

    def _open_set_view_window(self):
        '''Creates the Set View window'''
        popup = tkinter.Toplevel()
        popup.wm_title("Set Data")
        popup.resizable(width=False, height=True)
        popup.attributes("-topmost", True)

        location_x, location_y = identify_safe_coordinates(self.root,
                                                           self._scale_value(
                                                               1000),
                                                           self._scale_value(
                                                               170),
                                                           self._scale_value(
                                                               250),
                                                           self._scale_value(20))
        popup.wm_geometry(f"+{location_x}+{location_y}")

        tkinter.Grid.rowconfigure(popup, 1, weight=1)
        try:
            sets = self.extractor.return_set_list()

            headers = {"SET": {"width": .40, "anchor": tkinter.W},
                       "DRAFT": {"width": .20, "anchor": tkinter.CENTER},
                       "START DATE": {"width": .20, "anchor": tkinter.CENTER},
                       "END DATE": {"width": .20, "anchor": tkinter.CENTER}}

            list_box_frame = tkinter.Frame(popup)
            list_box_scrollbar = tkinter.Scrollbar(
                list_box_frame, orient=tkinter.VERTICAL)
            list_box_scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)

            list_box = self._create_header("set_table",
                                           list_box_frame, 0, self.fonts_dict["Sets.TableRow"], headers, self._scale_value(500), True, True, "Set.Treeview", True)

            list_box.config(yscrollcommand=list_box_scrollbar.set)
            list_box_scrollbar.config(command=list_box.yview)

            notice_label = Label(popup, text="17Lands has an embargo period of 12 days for new sets on Magic Arena. Visit https://www.17lands.com for more details.",
                                 style="Notes.TLabel", anchor="c")
            set_label = Label(popup, text="Set:",
                              style="SetOptions.TLabel")
            draft_label = Label(popup, text="Draft:",
                                style="SetOptions.TLabel")
            start_label = Label(popup, text="Start Date:",
                                style="SetOptions.TLabel")
            end_label = Label(popup, text="End Date:",
                              style="SetOptions.TLabel")
            draft_choices = constants.LIMITED_TYPE_LIST

            status_text = tkinter.StringVar()
            status_label = Label(popup, textvariable=status_text,
                                 style="Status.TLabel", anchor="c")
            status_text.set("Retrieving Set List")

            draft_value = tkinter.StringVar(self.root)
            draft_entry = OptionMenu(
                popup, draft_value, draft_choices[0], *draft_choices)
            menu = self.root.nametowidget(draft_entry['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            start_entry = tkinter.Entry(popup)
            start_entry.insert(tkinter.END, constants.SET_START_DATE_DEFAULT)
            end_entry = tkinter.Entry(popup)
            end_entry.insert(tkinter.END, str(date.today()))

            set_choices = list(sets.keys())

            set_value = tkinter.StringVar(self.root)
            set_entry = OptionMenu(
                popup, set_value, set_choices[0], *set_choices)
            menu = self.root.nametowidget(set_entry['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            set_value.trace("w", lambda *args, start=start_entry, selection=set_value,
                            set_list=sets: self._update_set_start_date(start, selection, set_list, *args))

            progress = Progressbar(
                popup, orient=tkinter.HORIZONTAL, length=100, mode='determinate')

            add_button = Button(popup, command=lambda: self._add_set(popup,
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

            notice_label.grid(row=0, column=0, columnspan=8, sticky='nsew')
            list_box_frame.grid(row=1, column=0, columnspan=8, sticky='nsew')
            set_label.grid(row=2, column=0, sticky='nsew')
            set_entry.grid(row=2, column=1, sticky='nsew')
            start_label.grid(row=2, column=2, sticky='nsew')
            start_entry.grid(row=2, column=3, sticky='nsew')
            end_label.grid(row=2, column=4, sticky='nsew')
            end_entry.grid(row=2, column=5, sticky='nsew')
            draft_label.grid(row=2, column=6, sticky='nsew')
            draft_entry.grid(row=2, column=7, sticky='nsew')
            add_button.grid(row=3, column=0, columnspan=8, sticky='nsew')
            progress.grid(row=4, column=0, columnspan=8, sticky='nsew')
            status_label.grid(row=5, column=0, columnspan=8, sticky='nsew')

            list_box.pack(expand=True, fill="both")

            self._update_set_table(list_box, sets)
            status_text.set("")
            popup.update()
        except Exception as error:
            overlay_logger.info("__open_set_view_window Error: %s", error)

    def _open_card_compare_window(self):
        '''Creates the Card Compare window'''
        popup = tkinter.Toplevel()
        popup.wm_title("Card Compare")
        popup.resizable(width=False, height=True)
        popup.attributes("-topmost", True)
        location_x, location_y = identify_safe_coordinates(self.root,
                                                           self._scale_value(
                                                               400),
                                                           self._scale_value(
                                                               170),
                                                           self._scale_value(
                                                               250),
                                                           self._scale_value(0))
        popup.wm_geometry(f"+{location_x}+{location_y}")

        try:
            tkinter.Grid.rowconfigure(popup, 2, weight=1)
            tkinter.Grid.columnconfigure(popup, 0, weight=1)

            taken_cards = self.draft.retrieve_taken_cards()

            filtered = self._identify_auto_colors(
                taken_cards, self.deck_filter_selection.get())
            fields = {"Column1": constants.DATA_FIELD_NAME,
                      "Column2": self.main_options_dict[self.column_2_selection.get()],
                      "Column3": self.main_options_dict[self.column_3_selection.get()],
                      "Column4": self.main_options_dict[self.column_4_selection.get()],
                      "Column5": self.extra_options_dict[self.column_5_selection.get()],
                      "Column6": self.extra_options_dict[self.column_6_selection.get()],
                      "Column7": self.extra_options_dict[self.column_7_selection.get()], }

            matching_cards = []

            card_frame = tkinter.Frame(popup)

            set_card_names = [v[constants.DATA_FIELD_NAME]
                              for k, v in self.draft.set_data["card_ratings"].items()]
            card_entry = AutocompleteEntry(
                card_frame,
                completevalues=set_card_names
            )

            headers = {"Column1": {"width": .46, "anchor": tkinter.W},
                       "Column2": {"width": .18, "anchor": tkinter.CENTER},
                       "Column3": {"width": .18, "anchor": tkinter.CENTER},
                       "Column4": {"width": .18, "anchor": tkinter.CENTER},
                       "Column5": {"width": .18, "anchor": tkinter.CENTER},
                       "Column6": {"width": .18, "anchor": tkinter.CENTER},
                       "Column7": {"width": .18, "anchor": tkinter.CENTER}}

            compare_table_frame = tkinter.Frame(popup)
            compare_scrollbar = tkinter.Scrollbar(
                compare_table_frame, orient=tkinter.VERTICAL)
            compare_scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
            compare_table = self._create_header("compare_table", compare_table_frame, 0, self.fonts_dict["All.TableRow"], headers,
                                                self.configuration.table_width, True, True, constants.TABLE_STYLE, False)
            compare_table.config(yscrollcommand=compare_scrollbar.set)
            compare_scrollbar.config(command=compare_table.yview)

            clear_button = Button(popup, text="Clear", command=lambda: self._clear_compare_table(
                compare_table, matching_cards))

            card_frame.grid(row=0, column=0, sticky="nsew")
            clear_button.grid(row=1, column=0, sticky="nsew")
            compare_table_frame.grid(row=2, column=0, sticky="nsew")

            compare_table.pack(expand=True, fill="both")
            card_entry.pack(side=tkinter.LEFT, expand=True, fill="both")

            card_entry.bind("<Return>", lambda event: self._update_compare_table(compare_table,
                                                                                 matching_cards,
                                                                                 card_entry,
                                                                                 self.draft.set_data["card_ratings"],
                                                                                 filtered,
                                                                                 fields))

            self._update_compare_table(compare_table,
                                       matching_cards,
                                       card_entry,
                                       self.draft.set_data["card_ratings"],
                                       filtered,
                                       fields)

        except Exception as error:
            overlay_logger.info("__open_card_compare_window Error: %s", error)

    def _close_taken_cards_window(self, popup):
        '''Clear taken card table data when the Taken Cards window is closed'''
        self.taken_table = None

        popup.destroy()

    def _open_taken_cards_window(self):
        '''Creates the Taken Cards window'''
        popup = tkinter.Toplevel()
        popup.wm_title("Taken Cards")
        popup.attributes("-topmost", True)
        popup.resizable(width=False, height=True)
        location_x, location_y = identify_safe_coordinates(self.root,
                                                           self._scale_value(
                                                               400),
                                                           self._scale_value(
                                                               170),
                                                           self._scale_value(
                                                               250),
                                                           self._scale_value(0))
        popup.wm_geometry(f"+{location_x}+{location_y}")

        popup.protocol(
            "WM_DELETE_WINDOW", lambda window=popup: self._close_taken_cards_window(window))
        self._control_trace(False)
        try:
            tkinter.Grid.rowconfigure(popup, 4, weight=1)
            tkinter.Grid.columnconfigure(popup, 6, weight=1)

            taken_cards = self.draft.retrieve_taken_cards()
            copy_button = Button(popup, command=lambda: copy_taken(taken_cards),
                                 text="Copy to Clipboard")

            headers = {"Column1": {"width": .40, "anchor": tkinter.W},
                       "Column2": {"width": .20, "anchor": tkinter.CENTER},
                       "Column3": {"width": .20, "anchor": tkinter.CENTER},
                       "Column4": {"width": .20, "anchor": tkinter.CENTER},
                       "Column5": {"width": .20, "anchor": tkinter.CENTER},
                       "Column6": {"width": .20, "anchor": tkinter.CENTER},
                       "Column7": {"width": .20, "anchor": tkinter.CENTER},
                       "Column8": {"width": .20, "anchor": tkinter.CENTER},
                       "Column9": {"width": .20, "anchor": tkinter.CENTER},
                       "Column10": {"width": .20, "anchor": tkinter.CENTER},
                       "Column11": {"width": .20, "anchor": tkinter.CENTER},
                       }

            taken_table_frame = tkinter.Frame(popup)
            taken_scrollbar = tkinter.Scrollbar(
                taken_table_frame, orient=tkinter.VERTICAL)
            taken_scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
            self.taken_table = self._create_header("taken_table",
                                                   taken_table_frame, 0, self.fonts_dict["All.TableRow"], headers, self._scale_value(440), True, True, "Taken.Treeview", False)
            self.taken_table.config(yscrollcommand=taken_scrollbar.set)
            taken_scrollbar.config(command=self.taken_table.yview)

            option_frame = tkinter.Frame(
                popup, highlightbackground="white", highlightthickness=2)
            taken_filter_label = Label(
                option_frame, text="Deck Filter:", style="MainSections.TLabel", anchor="w")
            self.taken_filter_selection.set(self.deck_filter_selection.get())
            taken_filter_list = self.deck_filter_list

            taken_option = OptionMenu(option_frame, self.taken_filter_selection, self.taken_filter_selection.get(
            ), *taken_filter_list, style="All.TMenubutton")
            menu = self.root.nametowidget(taken_option['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            type_checkbox_frame = tkinter.Frame(
                popup, highlightbackground="white", highlightthickness=2)

            taken_creature_checkbox = Checkbutton(type_checkbox_frame,
                                                  text="CREATURES",
                                                  style="Taken.TCheckbutton",
                                                  variable=self.taken_type_creature_checkbox_value,
                                                  onvalue=1,
                                                  offvalue=0)

            taken_land_checkbox = Checkbutton(type_checkbox_frame,
                                              text="LANDS",
                                              style="Taken.TCheckbutton",
                                              variable=self.taken_type_land_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)

            taken_instant_sorcery_checkbox = Checkbutton(type_checkbox_frame,
                                                         text="INSTANTS/SORCERIES",
                                                         style="Taken.TCheckbutton",
                                                         variable=self.taken_type_instant_sorcery_checkbox_value,
                                                         onvalue=1,
                                                         offvalue=0)

            taken_other_checkbox = Checkbutton(type_checkbox_frame,
                                               text="OTHER",
                                               style="Taken.TCheckbutton",
                                               variable=self.taken_type_other_checkbox_value,
                                               onvalue=1,
                                               offvalue=0)

            checkbox_frame = tkinter.Frame(
                popup, highlightbackground="white", highlightthickness=2)

            taken_alsa_checkbox = Checkbutton(checkbox_frame,
                                              text="ALSA",
                                              style="Taken.TCheckbutton",
                                              variable=self.taken_alsa_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)
            taken_ata_checkbox = Checkbutton(checkbox_frame,
                                             text="ATA",
                                             style="Taken.TCheckbutton",
                                             variable=self.taken_ata_checkbox_value,
                                             onvalue=1,
                                             offvalue=0)
            taken_gpwr_checkbox = Checkbutton(checkbox_frame,
                                              text="GPWR",
                                              style="Taken.TCheckbutton",
                                              variable=self.taken_gpwr_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)
            taken_ohwr_checkbox = Checkbutton(checkbox_frame,
                                              text="OHWR",
                                              style="Taken.TCheckbutton",
                                              variable=self.taken_ohwr_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)
            taken_gdwr_checkbox = Checkbutton(checkbox_frame,
                                              text="GDWR",
                                              style="Taken.TCheckbutton",
                                              variable=self.taken_gdwr_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)
            taken_gndwr_checkbox = Checkbutton(checkbox_frame,
                                               text="GNSWR",
                                               style="Taken.TCheckbutton",
                                               variable=self.taken_gndwr_checkbox_value,
                                               onvalue=1,
                                               offvalue=0)
            taken_iwd_checkbox = Checkbutton(checkbox_frame,
                                             text="IWD",
                                             style="Taken.TCheckbutton",
                                             variable=self.taken_iwd_checkbox_value,
                                             onvalue=1,
                                             offvalue=0)

            option_frame.grid(row=0, column=0, columnspan=7, sticky="nsew")
            type_checkbox_frame.grid(
                row=1, column=0, columnspan=7, sticky="nsew", pady=5)
            checkbox_frame.grid(row=2, column=0, columnspan=7, sticky="nsew")
            copy_button.grid(row=3, column=0, columnspan=7, sticky="nsew")
            taken_table_frame.grid(
                row=4, column=0, columnspan=7, sticky="nsew")

            self.taken_table.pack(side=tkinter.LEFT, expand=True, fill="both")

            taken_creature_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")

            taken_land_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")

            taken_instant_sorcery_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")

            taken_other_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")

            taken_alsa_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")
            taken_ata_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")
            taken_gpwr_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")
            taken_ohwr_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")
            taken_gdwr_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")
            taken_gndwr_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")
            taken_iwd_checkbox.pack(
                side=tkinter.LEFT, expand=True, fill="both")

            taken_filter_label.pack(side=tkinter.LEFT, expand=True, fill=None)
            taken_option.pack(side=tkinter.LEFT, expand=True, fill="both")

            self._update_taken_table()
            popup.update()
        except Exception as error:
            overlay_logger.info("__open_taken_cards_window Error: %s", error)
        self._control_trace(True)

    def _open_suggest_deck_window(self):
        '''Creates the Suggest Deck window'''
        popup = tkinter.Toplevel()
        popup.wm_title("Suggested Decks")
        popup.attributes("-topmost", True)
        popup.resizable(width=False, height=False)

        location_x, location_y = identify_safe_coordinates(self.root,
                                                           self._scale_value(
                                                               400),
                                                           self._scale_value(
                                                               170),
                                                           self._scale_value(
                                                               250),
                                                           self._scale_value(0))
        popup.wm_geometry(f"+{location_x}+{location_y}")

        try:
            tkinter.Grid.rowconfigure(popup, 3, weight=1)

            suggested_decks = CL.suggest_deck(
                self.draft.retrieve_taken_cards(), self.set_metrics, self.configuration)

            choices = ["None"]
            deck_color_options = {}

            if suggested_decks:
                choices = []
                for key, value in suggested_decks.items():
                    rating_label = f"{key} {value['type']} (Rating:{value['rating']})"
                    deck_color_options[rating_label] = key
                    choices.append(rating_label)

            deck_colors_label = Label(
                popup, text="Deck Colors:", anchor='e', style="MainSections.TLabel")

            deck_colors_value = tkinter.StringVar(popup)
            deck_colors_entry = OptionMenu(
                popup, deck_colors_value, choices[0], *choices)
            menu = self.root.nametowidget(deck_colors_entry['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            deck_colors_button = Button(popup, command=lambda: self._update_suggest_table(suggest_table,
                                                                                          deck_colors_value,
                                                                                          suggested_decks,
                                                                                          deck_color_options),
                                        text="Update")

            copy_button = Button(popup, command=lambda: copy_suggested(deck_colors_value,
                                                                       suggested_decks,
                                                                       deck_color_options),
                                 text="Copy to Clipboard")

            headers = {"CARD": {"width": .35, "anchor": tkinter.W},
                       "COUNT": {"width": .14, "anchor": tkinter.CENTER},
                       "COLOR": {"width": .12, "anchor": tkinter.CENTER},
                       "COST": {"width": .10, "anchor": tkinter.CENTER},
                       "TYPE": {"width": .29, "anchor": tkinter.CENTER}}

            #style = Style()
            #style.configure("Suggest.Treeview", rowheight=self._scale_value(25))

            suggest_table_frame = tkinter.Frame(popup)
            suggest_scrollbar = tkinter.Scrollbar(
                suggest_table_frame, orient=tkinter.VERTICAL)
            suggest_scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
            suggest_table = self._create_header("suggest_table",
                                                suggest_table_frame, 0, self.fonts_dict["All.TableRow"], headers, self._scale_value(450), True, True, "Suggest.Treeview", False)
            suggest_table.config(yscrollcommand=suggest_scrollbar.set)
            suggest_scrollbar.config(command=suggest_table.yview)

            deck_colors_label.grid(
                row=0, column=0, columnspan=1, sticky="nsew")
            deck_colors_entry.grid(
                row=0, column=1, columnspan=1, sticky="nsew")
            deck_colors_button.grid(
                row=1, column=0, columnspan=2, sticky="nsew")
            copy_button.grid(row=2, column=0, columnspan=2, sticky="nsew")
            suggest_table_frame.grid(
                row=3, column=0, columnspan=2, sticky='nsew')

            suggest_table.pack(expand=True, fill='both')

            self._update_suggest_table(
                suggest_table, deck_colors_value, suggested_decks, deck_color_options)
        except Exception as error:
            overlay_logger.info("__open_suggest_deck_window Error: %s", error)

    def _close_settings_window(self, popup):
        '''Clears settings data when the Settings window is closed'''
        self.column_2_options = None
        self.column_3_options = None
        self.column_4_options = None
        self.column_5_options = None
        self.column_6_options = None
        self.column_7_options = None
        popup.destroy()

    def _open_settings_window(self):
        '''Creates the Settings window'''
        popup = tkinter.Toplevel()
        popup.wm_title("Settings")
        popup.protocol("WM_DELETE_WINDOW",
                       lambda window=popup: self._close_settings_window(window))
        popup.attributes("-topmost", True)
        popup.resizable(width=False, height=False)
        location_x, location_y = identify_safe_coordinates(self.root,
                                                           self._scale_value(
                                                               400),
                                                           self._scale_value(
                                                               170),
                                                           self._scale_value(
                                                               250),
                                                           self._scale_value(0))
        popup.wm_geometry(f"+{location_x}+{location_y}")

        try:
            tkinter.Grid.columnconfigure(popup, 1, weight=1)

            self._control_trace(False)

            column_2_label = Label(
                popup, text="Column 2:", style="MainSections.TLabel", anchor="w")
            column_3_label = Label(
                popup, text="Column 3:", style="MainSections.TLabel", anchor="w")
            column_4_label = Label(
                popup, text="Column 4:", style="MainSections.TLabel", anchor="w")
            column_5_label = Label(
                popup, text="Column 5:", style="MainSections.TLabel", anchor="w")
            column_6_label = Label(
                popup, text="Column 6:", style="MainSections.TLabel", anchor="w")
            column_7_label = Label(
                popup, text="Column 7:", style="MainSections.TLabel", anchor="w")
            filter_format_label = Label(
                popup, text="Deck Filter Format:", style="MainSections.TLabel", anchor="w")
            result_format_label = Label(
                popup, text="Win Rate Format:", style="MainSections.TLabel", anchor="w")
            scale_label = Label(
                popup, text="UI Size:", style="MainSections.TLabel", anchor="w")
            deck_stats_label = Label(popup, text="Enable Draft Stats:",
                                     style="MainSections.TLabel", anchor="w")
            deck_stats_checkbox = Checkbutton(popup,
                                              variable=self.deck_stats_checkbox_value,
                                              onvalue=1,
                                              offvalue=0)
            missing_cards_label = Label(
                popup, text="Enable Missing Cards:", style="MainSections.TLabel", anchor="w")
            missing_cards_checkbox = Checkbutton(popup,
                                                 variable=self.missing_cards_checkbox_value,
                                                 onvalue=1,
                                                 offvalue=0)

            auto_highest_label = Label(
                popup, text="Enable Highest Rated:", style="MainSections.TLabel", anchor="w")
            auto_highest_checkbox = Checkbutton(popup,
                                                variable=self.auto_highest_checkbox_value,
                                                onvalue=1,
                                                offvalue=0)

            bayesian_average_label = Label(
                popup, text="Enable Bayesian Average:", style="MainSections.TLabel", anchor="w")
            bayesian_average_checkbox = Checkbutton(popup,
                                                    variable=self.bayesian_average_checkbox_value,
                                                    onvalue=1,
                                                    offvalue=0)

            draft_log_label = Label(popup, text="Enable Draft Log:",
                                    style="MainSections.TLabel", anchor="w")
            draft_log_checkbox = Checkbutton(popup,
                                             variable=self.draft_log_checkbox_value,
                                             onvalue=1,
                                             offvalue=0)

            card_colors_label = Label(
                popup, text="Enable Row Colors:", style="MainSections.TLabel", anchor="w")
            card_colors_checkbox = Checkbutton(popup,
                                               variable=self.card_colors_checkbox_value,
                                               onvalue=1,
                                               offvalue=0)

            color_identity_label = Label(
                popup, text="Enable Color Identity:", style="MainSections.TLabel", anchor="w")
            color_identity_checkbox = Checkbutton(popup,
                                                  variable=self.color_identity_checkbox_value,
                                                  onvalue=1,
                                                  offvalue=0)

            self.column_2_options = OptionMenu(popup, self.column_2_selection, self.column_2_selection.get(
            ), *self.column_2_list, style="All.TMenubutton")
            self.column_2_options.config(width=15)
            menu = self.root.nametowidget(self.column_2_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            self.column_3_options = OptionMenu(popup, self.column_3_selection, self.column_3_selection.get(
            ), *self.column_3_list, style="All.TMenubutton")
            self.column_3_options.config(width=15)
            menu = self.root.nametowidget(self.column_3_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            self.column_4_options = OptionMenu(popup, self.column_4_selection, self.column_4_selection.get(
            ), *self.column_4_list, style="All.TMenubutton")
            self.column_4_options.config(width=15)
            menu = self.root.nametowidget(self.column_4_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            self.column_5_options = OptionMenu(popup, self.column_5_selection, self.column_5_selection.get(
            ), *self.column_5_list, style="All.TMenubutton")
            self.column_5_options.config(width=15)
            menu = self.root.nametowidget(self.column_5_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            self.column_6_options = OptionMenu(popup, self.column_6_selection, self.column_6_selection.get(
            ), *self.column_6_list, style="All.TMenubutton")
            self.column_6_options.config(width=15)
            menu = self.root.nametowidget(self.column_6_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            self.column_7_options = OptionMenu(popup, self.column_7_selection, self.column_7_selection.get(
            ), *self.column_7_list, style="All.TMenubutton")
            self.column_7_options.config(width=15)
            menu = self.root.nametowidget(self.column_7_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            filter_format_options = OptionMenu(popup, self.filter_format_selection, self.filter_format_selection.get(
            ), *self.filter_format_list, style="All.TMenubutton")
            filter_format_options.config(width=15)
            menu = self.root.nametowidget(filter_format_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            result_format_options = OptionMenu(popup, self.result_format_selection, self.result_format_selection.get(
            ), *self.result_format_list, style="All.TMenubutton")
            result_format_options.config(width=15)
            menu = self.root.nametowidget(result_format_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            ui_size_options = OptionMenu(popup, self.ui_size_selection, self.ui_size_selection.get(
            ), *self.ui_size_list, style="All.TMenubutton", command=self._ui_size_callback)
            ui_size_options.config(width=15)
            menu = self.root.nametowidget(ui_size_options['menu'])
            menu.config(font=self.fonts_dict["All.TMenubutton"])

            default_button = Button(
                popup, command=self._default_settings_callback, text="Default Settings")

            row_padding_y = (self._scale_value(3), self._scale_value(3))
            row_padding_x = (self._scale_value(10), )
            column_2_label.grid(row=0, column=0, columnspan=1,
                                sticky="nsew", padx=row_padding_x, pady=row_padding_y)
            column_3_label.grid(row=1, column=0, columnspan=1,
                                sticky="nsew", padx=row_padding_x, pady=row_padding_y)
            column_4_label.grid(row=2, column=0, columnspan=1,
                                sticky="nsew", padx=row_padding_x, pady=row_padding_y)
            column_5_label.grid(row=3, column=0, columnspan=1,
                                sticky="nsew", padx=row_padding_x, pady=row_padding_y)
            column_6_label.grid(row=4, column=0, columnspan=1,
                                sticky="nsew", padx=row_padding_x, pady=row_padding_y)
            column_7_label.grid(row=5, column=0, columnspan=1,
                                sticky="nsew", padx=row_padding_x, pady=row_padding_y)
            filter_format_label.grid(
                row=6, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            result_format_label.grid(
                row=7, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            scale_label.grid(
                row=8, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            self.column_2_options.grid(
                row=0, column=1, columnspan=1, sticky="nsew")
            self.column_3_options.grid(
                row=1, column=1, columnspan=1, sticky="nsew")
            self.column_4_options.grid(
                row=2, column=1, columnspan=1, sticky="nsew")
            self.column_5_options.grid(
                row=3, column=1, columnspan=1, sticky="nsew")
            self.column_6_options.grid(
                row=4, column=1, columnspan=1, sticky="nsew")
            self.column_7_options.grid(
                row=5, column=1, columnspan=1, sticky="nsew")
            filter_format_options.grid(
                row=6, column=1, columnspan=1, sticky="nsew")
            result_format_options.grid(
                row=7, column=1, columnspan=1, sticky="nsew")
            ui_size_options.grid(
                row=8, column=1, columnspan=1, sticky="nsew")
            card_colors_label.grid(
                row=9, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            card_colors_checkbox.grid(
                row=9, column=1, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            color_identity_label.grid(
                row=10, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            color_identity_checkbox.grid(
                row=10, column=1, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            deck_stats_label.grid(
                row=11, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            deck_stats_checkbox.grid(
                row=11, column=1, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            missing_cards_label.grid(
                row=12, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            missing_cards_checkbox.grid(
                row=12, column=1, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            auto_highest_label.grid(
                row=13, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            auto_highest_checkbox.grid(
                row=13, column=1, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            bayesian_average_label.grid(
                row=14, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            bayesian_average_checkbox.grid(
                row=14, column=1, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            draft_log_label.grid(
                row=15, column=0, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            draft_log_checkbox.grid(
                row=15, column=1, columnspan=1, sticky="nsew",
                padx=row_padding_x, pady=row_padding_y)
            default_button.grid(row=16, column=0, columnspan=2, sticky="nsew")

            self._control_trace(True)

        except Exception as error:
            overlay_logger.info("__open_settings_window Error: %s", error)

    def _add_set(self, popup, draft_set, draft, start, end, button, progress, list_box, sets, status, version):
        '''Initiates the set download process when the Add Set button is clicked'''
        result = True
        result_string = ""
        return_size = 0
        while True:
            try:
                message_box = tkinter.messagebox.askyesno(
                    title="Download", message=f"17Lands updates their card data once a day at 03:00 UTC. Are you sure that you want to download {draft_set.get()} {draft.get()} data?")
                if not message_box:
                    break

                status.set("Starting Download Process")
                self.extractor.clear_data()
                button['state'] = 'disabled'
                progress['value'] = 0
                popup.update()
                self.extractor.select_sets(sets[draft_set.get()])
                self.extractor.set_draft_type(draft.get())
                if not self.extractor.set_start_date(start.get()):
                    result = False
                    result_string = "Invalid Start Date (YYYY-MM-DD)"
                    break
                if not self.extractor.set_end_date(end.get()):
                    result = False
                    result_string = "Invalid End Date (YYYY-MM-DD)"
                    break
                self.extractor.set_version(version)
                status.set("Downloading Color Ratings")
                self.extractor.retrieve_17lands_color_ratings()

                result, result_string, temp_size = self.extractor.download_card_data(
                    popup, progress, status, self.configuration.database_size)

                if not result:
                    break

                if not self.extractor.export_card_data():
                    result = False
                    result_string = "File Write Failure"
                    break
                progress['value'] = 100
                button['state'] = 'normal'
                return_size = temp_size
                popup.update()
                status.set("Updating Set List")
                self._update_set_table(list_box, sets)
                self._reset_draft(True)
                self.draft.log_suspend(True)
                self._update_overlay_callback(True)
                self.draft.log_suspend(False)
                status.set("Download Complete")
            except Exception as error:
                result = False
                result_string = error

            break

        if not result:
            status.set("Download Failed")
            popup.update()
            button['state'] = 'normal'
            message_string = f"Download Failed: {result_string}"
            message_box = tkinter.messagebox.showwarning(
                title="Error", message=message_string)
        else:
            self.configuration.database_size = return_size
            CL.write_config(self.configuration)
        popup.update()
        return

    def _update_set_table(self, list_box, sets):
        '''Updates the set list in the Set View table'''
        # Delete the content of the list box
        for row in list_box.get_children():
            list_box.delete(row)
        self.root.update()
        file_list = FE.retrieve_local_set_list(sets)

        if file_list:
            list_box.config(height=min(len(file_list), 10))
        else:
            list_box.config(height=0)

        # Sort list by end date
        file_list.sort(key=lambda x: x[3], reverse=True)

        for count, file in enumerate(file_list):
            row_tag = identify_table_row_tag(False, "", count)
            list_box.insert("", index=count, iid=count,
                            values=file, tag=(row_tag,))

    def _process_table_click(self, event, table, card_list, selected_color):
        '''Creates the card tooltip when a table row is clicked'''
        color_dict = {}
        for item in table.selection():
            card_name = table.item(item, "value")[0]
            for card in card_list:
                card_name = card_name if card_name[0] != '*' else card_name[1:]
                if card_name == card[constants.DATA_FIELD_NAME]:
                    try:
                        for color in selected_color:
                            color_dict[color] = {
                                x: "NA" for x in constants.DATA_FIELDS_LIST}
                            for k in color_dict[color]:
                                if k in card[constants.DATA_FIELD_DECK_COLORS][color]:
                                    if k in constants.WIN_RATE_FIELDS_DICT:
                                        winrate_count = constants.WIN_RATE_FIELDS_DICT[k]
                                        color_dict[color][k] = CL.calculate_win_rate(card[constants.DATA_FIELD_DECK_COLORS][color][k],
                                                                                     card[constants.DATA_FIELD_DECK_COLORS][color][winrate_count],
                                                                                     self.configuration.bayesian_average_enabled)
                                    else:
                                        color_dict[color][k] = card[constants.DATA_FIELD_DECK_COLORS][color][k]

                        CreateCardToolTip(table,
                                          event,
                                          card[constants.DATA_FIELD_NAME],
                                          color_dict,
                                          card[constants.DATA_SECTION_IMAGES],
                                          self.configuration.images_enabled,
                                          self.scale_factor,
                                          self.fonts_dict)
                    except Exception as error:
                        overlay_logger.info(
                            "__process_table_click Error: %s", error)
                    break

    def _open_draft_log(self):
        '''Reads and processes a stored draft log when File->Open is selected'''
        filename = filedialog.askopenfilename(filetypes=(("Log Files", "*.log"),
                                                         ("All files", "*.*")))

        if filename:
            self.arena_file = filename
            self._reset_draft(True)
            self.draft.set_arena_file(filename)
            self.draft.log_suspend(True)
            self._update_overlay_callback(True)
            self.draft.log_suspend(False)

    def _control_trace(self, enabled):
        '''Enable/Disable all of the overlay widget traces. This function is used when the application needs
           to modify a widget value without triggering a callback
        '''
        try:
            trace_list = [
                (self.column_2_selection, lambda: self.column_2_selection.trace(
                    "w", self._update_settings_callback)),
                (self.column_3_selection, lambda: self.column_3_selection.trace(
                    "w", self._update_settings_callback)),
                (self.column_4_selection, lambda: self.column_4_selection.trace(
                    "w", self._update_settings_callback)),
                (self.column_5_selection, lambda: self.column_5_selection.trace(
                    "w", self._update_settings_callback)),
                (self.column_6_selection, lambda: self.column_6_selection.trace(
                    "w", self._update_settings_callback)),
                (self.column_7_selection, lambda: self.column_7_selection.trace(
                    "w", self._update_settings_callback)),
                (self.deck_stats_checkbox_value, lambda: self.deck_stats_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.missing_cards_checkbox_value, lambda: self.missing_cards_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.auto_highest_checkbox_value, lambda: self.auto_highest_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.curve_bonus_checkbox_value, lambda: self.curve_bonus_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.color_bonus_checkbox_value, lambda: self.color_bonus_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.bayesian_average_checkbox_value, lambda: self.bayesian_average_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.data_source_selection, lambda: self.data_source_selection.trace(
                    "w", self._update_source_callback)),
                (self.stat_options_selection, lambda: self.stat_options_selection.trace(
                    "w", self._update_deck_stats_callback)),
                (self.draft_log_checkbox_value, lambda: self.draft_log_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.filter_format_selection, lambda: self.filter_format_selection.trace(
                    "w", self._update_source_callback)),
                (self.result_format_selection, lambda: self.result_format_selection.trace(
                    "w", self._update_source_callback)),
                (self.deck_filter_selection, lambda: self.deck_filter_selection.trace(
                    "w", self._update_source_callback)),
                (self.taken_alsa_checkbox_value, lambda: self.taken_alsa_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_ata_checkbox_value, lambda: self.taken_ata_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_gpwr_checkbox_value, lambda: self.taken_gpwr_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_ohwr_checkbox_value, lambda: self.taken_ohwr_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_gdwr_checkbox_value, lambda: self.taken_gdwr_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_gndwr_checkbox_value, lambda: self.taken_gndwr_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_iwd_checkbox_value, lambda: self.taken_iwd_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_filter_selection, lambda: self.taken_filter_selection.trace(
                    "w", self._update_settings_callback)),
                (self.taken_type_selection, lambda: self.taken_type_selection.trace(
                    "w", self._update_settings_callback)),
                (self.card_colors_checkbox_value, lambda: self.card_colors_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.color_identity_checkbox_value, lambda: self.color_identity_checkbox_value.trace(
                    "w", self._update_settings_callback)),
                (self.taken_type_creature_checkbox_value, lambda: self.taken_type_creature_checkbox_value.trace(
                    "w", self._update_taken_table)),
                (self.taken_type_land_checkbox_value, lambda: self.taken_type_land_checkbox_value.trace(
                    "w", self._update_taken_table)),
                (self.taken_type_instant_sorcery_checkbox_value, lambda: self.taken_type_instant_sorcery_checkbox_value.trace(
                    "w", self._update_taken_table)),
                (self.taken_type_other_checkbox_value, lambda: self.taken_type_other_checkbox_value.trace(
                    "w", self._update_taken_table)),
            ]

            if enabled:
                if not self.trace_ids:
                    for trace_tuple in trace_list:
                        self.trace_ids.append(trace_tuple[1]())
            elif self.trace_ids:
                for count, trace_tuple in enumerate(trace_list):
                    trace_tuple[0].trace_vdelete("w", self.trace_ids[count])
                self.trace_ids = []
        except Exception as error:
            overlay_logger.info("__control_trace Error: %s", error)

    def _reset_draft(self, full_reset):
        '''Clear all of the stored draft data (i.e., draft type, draft set, collected cards, etc.)'''
        self.draft.clear_draft(full_reset)

    def _update_overlay_build(self):
        '''Checks the version.txt file in Github to determine if a new version of the application is available'''
        # Version Check
        update_flag = True

        new_version_found, new_version = check_version(
            self.extractor, self.version)

        try:
            if new_version_found:
                if sys.platform == constants.PLATFORM_ID_WINDOWS:
                    import win32api
                    message_string = f"Update client {self.version} to version {new_version}?"
                    message_box = tkinter.messagebox.askyesno(
                        title="Update", message=message_string)
                    if message_box:
                        if self.extractor.retrieve_repository_file("setup.exe"):
                            update_flag = False
                            self.root.destroy()
                            win32api.ShellExecute(
                                0, "open", "setup.exe", None, None, 10)
                        else:
                            message_box = tkinter.messagebox.showerror(
                                title="Download Failed", message="Visit https://github.com/bstaple1/MTGA_Draft_17Lands/releases to manually download the new version.")

                else:
                    message_string = f"Update {new_version} is now available.\n Check https://github.com/bstaple1/MTGA_Draft_17Lands/releases for more details."
                    message_box = tkinter.messagebox.showinfo(
                        title="Update", message=message_string)
        except Exception as error:
            overlay_logger.info("_update_overlay_build Error: %s", error)

        if update_flag:
            self._arena_log_check()
            self._control_trace(True)

    def _enable_deck_stats_table(self, enable):
        '''Hide/Display the Deck Stats table based on the application settings'''
        try:
            if enable:
                self.stat_frame.grid(
                    row=10, column=0, columnspan=2, sticky='nsew')
                self.stat_table.grid(
                    row=11, column=0, columnspan=2, sticky='nsew')
            else:
                self.stat_frame.grid_remove()
                self.stat_table.grid_remove()
        except Exception:
            self.stat_frame.grid(row=10, column=0, columnspan=2, sticky='nsew')
            self.stat_table.grid(row=11, column=0, columnspan=2, sticky='nsew')

    def _enable_missing_cards_table(self, enable):
        '''Hide/Display the Missing Cards table based on the application settings'''
        try:
            if enable:
                self.missing_frame.grid(
                    row=8, column=0, columnspan=2, sticky='nsew')
                self.missing_table_frame.grid(row=9, column=0, columnspan=2)
            else:
                self.missing_frame.grid_remove()
                self.missing_table_frame.grid_remove()
        except Exception:
            self.missing_frame.grid(
                row=8, column=0, columnspan=2, sticky='nsew')
            self.missing_table_frame.grid(row=9, column=0, columnspan=2)


class CreateCardToolTip(ScaledWindow):
    '''Class that's used to create the card tooltip that appears when a table row is clicked'''

    def __init__(self, widget, event, card_name, color_dict, image, images_enabled, scale_factor, fonts_dict):
        super().__init__()
        self.scale_factor = scale_factor
        self.fonts_dict = fonts_dict
        self.waittime = 1  # miliseconds
        self.wraplength = 180  # pixels
        self.widget = widget
        self.card_name = card_name
        self.color_dict = color_dict
        self.image = image
        self.images_enabled = images_enabled
        self.widget.bind("<Leave>", self._leave)
        self.widget.bind("<ButtonPress>", self._leave)
        self.id = None
        self.tw = None
        self.event = event
        self.images = []
        self._enter()

    def _enter(self, event=None):
        '''Initiate creation of the tooltip widget'''
        self._schedule()

    def _leave(self, event=None):
        '''Remove tooltip when the user hovers over the tooltip or clicks elsewhere'''
        self._unschedule()
        self._hide_tooltip()

    def _schedule(self):
        '''Creates the tooltip window widget and stores the id'''
        self._unschedule()
        self.id = self.widget.after(self.waittime, self._display_tooltip)

    def _unschedule(self):
        '''Clear the stored widget data when the closing the tooltip'''
        widget_id = self.id
        self.id = None
        if widget_id:
            self.widget.after_cancel(widget_id)

    def _display_tooltip(self, event=None):
        '''Function that builds and populates the tooltip window '''
        try:
            row_height = self._scale_value(23)
            tt_width = self._scale_value(500)
            # creates a toplevel window
            self.tw = tkinter.Toplevel(self.widget)
            # Leaves only the label and removes the app window
            self.tw.wm_overrideredirect(True)
            if sys.platform == constants.PLATFORM_ID_OSX:
                self.tw.wm_overrideredirect(False)

            tt_frame = tkinter.Frame(self.tw, borderwidth=5, relief="solid")

            tkinter.Grid.rowconfigure(tt_frame, 2, weight=1)

            card_label = Label(tt_frame,
                               text=self.card_name,
                               style="TooltipHeader.TLabel",
                               background="#3d3d3d",
                               foreground="#e6ecec",
                               relief="groove",
                               anchor="c",)

            note_label = Label(tt_frame,
                               text="Win rate fields with fewer than 200 samples are listed as 0% or NA.",
                               style="Notes.TLabel",
                               background="#3d3d3d",
                               foreground="#e6ecec",
                               anchor="c",)

            if len(self.color_dict) == 2:
                headers = {"Label": {"width": .70, "anchor": tkinter.W},
                           "Value1": {"width": .15, "anchor": tkinter.CENTER},
                           "Value2": {"width": .15, "anchor": tkinter.CENTER}}
                width = self._scale_value(400)
                tt_width += self._scale_value(125)
            else:
                headers = {"Label": {"width": .80, "anchor": tkinter.W},
                           "Value1": {"width": .20, "anchor": tkinter.CENTER}}
                width = self._scale_value(340)

            style = Style()
            style.configure("Tooltip.Treeview", rowheight=row_height)

            stats_main_table = self._create_header("tooltip_table",
                                                   tt_frame, 0, self.fonts_dict["All.TableRow"], headers, width, False, True, "Tooltip.Treeview", False)
            main_field_list = []

            values = ["Filter:"] + list(self.color_dict.keys())
            main_field_list.append(tuple(values))

            values = ["Average Taken At:"] + \
                [f"{x[constants.DATA_FIELD_ATA]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Average Last Seen At:"] + \
                [f"{x[constants.DATA_FIELD_ALSA]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Improvement When Drawn:"] + \
                [f"{x[constants.DATA_FIELD_IWD]}pp" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Games In Hand Win Rate:"] + \
                [f"{x[constants.DATA_FIELD_GIHWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Opening Hand Win Rate:"] + \
                [f"{x[constants.DATA_FIELD_OHWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Games Played Win Rate:"] + \
                [f"{x[constants.DATA_FIELD_GPWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Games Drawn Win Rate:"] + \
                [f"{x[constants.DATA_FIELD_GDWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Games Not Seen Win Rate:"] + \
                [f"{x[constants.DATA_FIELD_GNSWR]}%" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            main_field_list.append(tuple(["", ""]))

            values = ["Number of Games In Hand:"] + \
                [f"{x[constants.DATA_FIELD_GIH]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Number of Games in Opening Hand:"] + \
                [f"{x[constants.DATA_FIELD_NGOH]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Number of Games Played:"] + \
                [f"{x[constants.DATA_FIELD_NGP]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Number of Games Drawn:"] + \
                [f"{x[constants.DATA_FIELD_NGD]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            values = ["Number of Games Not Seen:"] + \
                [f"{x[constants.DATA_FIELD_NGND]}" for x in self.color_dict.values()]
            main_field_list.append(tuple(values))

            for x in range(2):
                main_field_list.append(tuple(["", ""]))

            stats_main_table.config(height=len(main_field_list))

            column_offset = 0
            # Add scryfall image
            if self.images_enabled:
                image_size_y = len(main_field_list) * row_height
                size = self._scale_value(280), image_size_y
                self.images = []
                request_header = {'User-Agent': 'Mozilla/5.0'}
                for count, picture_url in enumerate(self.image):
                    try:
                        if picture_url:
                            image_request = urllib.request.Request(
                                url=picture_url, headers=request_header)
                            raw_data = urllib.request.urlopen(
                                image_request).read()
                            im = Image.open(io.BytesIO(raw_data))
                            im.thumbnail(size, Image.ANTIALIAS)
                            image = ImageTk.PhotoImage(im)
                            image_label = Label(tt_frame, image=image)
                            image_label.grid(
                                column=count, row=1, columnspan=1)
                            self.images.append(image)
                            column_offset += 1
                            tt_width += self._scale_value(200)
                    except Exception as error:
                        overlay_logger.info(
                            "_display_tooltip Image Error: %s", error)

            card_label.grid(column=0, row=0,
                            columnspan=column_offset + 2, sticky=tkinter.NSEW)

            note_label.grid(column=0, row=2,
                            columnspan=column_offset + 2, sticky=tkinter.NSEW)

            for count, row_values in enumerate(main_field_list):
                row_tag = identify_table_row_tag(False, "", count)
                stats_main_table.insert(
                    "", index=count, iid=count, values=row_values, tag=(row_tag,))

            stats_main_table.grid(
                row=1, column=column_offset, sticky=tkinter.NSEW)

            location_x, location_y = identify_safe_coordinates(self.tw,
                                                               self._scale_value(
                                                                   tt_width),
                                                               self._scale_value(
                                                                   450),
                                                               self._scale_value(
                                                                   25),
                                                               self._scale_value(20))
            self.tw.wm_geometry(f"+{location_x}+{location_y}")

            tt_frame.pack()

            self.tw.attributes("-topmost", True)
        except Exception as error:
            overlay_logger.info("__display_tooltip Error: %s", error)

    def _hide_tooltip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
