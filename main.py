#!/usr/bin/env python3
"""! @brief Magic the Gathering draft application that utilizes 17Lands data"""

# Imports
import argparse
import overlay as OL

__version__ = 3.02


def startup():
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--file')
    parser.add_argument('-d', '--data')
    parser.add_argument('--step', action='store_true')

    args = parser.parse_args()

    overlay = OL.Overlay(__version__, args)

    overlay.main_loop()


def main():
    startup()


if __name__ == "__main__":
    main()
