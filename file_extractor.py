"""This module contains the functions and classes that are used for building the set files and communicating with platforms"""
from enum import Enum
from urllib.parse import quote as urlencode
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


if not os.path.exists(constants.SETS_FOLDER):
    os.makedirs(constants.SETS_FOLDER)

if not os.path.exists(constants.TIER_FOLDER):
    os.makedirs(constants.TIER_FOLDER)

if not os.path.exists(constants.TEMP_FOLDER):
    os.makedirs(constants.TEMP_FOLDER)

file_logger = logging.getLogger(constants.LOG_TYPE_DEBUG)


class Result(Enum):
    '''Enumeration class for file integrity results'''
    VALID = 0
    ERROR_MISSING_FILE = 1
    ERROR_UNREADABLE_FILE = 2


def decode_mana_cost(encoded_cost):
    '''Parse the raw card mana_cost field and return the cards cmc and color identity list'''
    decoded_cost = ""
    cmc = 0
    if len(encoded_cost):
        cost_string = re.sub('\(|\)', '', encoded_cost)

        sections = cost_string[1:].split("o")
        index = 0
        for count, section in enumerate(sections):
            if section.isnumeric() and count != 0:
                break
            else:
                index += 1
                cmc += int(section) if section.isnumeric() else 1

        decoded_cost = "".join(f"{{{x}}}" for x in sections[0:index])

    return decoded_cost, cmc


def retrieve_local_set_list(sets):
    '''Scans the Sets folder and returns a list of valid set files'''
    file_list = []
    main_sets = [v[constants.SET_LIST_17LANDS][0] for k, v in sets.items()]
    for file in os.listdir(constants.SETS_FOLDER):
        try:
            name_segments = file.split("_")
            if len(name_segments) == 3:

                if ((name_segments[0].upper() in main_sets) and
                    (name_segments[1] in constants.LIMITED_TYPES_DICT) and
                        (name_segments[2] == constants.SET_FILE_SUFFIX)):

                    set_name = list(sets.keys())[list(
                        main_sets).index(name_segments[0].upper())]
                    result, json_data = check_file_integrity(
                        os.path.join(constants.SETS_FOLDER, file))
                    if result == Result.VALID:
                        if json_data["meta"]["version"] == 1:
                            start_date, end_date = json_data["meta"]["date_range"].split(
                                "->")
                        else:
                            start_date = json_data["meta"]["start_date"]
                            end_date = json_data["meta"]["end_date"]
                        file_list.append(
                            (set_name, name_segments[1], start_date, end_date))
        except Exception as error:
            file_logger.info("retrieve_local_set_list Error: %s", error)

    return file_list


def retrieve_arena_log_location():
    '''Searches local directories for the location of the Arena Player.log file'''
    log_location = ""
    try:
        if sys.platform == constants.PLATFORM_ID_OSX:
            paths = [os.path.join(os.path.expanduser(
                '~'), constants.LOG_LOCATION_OSX)]
        else:
            path_list = [constants.WINDOWS_DRIVES,
                         [constants.LOG_LOCATION_WINDOWS]]
            paths = [os.path.join(*x) for x in itertools.product(*path_list)]

        for file_path in paths:
            file_logger.info("Arena Log: Searching file path %s", file_path)
            if os.path.exists(file_path):
                log_location = file_path
                break

    except Exception as error:
        file_logger.info("retrieve_arena_log_location Error: %s", error)
    return log_location


def retrieve_arena_directory(log_location):
    '''Searches the Player.log file for the Arena install location (windows only)'''
    arena_directory = ""
    try:
        # Retrieve the arena directory
        with open(log_location, 'r', encoding="utf-8", errors="replace") as log_file:
            line = log_file.readline()
            location = re.findall(r"'(.*?)/Managed'", line, re.DOTALL)
            if location and os.path.exists(location[0]):
                arena_directory = location[0]

    except Exception as error:
        file_logger.info("retrieve_arena_directory Error: %s", error)
    return arena_directory


def search_local_files(paths, file_prefixes):
    '''Generic function that's used for searching local directories for a file'''
    file_locations = []
    for file_path in paths:
        try:
            if os.path.exists(file_path):
                for prefix in file_prefixes:
                    files = [filename for filename in os.listdir(
                        file_path) if filename.startswith(prefix)]

                    for file in files:
                        file_location = os.path.join(file_path, file)
                        file_locations.append(file_location)

        except Exception as error:
            file_logger.info("search_local_files Error: %s", error)

    return file_locations


def extract_types(type_line):
    '''Parses a type string and returns a list of card types'''
    types = []
    if constants.CARD_TYPE_CREATURE in type_line:
        types.append(constants.CARD_TYPE_CREATURE)

    if constants.CARD_TYPE_PLANESWALKER in type_line:
        types.append(constants.CARD_TYPE_PLANESWALKER)

    if constants.CARD_TYPE_LAND in type_line:
        types.append(constants.CARD_TYPE_LAND)

    if constants.CARD_TYPE_INSTANT in type_line:
        types.append(constants.CARD_TYPE_INSTANT)

    if constants.CARD_TYPE_SORCERY in type_line:
        types.append(constants.CARD_TYPE_SORCERY)

    if constants.CARD_TYPE_ENCHANTMENT in type_line:
        types.append(constants.CARD_TYPE_ENCHANTMENT)

    if constants.CARD_TYPE_ARTIFACT in type_line:
        types.append(constants.CARD_TYPE_ARTIFACT)

    return types


def check_date(date):
    '''Checks a date string and returns false if the date is in the future'''
    result = True
    try:
        parts = date.split("-")
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = 0

        if datetime.datetime(year=year, month=month, day=day, hour=hour) > datetime.datetime.now():
            result = False

    except Exception:
        result = False
    return result


def shift_date(start_date, shifted_days, string_format):
    '''Shifts a date by a certain number of days'''
    shifted_date_string = ""
    shifted_date = datetime.date.min
    try:
        shifted_date = start_date + datetime.timedelta(days=shifted_days)
        if string_format is not None:
            shifted_date_string = shifted_date.strftime(string_format)
    except Exception as error:
        file_logger.info("shift_date Error: %s", error)

    return shifted_date, shifted_date_string


def check_release_date(release_string, shifted_days):
    '''Checks a shifted release data and returns false if the data is in the future'''
    result = True
    try:
        release_date = datetime.datetime.strptime(
            release_string, "%Y-%m-%d").date()
        shifted_release_date = shift_date(release_date, shifted_days, None)[0]
        today = datetime.date.today()

        if shifted_release_date > today:
            result = False

    except Exception as error:
        file_logger.info("check_release_date Error: %s", error)

    return result


def check_file_integrity(filename):
    '''Extracts data from a file to determine if it's formatted correctly'''
    result = Result.VALID
    json_data = {}
    while True:
        # Check 1) File is present
        try:
            with open(filename, 'r', encoding="utf-8", errors="replace") as json_file:
                json_data = json_file.read()
        except Exception:
            result = Result.ERROR_MISSING_FILE
            break

        # Check 2) File contains required elements
        try:
            json_data = json.loads(json_data)

            # Check 2A) Meta data is present
            version = json_data["meta"]["version"]
            if version == 1:
                json_data["meta"]["date_range"].split("->")
            else:
                json_data["meta"]["start_date"]
                json_data["meta"]["end_date"]

            # Check 2B) Card data is present
            cards = json_data["card_ratings"]
            for card in cards:
                cards[card][constants.DATA_FIELD_NAME]
                cards[card][constants.DATA_FIELD_COLORS]
                cards[card][constants.DATA_FIELD_CMC]
                cards[card][constants.DATA_FIELD_TYPES]
                cards[card]["mana_cost"]
                cards[card][constants.DATA_SECTION_IMAGES]
                cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIHWR]
                cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_ALSA]
                cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_IWD]
                break

            if len(cards.keys()) < 100:
                result = Result.ERROR_UNREADABLE_FILE
                break

        except Exception:
            result = Result.ERROR_UNREADABLE_FILE
            break
        break
    return result, json_data


class FileExtractor:
    '''Class that handles the creation of set files and the retrieval of platform information'''

    def __init__(self, directory):
        self.selected_sets = []
        self.set_list = []
        self.draft = ""
        self.session = ""
        self.start_date = ""
        self.end_date = ""
        self.directory = directory
        self.context = ssl.SSLContext()
        self.card_ratings = {}
        self.combined_data = {
            "meta": {"collection_date": str(datetime.datetime.now())}}
        self.card_dict = {}
        self.deck_colors = constants.DECK_COLORS

    def clear_data(self):
        '''Clear stored set information'''
        self.combined_data = {
            "meta": {"collection_date": str(datetime.datetime.now())}}
        self.card_dict = {}
        self.card_ratings = {}

    def select_sets(self, sets):
        '''Public function that's used for setting class variables'''
        self.selected_sets = sets

    def return_set_list(self):
        '''Public function that's used for setting class variables'''
        if not self.set_list:
            self.set_list = self.retrieve_set_list()

        return self.set_list

    def set_draft_type(self, draft_type):
        '''Public function that's used for setting class variables'''
        self.draft = draft_type

    def set_start_date(self, start_date):
        '''Sets the start data in a set file'''
        result = False
        if check_date(start_date):
            result = True
            self.start_date = start_date
            self.combined_data["meta"]["start_date"] = self.start_date
        return result

    def set_end_date(self, end_date):
        '''Sets the end date in a set file'''
        result = False
        if check_date(end_date):
            result = True
            self.end_date = end_date
            self.combined_data["meta"]["end_date"] = self.end_date
        return result

    def set_version(self, version):
        '''Sets the version in a set file'''
        self.combined_data["meta"]["version"] = version

    def download_card_data(self, ui_root, progress_bar, status, database_size):
        '''Wrapper function for starting the set file download/creation process'''
        result = False
        result_string = ""
        temp_size = 0
        try:
            result, result_string, temp_size = self._download_expansion(
                ui_root, progress_bar, status, database_size)

        except Exception as error:
            file_logger.info("download_card_data Error: %s", error)
            result_string = error

        return result, result_string, temp_size

    def _download_expansion(self, ui_root, progress_bar, status, database_size):
        ''' Function that performs the following steps:
            1. Build a card data file from local Arena files (stored as temp_card_data.json in the Temp folder)
               - The card sets contains the Arena IDs, card name, mana cost, colors, etc.
            1A. Collect the card data from Scryfall if it's unavailable locally (fallback)
            2. Collect the card_ratings data from scryfall
            3. Build a set file by combining the card data and the card ratings
        '''
        result = False
        result_string = ""
        temp_size = 0
        try:
            while True:
                progress_bar['value'] = 5
                ui_root.update()

                result, result_string, temp_size = self._retrieve_local_arena_data(
                    ui_root, status, database_size)

                if not result:

                    result, result_string = self.retrieve_scryfall_data(
                        ui_root, status)
                    if not result:
                        break

                progress_bar['value'] = 10
                status.set("Collecting 17Lands Data")
                ui_root.update()

                if not self.retrieve_17lands_data(self.selected_sets[constants.SET_LIST_17LANDS],
                                                  self.deck_colors,
                                                  ui_root,
                                                  progress_bar,
                                                  progress_bar['value'],
                                                  status):
                    result = False
                    result_string = "Couldn't Collect 17Lands Data"
                    break

                matching_only = True if constants.SET_SELECTION_ALL in self.selected_sets[
                    constants.SET_LIST_ARENA] else False

                if not matching_only:
                    self._initialize_17lands_data()

                status.set("Building Data Set File")
                ui_root.update()
                self._assemble_set(matching_only)
                break

        except Exception as error:
            file_logger.info("_download_expansion Error: %s", error)
            result_string = error

        return result, result_string, temp_size

    def _retrieve_local_arena_data(self, root, status, previous_database_size):
        '''Builds a card data file from raw Arena files'''
        result_string = "Couldn't Collect Local Card Data"
        result = False
        self.card_dict = {}
        database_size = 0
        status.set("Searching Local Files")
        root.update()
        if sys.platform == constants.PLATFORM_ID_OSX:
            directory = os.path.join(os.path.expanduser('~'),
                                     constants.LOCAL_DATA_FOLDER_PATH_OSX) if not self.directory else self.directory
            paths = [os.path.join(directory, constants.LOCAL_DOWNLOADS_DATA)]
        else:
            if not self.directory:
                path_list = [constants.WINDOWS_DRIVES, constants.WINDOWS_PROGRAM_FILES, [
                    constants.LOCAL_DATA_FOLDER_PATH_WINDOWS]]
                paths = [os.path.join(*x)
                         for x in itertools.product(*path_list)]
            else:
                paths = [os.path.join(
                    self.directory, constants.LOCAL_DOWNLOADS_DATA)]

        arena_cards_locations = search_local_files(
            paths, [constants.LOCAL_DATA_FILE_PREFIX_CARDS])
        arena_database_locations = search_local_files(
            paths, [constants.LOCAL_DATA_FILE_PREFIX_DATABASE])

        while True:
            try:
                if (not arena_cards_locations) or (not arena_database_locations):
                    break

                current_database_size = os.path.getsize(
                    arena_cards_locations[0])

                if current_database_size != previous_database_size:
                    file_logger.info(
                        "Local File Change Detected %d, %d",
                        current_database_size, previous_database_size)
                    file_logger.info(
                        "Local Database Data: Searching file path %s",
                        arena_database_locations[0])
                    status.set("Retrieving Localization Data")
                    root.update()
                    result, card_text, card_enumerators = self._retrieve_local_database(
                        arena_database_locations[0])

                    if not result:
                        break

                    file_logger.info(
                        "Local Card Data: Searching file path %s",
                        arena_cards_locations[0])
                    status.set("Retrieving Raw Card Data")
                    root.update()
                    result, raw_card_data = self._retrieve_local_cards(
                        arena_cards_locations[0])

                    if not result:
                        break

                    status.set("Building Temporary Card Data File")
                    root.update()
                    result = self._assemble_stored_data(
                        card_text, card_enumerators, raw_card_data)

                    if not result:
                        break

                # Assemble information for local data set
                status.set("Retrieving Temporary Card Data")
                root.update()
                result = self._retrieve_stored_data(
                    self.selected_sets[constants.SET_LIST_ARENA])

                database_size = current_database_size

            except Exception as error:
                file_logger.info("_retrieve_local_arena_data Error: %s", error)
            break

        if not result:
            file_logger.info(result_string)

        return result, result_string, database_size

    def _retrieve_local_cards(self, file_location):
        '''Function that retrieves pertinent card data from raw Arena files'''
        result = False
        card_data = {}
        try:
            with open(file_location, 'r', encoding="utf-8", errors="replace") as json_file:
                json_data = json.loads(json_file.read())

                for card in json_data:
                    # Making all of the keys lowercase
                    card = {k.lower(): v for k, v in card.items()}
                    try:
                        card_set = card[constants.LOCAL_CARDS_KEY_SET]

                        if ((constants.LOCAL_CARDS_KEY_DIGITAL_RELEASE_SET in card) and
                           (re.findall("^[yY]\d{2}$", card_set, re.DOTALL))):
                            card_set = card[constants.LOCAL_CARDS_KEY_DIGITAL_RELEASE_SET]

                        if card_set not in card_data:
                            card_data[card_set] = {}

                        if constants.LOCAL_CARDS_KEY_TOKEN in card:
                            continue

                        group_id = card[constants.LOCAL_CARDS_KEY_GROUP_ID]

                        if constants.LOCAL_CARDS_KEY_LINKED_FACES in card:
                            linked_id = int(
                                card[constants.LOCAL_CARDS_KEY_LINKED_FACES].split(',')[0])
                            if linked_id < group_id:
                                # The application will no longer list the names of all the card faces. This will address an issue with excessively long tooltips for specialize cards
                                # self.card_dict[card["linkedFaces"][0]][constants.DATA_FIELD_NAME].append(card["titleId"])
                                types = [int(x) for x in card[constants.LOCAL_CARDS_KEY_TYPES].split(
                                    ',')] if constants.LOCAL_CARDS_KEY_TYPES in card else []
                                card_data[card_set][linked_id][constants.LOCAL_CARDS_KEY_TYPES].extend(
                                    types)
                                continue

                        card_data[card_set][group_id] = {constants.DATA_FIELD_NAME: [
                            card[constants.LOCAL_CARDS_KEY_TITLE_ID]], constants.DATA_SECTION_IMAGES: []}
                        card_data[card_set][group_id][constants.DATA_FIELD_TYPES] = [int(
                            x) for x in card[constants.LOCAL_CARDS_KEY_TYPES].split(',')] if constants.LOCAL_CARDS_KEY_TYPES in card else []
                        card_data[card_set][group_id][constants.DATA_FIELD_COLORS] = [int(
                            x) for x in card[constants.LOCAL_CARDS_KEY_COLOR_ID].split(',')] if constants.LOCAL_CARDS_KEY_COLOR_ID in card else []
                        mana_cost, cmc = decode_mana_cost(
                            card[constants.LOCAL_CARDS_KEY_CASTING_COST]) if constants.LOCAL_CARDS_KEY_CASTING_COST in card else ("", 0)
                        card_data[card_set][group_id][constants.DATA_FIELD_CMC] = cmc
                        card_data[card_set][group_id]["mana_cost"] = mana_cost
                        card_data[card_set][group_id][constants.DATA_FIELD_RARITY] = constants.CARD_RARITY_DICT[card[constants.LOCAL_CARDS_KEY_RARITY]
                                                                                                                ] if constants.LOCAL_CARDS_KEY_RARITY in card else constants.CARD_RARITY_COMMON

                        result = True
                    except Exception as error:
                        file_logger.info(
                            "Card Read Error: %s, %s", error, card)
                        break
                        # pass
        except Exception as error:
            file_logger.info("_retrieve_local_cards Error: %s", error)

        return result, card_data

    def _retrieve_local_database(self, file_location):
        '''Retrieves localization and enumeration data from an Arena database'''
        result = False
        card_text = {}
        card_enumerators = {}
        try:
            # Open Sqlite3 database
            while True:
                connection = sqlite3.connect(file_location)
                connection.row_factory = sqlite3.Row
                cursor = connection.cursor()

                rows = [dict(row) for row in cursor.execute(
                    constants.LOCAL_DATABASE_LOCALIZATION_QUERY)]

                if not rows:
                    break

                result, card_text = self._retrieve_local_card_text(rows)

                if not result:
                    break

                rows = [dict(row) for row in cursor.execute(
                    constants.LOCAL_DATABASE_ENUMERATOR_QUERY)]

                if not rows:
                    break

                result, card_enumerators = self._retrieve_local_card_enumerators(
                    rows)

                if not result:
                    break

                break

        except Exception as error:
            result = False
            file_logger.info("_retrieve_local_database Error: %s", error)

        return result, card_text, card_enumerators

    def _retrieve_local_card_text(self, data):
        '''Returns a dict containing localization data'''
        result = True
        card_text = {}
        try:
            # Retrieve the title (card name) for each of the collected arena IDs
            card_text = {x[constants.LOCAL_DATABASE_LOCALIZATION_COLUMN_ID]: x[constants.LOCAL_DATABASE_LOCALIZATION_COLUMN_TEXT] for x in data}

        except Exception as error:
            result = False
            file_logger.info("_retrieve_local_card_text Error: %s", error)

        return result, card_text

    def _retrieve_local_card_enumerators(self, data):
        '''Returns a dict containing card enumeration data'''
        result = True
        card_enumerators = {constants.DATA_FIELD_COLORS: {},
                            constants.DATA_FIELD_TYPES: {}}
        try:
            for row in data:
                if row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_TYPE] == constants.LOCAL_DATABASE_ENUMERATOR_TYPE_CARD_TYPES:
                    card_enumerators[constants.DATA_FIELD_TYPES][row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_VALUE]
                                                                 ] = row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_ID]
                elif row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_TYPE] == constants.LOCAL_DATABASE_ENUMERATOR_TYPE_COLOR:
                    card_enumerators[constants.DATA_FIELD_COLORS][row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_VALUE]
                                                                  ] = row[constants.LOCAL_DATABASE_ENUMERATOR_COLUMN_ID]

        except Exception as error:
            result = False
            file_logger.info(
                "_retrieve_local_card_enumerators Error: %s", error)

        return result, card_enumerators

    def _assemble_stored_data(self, card_text, card_enumerators, card_data):
        '''Creates a temporary card data file from data collected from local Arena files'''
        result = False
        try:
            for card_set in card_data:
                for card in card_data[card_set]:
                    try:
                        card_data[card_set][card][constants.DATA_FIELD_NAME] = " // ".join(
                            card_text[x] for x in card_data[card_set][card][constants.DATA_FIELD_NAME])
                        card_data[card_set][card][constants.DATA_FIELD_TYPES] = list(set(
                            [card_text[card_enumerators[constants.DATA_FIELD_TYPES][x]] for x in card_data[card_set][card][constants.DATA_FIELD_TYPES]]))
                        card_data[card_set][card][constants.DATA_FIELD_COLORS] = [
                            constants.CARD_COLORS_DICT[card_text[card_enumerators[constants.DATA_FIELD_COLORS][x]]] for x in card_data[card_set][card][constants.DATA_FIELD_COLORS]]
                        if constants.CARD_TYPE_CREATURE in card_data[card_set][card][constants.DATA_FIELD_TYPES]:
                            index = card_data[card_set][card][constants.DATA_FIELD_TYPES].index(
                                constants.CARD_TYPE_CREATURE)
                            card_data[card_set][card][constants.DATA_FIELD_TYPES].insert(
                                0, card_data[card_set][card][constants.DATA_FIELD_TYPES].pop(index))
                        result = True
                    except Exception:
                        pass

            if result:
                # Store all of the processed card data
                with open(constants.TEMP_CARD_DATA_FILE, 'w', encoding="utf-8", errors="replace") as json_file:
                    json.dump(card_data, json_file)

        except Exception as error:
            result = False
            file_logger.info("_assemble_stored_data Error: %s", error)

        return result

    def _retrieve_stored_data(self, set_list):
        '''Retrieves card data from the temp_card_data.json file stored in the Temp folder'''
        result = False
        self.card_dict = {}
        try:
            with open(constants.TEMP_CARD_DATA_FILE, 'r', encoding="utf-8", errors="replace") as data:
                json_file = data.read()
                json_data = json.loads(json_file)

            if constants.SET_SELECTION_ALL in set_list:
                for card_data in json_data.values():
                    self.card_dict.update(card_data.copy())
            else:
                for search_set in set_list:
                    matching_sets = list(
                        filter(lambda x, ss=search_set: ss in x, json_data))
                    for match in matching_sets:
                        self.card_dict.update(json_data[match].copy())

            if len(self.card_dict):
                result = True

        except Exception as error:
            result = False
            file_logger.info("_retrieve_stored_data Error: %s", error)

        return result

    def retrieve_repository_version(self):
        '''Read the version.txt file in Github to determine the latest application version'''
        version = ""
        try:
            url = "https://raw.github.com/bstaple1/MTGA_Draft_17Lands/master/version.txt"
            url_data = urllib.request.urlopen(url, context=self.context).read()

            version = self._process_repository_version(url_data)

        except Exception as error:
            file_logger.info("retrieve_repository_version Error: %s", error)
        return version

    def retrieve_repository_file(self, filename):
        '''Download a file from Github'''
        result = True
        try:
            url = f"https://raw.github.com/bstaple1/MTGA_Draft_17Lands/master/{filename}"
            url_data = urllib.request.urlopen(url, context=self.context).read()

            with open(filename, 'wb', encoding="utf-8", errors="replace") as file:
                file.write(url_data)
        except Exception as error:
            file_logger.info("retrieve_repository_file Error: %s", error)
            result = False
        return result

    def retrieve_scryfall_data(self, root, status):
        '''Use the Scryfall API to retrieve the set data needed for building a card set file*
           - This is a fallback feature feature that's used in case there's an issue with the local Arena files
        '''
        result = False
        self.card_dict = {}
        result_string = "Couldn't Retrieve Card Data"
        url = ""
        for card_set in self.selected_sets[constants.SET_LIST_SCRYFALL]:
            if set == "dbl":
                continue
            retry = constants.SCRYFALL_REQUEST_ATTEMPT_MAX
            while retry:
                try:
                    status.set("Collecting Scryfall Data")
                    root.update()
                    # https://api.scryfall.com/cards/search?order=set&unique=prints&q=e%3AMID
                    url = "https://api.scryfall.com/cards/search?order=set&unique=prints&q=e" + \
                        urlencode(':', safe='') + f"{card_set}"
                    url_data = urllib.request.urlopen(
                        url, context=self.context).read()

                    set_json_data = json.loads(url_data)

                    result, result_string = self._process_scryfall_data(
                        set_json_data["data"])

                    while set_json_data["has_more"] and result:
                        url = set_json_data["next_page"]
                        url_data = urllib.request.urlopen(
                            url, context=self.context).read()
                        set_json_data = json.loads(url_data)
                        result, result_string = self._process_scryfall_data(
                            set_json_data["data"])

                    if result:
                        break

                except Exception as error:
                    file_logger.info(url)
                    file_logger.info("retrieve_scryfall_data Error: %s", error)

                if not result:
                    retry -= 1

                    if retry:
                        attempt_count = constants.CARD_RATINGS_ATTEMPT_MAX - retry
                        status.set(
                            f"""Collecting Scryfall Data - Request Failed ({attempt_count}/{constants.SCRYFALL_REQUEST_ATTEMPT_MAX}) - Retry in {constants.SCRYFALL_REQUEST_BACKOFF_DELAY_SECONDS} seconds""")
                        root.update()
                        time.sleep(
                            constants.SCRYFALL_REQUEST_BACKOFF_DELAY_SECONDS)
        return result, result_string

    def _initialize_17lands_data(self):
        '''Initialize the 17Lands data by setting the fields to 0 in case there are gaps in the downloaded card data'''
        for data in self.card_dict.values():
            data[constants.DATA_FIELD_DECK_COLORS] = {}
            for color in self.deck_colors:
                data[constants.DATA_FIELD_DECK_COLORS][color] = {
                    x: 0.0 for x in constants.DATA_FIELD_17LANDS_DICT if x != constants.DATA_SECTION_IMAGES}

    def retrieve_17lands_data(self, sets, deck_colors, root, progress, initial_progress, status):
        '''Use the 17Lands endpoint to download the card ratings data for all of the deck filter options'''
        self.card_ratings = {}
        current_progress = 0
        result = False
        url = ""
        for set_code in sets:
            if set_code == "dbl":
                continue
            for color in deck_colors:
                retry = constants.CARD_RATINGS_ATTEMPT_MAX
                result = False
                while retry:

                    try:
                        status.set(f"Collecting {color} 17Lands Data")
                        root.update()
                        url = f"https://www.17lands.com/card_ratings/data?expansion={set_code}&format={self.draft}&start_date={self.start_date}&end_date={self.end_date}"

                        if color != constants.FILTER_OPTION_ALL_DECKS:
                            url += "&colors=" + color
                        url_data = urllib.request.urlopen(
                            url, context=self.context).read()

                        set_json_data = json.loads(url_data)
                        self._process_17lands_data(color, set_json_data)
                        result = True
                        break
                    except Exception as error:
                        file_logger.info(url)
                        file_logger.info(
                            "retrieve_17lands_data Error: %s", error)
                        retry -= 1

                        if retry:
                            attempt_count = constants.CARD_RATINGS_ATTEMPT_MAX - retry
                            status.set(
                                f"""Collecting {color} 17Lands Data - Request Failed ({attempt_count}/{constants.CARD_RATINGS_ATTEMPT_MAX}) - Retry in {constants.CARD_RATINGS_BACKOFF_DELAY_SECONDS} seconds""")
                            root.update()
                            time.sleep(
                                constants.CARD_RATINGS_BACKOFF_DELAY_SECONDS)

                if result:
                    current_progress += (3 /
                                         len(self.selected_sets[constants.SET_LIST_17LANDS]))
                    progress['value'] = current_progress + initial_progress
                    root.update()
                else:
                    break
                time.sleep(constants.CARD_RATINGS_INTER_DELAY_SECONDS)
            if set == "stx":
                break

        return result

    def _assemble_set(self, matching_only):
        '''Combine the 17Lands ratings and the card data to form the complete set data'''
        self.combined_data["card_ratings"] = {}
        for card, card_data in self.card_dict.items():
            if self._process_card_data(card_data):
                self.combined_data["card_ratings"][card] = card_data
            elif not matching_only:
                self.combined_data["card_ratings"][card] = card_data

    def retrieve_set_list(self):
        '''Use the Scryfall set API to collect a list of Magic sets
           - The application only recognizes sets that it can collect using this API
           - The application will automatically support any new set that can be retrieved using this API
        '''
        sets = {}
        try:
            url = "https://api.scryfall.com/sets"
            url_data = urllib.request.urlopen(url, context=self.context).read()

            set_json_data = json.loads(url_data)
            sets = self._process_set_data(sets, set_json_data["data"])
            while set_json_data["has_more"]:
                url = set_json_data["next_page"]
                url_data = urllib.request.urlopen(
                    url, context=self.context).read()
                set_json_data = json.loads(url_data)
                sets = self._process_set_data(sets, set_json_data["data"])

        except Exception as error:
            file_logger.info("retrieve_set_list Error: %s", error)
        return sets

    def retrieve_17lands_color_ratings(self):
        '''Use 17Lands endpoint to collect the data from the color_ratings page'''
        try:
            # https://www.17lands.com/color_ratings/data?expansion=VOW&event_type=QuickDraft&start_date=2019-1-1&end_date=2022-01-13&combine_splash=true
            url = f"https://www.17lands.com/color_ratings/data?expansion={self.selected_sets[constants.SET_LIST_17LANDS][0]}&event_type={self.draft}&start_date={self.start_date}&end_date={self.end_date}&combine_splash=true"
            url_data = urllib.request.urlopen(url, context=self.context).read()

            color_json_data = json.loads(url_data)
            self._process_17lands_color_ratings(color_json_data)

        except Exception as error:
            file_logger.info(url)
            file_logger.info("retrieve_17lands_color_ratings Error: %s", error)

    def _process_17lands_data(self, colors, cards):
        '''Parse the 17Lands json data to extract the card ratings'''
        result = True

        for card in cards:
            try:
                card_data = {constants.DATA_SECTION_RATINGS: [],
                             constants.DATA_SECTION_IMAGES: []}
                color_data = {colors: {}}
                for key, value in constants.DATA_FIELD_17LANDS_DICT.items():
                    if key == constants.DATA_SECTION_IMAGES:
                        for field in value:
                            if field in card and len(card[field]):
                                image_url = f"{constants.URL_17LANDS}{card[field]}" if card[field].startswith(
                                    constants.IMAGE_17LANDS_SITE_PREFIX) else card[field]
                                card_data[constants.DATA_SECTION_IMAGES].append(
                                    image_url)
                    elif value in card:
                        if (key in constants.WIN_RATE_OPTIONS) or (key == constants.DATA_FIELD_IWD):
                            color_data[colors][key] = round(
                                float(card[value]) * 100.0, 2) if card[value] is not None else 0.0
                        elif ((key == constants.DATA_FIELD_ATA) or
                              (key == constants.DATA_FIELD_ALSA)):
                            color_data[colors][key] = round(
                                float(card[value]), 2)
                        else:
                            color_data[colors][key] = int(card[value])

                card_name = card[constants.DATA_FIELD_NAME]

                if card_name not in self.card_ratings:
                    self.card_ratings[card_name] = card_data

                self.card_ratings[card_name][constants.DATA_SECTION_RATINGS].append(
                    color_data)

            except Exception as error:
                result = False
                file_logger.info("_process_17lands_data Error: %s", error)

        return result

    def _process_17lands_color_ratings(self, colors):
        '''Parse the 17Lands json data to collect the color ratings'''
        color_ratings_dict = {
            "Mono-White": constants.CARD_COLOR_SYMBOL_WHITE,
            "Mono-Blue": constants.CARD_COLOR_SYMBOL_BLUE,
            "Mono-Black": constants.CARD_COLOR_SYMBOL_BLACK,
            "Mono-Red": constants.CARD_COLOR_SYMBOL_RED,
            "Mono-Green": constants.CARD_COLOR_SYMBOL_GREEN,
            "(WU)": "WU",
            "(UB)": "UB",
            "(BR)": "BR",
            "(RG)": "RG",
            "(GW)": "GW",
            "(WB)": "WB",
            "(BG)": "BG",
            "(GU)": "GU",
            "(UR)": "UR",
            "(RW)": "RW",
            "(WUR)": "WUR",
            "(UBG)": "UBG",
            "(BRW)": "BRW",
            "(RGU)": "RGU",
            "(GWB)": "GWB",
            "(WUB)": "WUB",
            "(UBR)": "UBR",
            "(BRG)": "BRG",
            "(RGW)": "RGW",
            "(GWU)": "GWU",
        }

        try:
            self.combined_data["color_ratings"] = {}
            for color in colors:
                games = color["games"]
                if not color["is_summary"] and (games > 5000):
                    color_name = color["color_name"]
                    winrate = round(
                        (float(color["wins"])/color["games"]) * 100, 1)

                    color_label = [
                        x for x in color_ratings_dict if x in color_name]

                    if color_label:

                        processed_colors = color_ratings_dict[color_label[0]]

                        if processed_colors not in self.combined_data["color_ratings"]:
                            self.combined_data["color_ratings"][processed_colors] = winrate

        except Exception as error:
            file_logger.info("_process_17lands_color_ratings Error: %s", error)

    def _process_scryfall_data(self, data):
        '''Parse json data from the Scryfall API to extract pertinent card data'''
        result = False
        result_string = "Scryfall Data Unavailable"
        for card_data in data:
            try:
                if "arena_id" not in card_data:
                    continue

                arena_id = card_data["arena_id"]

                self.card_dict[arena_id] = {
                    constants.DATA_FIELD_NAME: card_data[constants.DATA_FIELD_NAME],
                    constants.DATA_FIELD_CMC: card_data[constants.DATA_FIELD_CMC],
                    constants.DATA_FIELD_COLORS: card_data["color_identity"],
                    constants.DATA_FIELD_TYPES: extract_types(card_data["type_line"]),
                    "mana_cost": 0,
                    constants.DATA_SECTION_IMAGES: [],
                }

                if "card_faces" in card_data:
                    self.card_dict[arena_id]["mana_cost"] = card_data["card_faces"][0]["mana_cost"]
                    self.card_dict[arena_id][constants.DATA_SECTION_IMAGES].append(
                        card_data["card_faces"][0]["image_uris"]["normal"])
                    self.card_dict[arena_id][constants.DATA_SECTION_IMAGES].append(
                        card_data["card_faces"][1]["image_uris"]["normal"])

                else:
                    self.card_dict[arena_id]["mana_cost"] = card_data["mana_cost"]
                    self.card_dict[arena_id][constants.DATA_SECTION_IMAGES] = [
                        card_data["image_uris"]["normal"]]

                result = True

            except Exception as error:
                file_logger.info("_process_scryfall_data Error: %s", error)
                result_string = error

        return result, result_string

    def _process_card_data(self, card):
        '''Link the 17Lands card ratings with the card data'''
        result = False
        try:
            card_sides = card[constants.DATA_FIELD_NAME].split(" // ")
            card_sides = [x.replace("///", "//") for x in card_sides]
            matching_cards = [
                x for x in self.card_ratings if x in card_sides]
            if matching_cards:
                ratings_card_name = matching_cards[0]
                deck_colors = self.card_ratings[ratings_card_name][constants.DATA_SECTION_RATINGS]

                card[constants.DATA_SECTION_IMAGES] = self.card_ratings[ratings_card_name][constants.DATA_SECTION_IMAGES]
                card[constants.DATA_FIELD_DECK_COLORS] = {}
                for color in self.deck_colors:
                    card[constants.DATA_FIELD_DECK_COLORS][color] = {
                        x: 0.0 for x in constants.DATA_FIELD_17LANDS_DICT if x != constants.DATA_SECTION_IMAGES}
                result = True
                for deck_color in deck_colors:
                    for key, value in deck_color.items():
                        for field in value:
                            card[constants.DATA_FIELD_DECK_COLORS][key][field] = value[field]

        except Exception as error:
            file_logger.info("_process_card_data Error: %s", error)

        return result

    def _process_set_data(self, sets, data):
        '''Parse the Scryfall set list data to extract information for sets that are supported by Arena
           - Scryfall lists all Magic sets (paper and digital), so the application needs to filter out non-Arena sets
           - The application will only display sets that have been released
        '''
        counter = 0
        for card_set in data:
            try:
                # Check if the set has been released
                if "released_at" in card_set:
                    # Sets that are not digitial only are release in Arena 1 week before paper
                    start_offset = constants.SET_RELEASE_OFFSET_DAYS if not card_set[
                        "digital"] else 0
                    if not check_release_date(card_set["released_at"], start_offset):
                        continue

                set_name = card_set[constants.DATA_FIELD_NAME]
                set_code = card_set["code"]

                if set_code == "dbl":
                    sets[set_name] = {}
                    sets[set_name][constants.SET_LIST_ARENA] = ["VOW", "MID"]
                    sets[set_name][constants.SET_LIST_17LANDS] = [
                        set_code.upper()]
                    sets[set_name][constants.SET_LIST_SCRYFALL] = ["VOW", "MID"]
                    counter += 1
                elif card_set["set_type"] in constants.SUPPORTED_SET_TYPES:
                    if card_set["set_type"] == constants.SET_TYPE_ALCHEMY:
                        sets[set_name] = {}
                        if ("parent_set_code" in card_set) and ("block_code" in card_set):
                            sets[set_name][constants.SET_LIST_ARENA] = [
                                card_set["parent_set_code"].upper()]
                            sets[set_name][constants.SET_LIST_17LANDS] = [
                                f"{card_set['block_code'].upper()}{card_set['parent_set_code'].upper()}"]
                            sets[set_name][constants.SET_LIST_SCRYFALL] = [
                                set_code.upper(), card_set["parent_set_code"].upper()]
                        else:
                            sets[set_name] = {key: [set_code.upper()] for key in [
                                constants.SET_LIST_ARENA, constants.SET_LIST_SCRYFALL, constants.SET_LIST_17LANDS]}
                    elif (card_set["set_type"] == constants.SET_TYPE_MASTERS) and (not card_set["digital"]):
                        continue
                    else:
                        sets[set_name] = {key: [set_code.upper()] for key in [
                            constants.SET_LIST_ARENA, constants.SET_LIST_SCRYFALL, constants.SET_LIST_17LANDS]}
                        # Add mystic archives to strixhaven
                        if set_code == "stx":
                            sets[set_name][constants.SET_LIST_ARENA].append(
                                "STA")
                            sets[set_name][constants.SET_LIST_SCRYFALL].append(
                                "STA")
                    counter += 1

                # Only retrieve the last X sets + CUBE
                if counter >= constants.SET_LIST_COUNT_MAX:
                    break
            except Exception as error:
                file_logger.info("_process_set_data Error: %s", error)

        # Insert the cube sets
        sets["Arena Cube"] = {constants.SET_LIST_ARENA: [constants.SET_SELECTION_ALL], constants.SET_LIST_SCRYFALL: [
        ], constants.SET_LIST_17LANDS: [constants.SET_SELECTION_CUBE]}
        sets["Arena Cube"][constants.SET_START_DATE] = shift_date(
            datetime.date.today(), constants.SET_ARENA_CUBE_START_OFFSET_DAYS, "%Y-%m-%d")[1]

        return sets

    def _process_repository_version(self, data):
        '''Convert a version string to float'''
        version = round(float(data.decode("ascii")) * 100)

        return version

    def export_card_data(self):
        '''Build the file for the set data'''
        result = True
        try:
            output_file = "_".join(
                (self.selected_sets[constants.SET_LIST_17LANDS][0], self.draft, constants.SET_FILE_SUFFIX))
            location = os.path.join(constants.SETS_FOLDER, output_file)

            with open(location, 'w', encoding="utf-8", errors="replace") as file:
                json.dump(self.combined_data, file)

            # Verify that the file was written
            write_data = check_file_integrity(location)

            if write_data[0] != Result.VALID:
                result = False

        except Exception as error:
            file_logger.info("export_card_data Error: %s", error)
            result = False

        return result
