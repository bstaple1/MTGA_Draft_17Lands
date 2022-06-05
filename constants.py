import os
import getpass
# Global Constants
## The different types of draft.

LOG_TYPE_DEBUG = "mtgaTool"
LOG_TYPE_DRAFT = "draftLog"

BASIC_LANDS = ["Island","Mountain","Swamp","Plains","Forest"]

LIMITED_TYPE_UNKNOWN            = 0
LIMITED_TYPE_DRAFT_PREMIER_V1   = 1
LIMITED_TYPE_DRAFT_PREMIER_V2   = 2
LIMITED_TYPE_DRAFT_QUICK        = 3
LIMITED_TYPE_DRAFT_TRADITIONAL  = 4
LIMITED_TYPE_SEALED             = 5
LIMITED_TYPE_SEALED_TRADITIONAL = 6

NON_COLORS_OPTIONS = ["Auto", "All GIHWR", "All IWD", "All ALSA"]
DECK_COLORS = ["All Decks","W","U","B","R","G","WU","WB","WR","WG","UB","UR","UG","BR","BG","RG","WUB","WUR","WUG","WBR","WBG","WRG","UBR","UBG","URG","BRG"]
DECK_FILTERS = NON_COLORS_OPTIONS + DECK_COLORS

DRAFT_LOG_FOLDER = os.path.join(os.getcwd(), "Logs")

TIER_FILE_PREFIX = "Tier_"

DRAFT_DETECTION_CATCH_ALL = ["Draft", "draft"]

DRAFT_START_STRING = "[UnityCrossThreadLogger]==> Event_Join "

DATA_SOURCES_NONE = {"None" : ""}

FILTER_FORMAT_NAMES = "Names"
FILTER_FORMAT_COLORS = "Colors"
FILTER_FORMAT_SET_NAMES = "Set Names"

FILTER_FORMAT_LIST = [FILTER_FORMAT_COLORS, FILTER_FORMAT_NAMES]

LOCAL_DATA_FOLDER_PATH_WINDOWS = os.path.join("Wizards of the Coast","MTGA","MTGA_Data")
LOCAL_DATA_FOLDER_PATH_OSX = os.path.join("Library","Application Support","com.wizards.mtga")

LOCAL_DOWNLOADS_DATA = os.path.join("Downloads","Raw")

LOCAL_DATA_FILE_PREFIX_CARDS = "Raw_cards_"
LOCAL_DATA_FILE_PREFIX_DATABASE = "Raw_CardDatabase_"

LOCAL_DATABASE_TABLE_LOCALIZATION = "Localizations"
LOCAL_DATABASE_TABLE_ENUMERATOR = "Enums"

LOCAL_DATABASE_LOCALIZATION_COLUMN_ID = "LocId"
LOCAL_DATABASE_LOCALIZATION_COLUMN_FORMAT = "Formatted"
LOCAL_DATABASE_LOCALIZATION_COLUMN_TEXT = "enUS"

LOCAL_DATABASE_ENUMERATOR_COLUMN_ID = "LocId"
LOCAL_DATABASE_ENUMERATOR_COLUMN_TYPE = "Type"
LOCAL_DATABASE_ENUMERATOR_COLUMN_VALUE = "Value"

LOCAL_DATABASE_ENUMERATOR_TYPE_COLOR = "Color"
LOCAL_DATABASE_ENUMERATOR_TYPE_CARD_TYPES = "CardType"

LOCAL_DATABASE_LOCALIZATION_QUERY = f"""SELECT 
                                            A.{LOCAL_DATABASE_LOCALIZATION_COLUMN_ID}, 
                                            A.{LOCAL_DATABASE_LOCALIZATION_COLUMN_FORMAT}, 
                                            A.{LOCAL_DATABASE_LOCALIZATION_COLUMN_TEXT}
                                        FROM {LOCAL_DATABASE_TABLE_LOCALIZATION} A INNER JOIN(
                                            SELECT 
                                                {LOCAL_DATABASE_LOCALIZATION_COLUMN_ID},
                                                min({LOCAL_DATABASE_LOCALIZATION_COLUMN_FORMAT}) AS MIN_FORMAT 
                                            FROM {LOCAL_DATABASE_TABLE_LOCALIZATION} 
                                            GROUP BY {LOCAL_DATABASE_LOCALIZATION_COLUMN_ID}) 
                                        B ON A.{LOCAL_DATABASE_LOCALIZATION_COLUMN_ID} = B.{LOCAL_DATABASE_LOCALIZATION_COLUMN_ID} 
                                        AND A.{LOCAL_DATABASE_LOCALIZATION_COLUMN_FORMAT} = B.MIN_FORMAT"""
                                        
LOCAL_DATABASE_ENUMERATOR_QUERY = f"""SELECT
                                        {LOCAL_DATABASE_ENUMERATOR_COLUMN_ID},
                                        {LOCAL_DATABASE_ENUMERATOR_COLUMN_TYPE},
                                        {LOCAL_DATABASE_ENUMERATOR_COLUMN_VALUE}
                                      FROM {LOCAL_DATABASE_TABLE_ENUMERATOR}
                                      WHERE {LOCAL_DATABASE_ENUMERATOR_COLUMN_TYPE} 
                                      IN ('{LOCAL_DATABASE_ENUMERATOR_TYPE_COLOR}', 
                                          '{LOCAL_DATABASE_ENUMERATOR_TYPE_CARD_TYPES}')"""

SETS_FOLDER = os.path.join(os.getcwd(), "Sets")
SET_FILE_SUFFIX = "Data.json"

CARD_RATINGS_BACKOFF_DELAY_SECONDS = 30
CARD_RATINGS_INTER_DELAY_SECONDS = 2

PLATFORM_ID_OSX = "darwin"
PLATFORM_ID_WINDOWS = "win32"

LOG_LOCATION_WINDOWS = os.path.join('Users', getpass.getuser(), "AppData", "LocalLow","Wizards Of The Coast","MTGA","Player.log")
LOG_LOCATION_OSX = os.path.join("Library","Logs","Wizards of the Coast","MTGA","Player.log")

DEFAULT_GIHWR_AVERAGE = 0.0

WINDOWS_DRIVES = ["C:/","D:/","E:/","F:/"]
WINDOWS_PROGRAM_FILES = ["Program Files","Program Files (x86)"]


SET_TYPE_EXPANSION = "expansion"
SET_TYPE_ALCHEMY = "alchemy"

SET_LIST_ARENA = "arena"
SET_LIST_SCRYFALL = "scryfall"
SET_LIST_17LANDS = "17Lands"

SUPPORTED_SET_TYPES = [SET_TYPE_EXPANSION, SET_TYPE_ALCHEMY]

DEBUG_LOG_FOLDER = os.path.join(os.getcwd(), "Debug")
DEBUG_LOG_FILE = os.path.join(DEBUG_LOG_FOLDER, "debug.log")

#Dictionaries
## Used to identify the limited type based on log string
LIMITED_TYPES_DICT = {
    "PremierDraft"     : LIMITED_TYPE_DRAFT_PREMIER_V1,
    "QuickDraft"       : LIMITED_TYPE_DRAFT_QUICK,
    "TradDraft"        : LIMITED_TYPE_DRAFT_TRADITIONAL,
    "BotDraft"         : LIMITED_TYPE_DRAFT_QUICK,
    "Sealed"           : LIMITED_TYPE_SEALED,
    "TradSealed"       : LIMITED_TYPE_SEALED_TRADITIONAL,
}

COLOR_NAMES_DICT = {
    "W"   : "White",
    "U"   : "Blue",
    "B"   : "Black",
    "R"   : "Red",
    "G"   : "Green",
    "WU"  : "Azorius",
    "UB"  : "Dimir",
    "BR"  : "Rakdos",
    "RG"  : "Gruul",
    "WG"  : "Selesnya",
    "WB"  : "Orzhov",
    "BG"  : "Golgari",
    "UG"  : "Simic",
    "UR"  : "Izzet",
    "WR"  : "Boros",
    "WUR" : "Jeskai",
    "UBG" : "Sultai",
    "WBR" : "Mardu",
    "URG" : "Temur",
    "WBG" : "Abzan",
    "WUB" : "Esper",
    "UBR" : "Grixis",
    "BRG" : "Jund",
    "WRG" : "Naya",
    "WUG" : "Bant",
}

CARD_COLORS_DICT = {
    "White" : "W",
    "Black" : "B",
    "Blue"  : "U",
    "Red"   : "R",
    "Green" : "G",
}

PLATFORM_LOG_DICT = {
    PLATFORM_ID_OSX     : LOG_LOCATION_OSX,
    PLATFORM_ID_WINDOWS : LOG_LOCATION_WINDOWS,
}