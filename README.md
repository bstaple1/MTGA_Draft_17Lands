# MTGA_Draft_17Lands
Magic: The Gathering Arena draft tool that utilizes 17Lands data.

![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Premier.png?raw=true)

## Steps for Windows

- Step 1: Download and unzip the MTGA_Draft_17Lands-main.zip file, clone the repository, or download the executable from the releases page.

- Step 2: In Arena, go to Adjust Options, Account, and then check the Detailed Logs (Plugin Support) check box.

- Step 3: Double-click setup.exe to start the install. 

    - Note: The application must be installed to the main drive (C drive).

- Step 4: Go to the installed folder and right-click the exectuable (.exe), click properties, compatibility tab, and check Run this program as an administrator.

- Step 5: Double-click the MTGA_Draft_Tool.exe to start the program.

- Step 6: Download the sets that you plan on using (Data->View Sets).

- Step 7: Start the draft in Arena.

## Steps for Mac
- Step 1: Download and unzip the MTGA_Draft_17Lands-main.zip file or clone the repository.

- Step 2: In Arena, go to Adjust Options, Account, and then check the Detailed Logs (Plugin Support) check box.

- Step 3: Download and install the latest version of python 3 from this location: https://www.python.org/downloads/macos/.

- Step 4: Install the python package installer Pip by opening the Mac terminal and entering "python3.10 -m ensurepip --upgrade".

- Step 5: Install the python image library Pillow by opening the Mac terminal and entering "python3.10 -m pip install --upgrade Pillow".

- Step 6: Install the python input monitoring library Pynput by opening the Mac terminal and entering "python3.10 -m pip install --upgrade pynput".

- Step 7: Install web certificates by going to "/Applications/Python 3.10/" and double-clicking the file "Install Certificates.command".

- Step 8: Open the config.json file in a text editor and change the "hotkey_enabled" field from "true" to "false".

- Step 9: Decrease the table width by setting the "table_width" field to 220 in the config.json file.

- Step 10: Install the python widget library by opening the Mac terminal and entering "python3.10 -m pip install --upgrade ttkwidgets".

- Step 11: Start the application by opening the Mac terminal and entering "python3.10 main.py --os=MAC".

- Step 12: Set Arena to window mode.

- Step 13: Download the sets that you plan on using (Data->View Sets).

- Step 14: Start the draft in Arena.

## UI Features

- Current Draft: Lists the current draft type (Premier, Quick, or Traditional) that the application has identified.

    - The application has been tested with Premier, Quick, and Traditional drafts.
    - In the Arena logs, P1P1 doesn't appear for Premier and Traditional drafts until after P1P2.

- Data Source: Lists the current draft type (Premier, Quick, or Traditional) from which the application is pulling the card data.

    - The application will attempt to pull data for the current draft type and set (e.g. data from NEO_PremierDraft_Data.json for a Premier Draft). If the user hasn't downloaded the data file for the current draft type and set, then the application will attempt to use a different data file from the same set (e.g. NEO_QuickDraft_Data.json if NEO_PremierDraft_Data.json isn't available).
    - This field will display "None" if the application is unable to find a valid data file for the current draft type and set.
  
- Deck Filter: A drop-down that lists all of the available deck color permutations that you can use to filter the deck card ratings.

    - The percentage next to the number represents the win rate for that color combination. These percentage values are collected from the color ratings page on 17Lands. If there are no values, then that means the sample size was too small to determine the win rate (unpopular deck combination).
    - The "All Decks" option lists the combined rating across all of the deck color combinations
        -The "Auto" option will keep the filter at "All Decks" for the first 15 picks and then switch over to the filter that best matches your taken cards. See the auto averaging note in the card logic section.
- Pack, Pick Table: This table lists the cards contained in the current pack. 

    - The "All" column lists the card rating for the "All Decks" filter.
        - The last column will list the card rating for the chosen Deck Filter option.
        - The card rating is derived from the Games in Hand Win Rate, Average Last Seen At, and Improvement When Drawn fields from 17Lands. The individual values can be seen by clicking on the card in the table.
        - For Premier and Traditional drafts, P1P1 doesn't appear in the logs until after P1P2. Use the Card Compare feature to perform the card analysis.
	
- Missing Cards Table: This table will list the cards missing from a pack that has already been seen. 

    - The user's chosen card will have an asterisk next to the name.
	
- Deck Stats Table: This table lists the card distribution and total for creatures, noncreatures, and all cards.

    - The numbered columns represent the cost of the card (cmc).

## Menu Features

![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Draft_Menus.png?raw=true)

- Read Draft Logs: Read the log file from a draft by selecting File->Open. Select a file that has the following naming scheme DraftLog_<Set>_<Draft Type>_<Timestamp>.log file to read the file.

- Download Set Data: Get to the Add Sets window by selecting Data->View Sets. Enter the set information and click on the ADD SET button to begin downloading the set data.

    - For the ID field, keep the value at 0.
    - The download can take several minutes.
    
- List Taken Cards: Get to the Taken Cards window by selecting Cards->Taken Cards. 
    - This table lists the cards that were taken by the user over the course of the draft.

- List Suggested Decks: Get to the Suggested Decks window by selecting Cards->Suggested Decks. 
    - This table lists a 40 card deck that the application has built from your taken cards. You might see multiple decks if the application is able to build them.
    - The application might be unable to build any decks if this option is selected before the draft is over or if too few creatures were taken.
        - The application builds the decks based on a number of requirements including the Games in Hand Win Rate of the individual cards. The rating listed is the combined Games in Hand Win Rate of all the cards in the deck.

- Card Compare: Get to the Card Compare window by selecting Cards->Compare Cards. This window will allow you to compare cards that you've entered in.
    - This feature can be used to quickly compare cards for P1P1 of the Premier and Traditional drafts.
	
![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Card_Compare.png?raw=true)
    
## Additional Features

- Hotkey: The user can use the hotkey ctrl+g to toggle between minimizing and maximizing the main application window.

    - This feature doesn't work on Mac.
    - You need to run the executable as an administrator for this feature to work in Arena.

- Top-Level Window: The main application window, and subsequent windows, will act as an overlay and remain above all other windows, including the Arena screen.

- Tier List: A tier list can be added to the drop-downs by following the instructions in /Tools/TierScraper17Lands/README.txt.

- Tooltips: Clicking on any field that lists a card will display a tooltip the contains the following information: Card image, Average Last Seen At, Improvement When Drawn, and Games in Hand Win Rate.
	
![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Tooltip.png?raw=true)	
	
## Settings

- Column 2: Configure column 2 of the pack table, missing table, compare table, and taken table. Any filter can be used.

- Column 3: Configure column 3 of the pack table, missing table, compare table, and taken table. Any filter can be used.

- Column 4: Configure column 2 of the pack table, missing table, compare table, and taken table. Any filter can be used. This configures the same column as the deck filter drop-down in the main window.

- Hide Deck Stats: Hides the deck stats table and drop-down in the main window.

- Hide Missing Cards: Hides the missing cards table in the main window.

- Disable Highest Rated: Disables the highest rated card logic for the "Auto" filter configuration for column 4. See the auto highest rating note in the card logic section.

- Disable Curve Bonus: Disables the curve bonus logic for the "Auto" filter configuration for column 4. See the curve bonus note in the card logic section.

- Disable Color Bonus: Disables the color bonus logic for the "Auto" and "All Decks" filter configurations for column 4. See the color bonus note in the card logic section

## Card Logic:

- Auto Highest Rating: If the "Auto" filter is set, then the tool will attempt to identify the user's deck (using two-color pairs) after 16 cards have been picked. If the tool is unable to identify a definitive leading color pair, then it will display the highest pick rating of the top two color pairs. The column header will display both color pairs separated by a slash.
    - Example: If the user has taken primarily black, blue, and green cards, and Generous Visitor has a BG rating of 3.5 and a UB rating of 0, then the displayed pick rating will be 3.5.

- Curve Bonus: If column 4 is set to a specific color filter, or the "Auto" filter is used, then the tool will add a curve bonus if certain conditions aren't met.
    - Curve Bonus Conditions:
        - If the identified, or configured, color pair has fewer than 13 creatures, then the tool will add a curve bonus ranging from 0.1 - 1.0.
        - If the identified, or configured, color pair has fewer than 4 2-drops, 3 3-drops, 2 4-drops, and 1 5-drop, then it will add a curve bonus ranging from 0.1 - 0.5 to cards that fit the distribution.
        - If the identified, or configured, color pair identifies a card in a pack that could potentially replace a taken card (due to higher GIHWR or lower CMC), then it will add a curve bonus ranging from 0.1 - 0.25.
        
- Color Bonus: If column 4 is set to "All Decks", or "Auto" with fewer than 16 cards, then the tool will add a color bonus based on the top 3 colors identified from the taken cards.
    - Color Bonus Factors:
        - The tool will add a color bonus of 0.3 for each taken card that has a GIHWR equal to or above 65%
        - The tool will add a color bonus of 0.2 for each taken card that has a GIHWR between 64.9% and 60%.
        - The tool will add a color bonus of 0.1 for each taken card that has a GIHWR between 59.9% and 52%.
        - For colorless cards, the tool will divide the highest color bonus by 2.
        
- Deck Suggester: For each viable color combination, the deck suggester will construct multiple decks (Aggro, Mid, and Control decks), using some generic deck building requirements, from a card pool of the highest win rate cards. The suggester will rate each deck and choose the highest rated deck for each viable color combination. The deck suggester will NOT identify card synergies and build a deck that's intentionally synergistic. 
    - Deck Building Requirements:
        - Aggro Deck:
            - The deck must have a minimum of 13 creatures and should have no less than 17 creatures.
            - The deck should have at least 2 1-drops, 5 2-drops, 3 3-drops.
            - The average CMC of all of the creatures must be 2.40 or less.
            - The deck has 16 lands.
        - Mid Deck:
            - The deck must have a minimum of 13 creatures and should have no less than 15 creatures.
            - The deck should have at least 4 2-drops, 3 3-drops, 2 4-drops, and 1 5-drop.
            - The average CMC of all of the creatures must be 3.04 or less.
            - The deck has 17 lands.
        - Control Deck:
            - The deck must have a minimum of 13 creatures and should have no less than 14 creatures.
            - The deck should have at least 3 2-drops, 3 3-drops, 3 4-drops, 1 5-drop, and 1 6-drop.
            - The average CMC of all of the creatures must be 3.68 or less.      
            - The deck has 18 lands.
    - Notes:
        - The CMC average and land requirements were derived from this article: https://strategy.channelfireball.com/all-strategy/mtg/channelmagic-articles/how-many-lands-do-you-need-to-consistently-hit-your-land-drops/
        - The deck distribution and CMC requirements can result in the inclusion of some poor performing cards.
            Example: If the user has a pool of white and blue cards, and the only 3-drops are Acquisition Octopus (53.7% for WU) and Guardians of Oboro (50.7% for WU), then the suggester will include those two cards to fulfill the 3-drop requirement (3 Aggro/3 Mid/3 Control).
        - The rating consists of the combined GIHWR of all of the cards minus penalties for not adhering to the deck requirements.
        - The NEO creature sagas count as creatures.

