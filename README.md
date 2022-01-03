# MTGA_Draft_17Lands
Magic: The Gathering Arena draft tool that utilizes 17Lands data.

![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Premier.png?raw=true)

## Steps for Windows

- Step 1: In Arena, go to Adjust Options, Account, and then check the Detailed Logs (Plugin Support) check box

- Step 2: Double-click the Draft Tool executable (.exe) to start the application.

- Step 3: Start the draft in Arena.

## Steps for Mac

- Step 1: In Arena, go to Adjust Options, Account, and then check the Detailed Logs (Plugin Support) check box.

- Step 2: Download and install the latest version of python 3 from this location: https://www.python.org/downloads/macos/.

- Step 3: Install the python package installer Pip by opening the Mac terminal and entering "python3.10 -m ensurepip --upgrade".

- Step 4: Install the python image library Pillow by opening the Mac terminal and entering "python3.10 -m pip install --upgrade Pillow".

- Step 5: Install the python input monitoring library Pynput by opening the Mac terminal and entering "python3.10 -m pip install --upgrade pynput".

- Step 6: Install web certificates by going to "/Applications/Python 3.10/" and double-clicking the file "Install Certificates.command".

- Step 7: Open the config.json file in a text editor and change the "hotkey_enabled" field from "true" to "false".

- Step 8: Decrease the table width by setting the table_width field to 220 in the config.json file.

- Step 9: Start the application by opening the Mac terminal and entering "python3.10 main.py --os=MAC" without quotes.

- Step 10: Install the python widget library by opening the Mac terminal and entering "python3.10 -m pip install --upgrade ttkwidgets".

- Step 11: Set Arena to window mode.

- Step 12: Start the draft in Arena.

## UI Features

- Current Draft: Lists the current draft type (Premier, Quick, or Traditional) that the application has identified

    - The application has only ever been tested on Premier and Quick drafts. 
    - The Arena logs don't contain the pack data for pack 1, pick 1 for Premier drafts
  
- Deck Filter: A drop-down that lists all of the available deck color permutations that you can use to filter the deck card ratings.

    - The percentage next to the number represents the win rate for that color combination. These percentage values are collected from the color ratings page on 17 Lands. If there are no values, then that means the sample size was too small to determine the win rate (unpopular deck combination).
    - The "All Decks" option lists the combined rating across all of the deck color combinations
        -The "Auto" option will keep the filter at "All Decks" for the first 15 picks and then switch over to the filter that best matches your taken cards.
	
- Pack, Pick Table: This table lists the cards contained in the current pack. 

    - The "All" column lists the card rating for the "All Decks" filter. This is visible regardless of the Deck Filter option chosen.
        - The last column will list the card rating for the chosen Deck Filter option.
        - The card rating is derived from the Games in Hand Win Rate, Average Last Seen At, and Improvement When Drawn fields from 17 Lands. The individual values can be seen by clicking on the card in the table.
        - For Premier drafts, the pack 1, pick 1 card isn't available in the logs.
	
- Missing Cards Table: This table will list the cards missing from a pack that's already been seen. 

    - The user's chosen card will have an asterisk next to the name.
    - For premier drafts, the missing cards from pack 1, pick 1 will not be available.
	
- Deck Stats Table: This table lists the card distribution and total for creatures, noncreatures, and all cards.

    - The numbered columns represent the cost of the card (cmc).

## Menu Features

- Read Draft Logs: Read the log file from a draft by selecting File->Open. Select a .log file to read the file.

- Download Set Data: Get to the Add Sets window by selecting Data->View Sets. Enter the set information and click on the ADD SET button to begin downloading the set data.

    - For the ID field, keep the value at 0.
    - The download can take several minutes.
    - The firefox browser is required if the Color Ratings option is checked; you will see the application briefly open the "https://www.17lands.com/color_ratings" page while it collects the color ratings data
 
- List Taken Cards: Go to Taken Cards window by selecting Cards->Taken Cards. This table lists the cards that were taken by the user over the course of the draft.

- List Suggested Decks: Go to Suggested Decks window by selecting Cards->Suggested Decks. This table lists a 40 card deck that the application has built from your taken cards. You might see multiple decks if the application is able to build them.
 
    - The application might be unable to build any decks if this option is selected before the draft is over or if too few creatures were taken.
        - The application builds the decks based on a number of constraints including the Games in Hand Win Rate of the individual cards. The rating listed is the combined Games in Hand Win Rate of all the cards in the deck.
	
	
## Additional Features

- Hotkey: The user can use the hotkey ctrl+f to toggle between minimizing and maximizing the main application window.

    - This feature doesn't work on Mac.
    - You need to run the executable as an administrator for this feature to work in Arena.

- Top-Level Window: The main application window, and subsequent windows, will act as an overlay and remain above all other windows, including the Arena screen.

- Tooltips: Clicking on any field that lists a card will display a tooltip the contains the following information: Card image, Average Last Seen At, Improvement When Drawn, and Games in Hand Win Rate.

	
	
	








