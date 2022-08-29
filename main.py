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
import argparse
import sys
import overlay as OL

__version__ = 3.02


def Startup(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--file')
    parser.add_argument('-d', '--data')
    parser.add_argument('--step', action='store_true')

    args = parser.parse_args()

    overlay = OL.Overlay(__version__, args)

    overlay.MainLoop()


def main(argv):
    Startup(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
