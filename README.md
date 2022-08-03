# MTGA_Draft_17Lands
Magic: The Gathering Arena draft tool that utilizes 17Lands data.

**Latest Supported Set:** Alchemy Horizons: Baldur's Gate

**Supported Events:** Premier Draft\*, Traditional Draft\*, Quick Draft, Sealed, Traditional Sealed, and Special Events\*\*
  * \* For some events, the Arena logs don't list P1P1 until after P1P2. The _Card Compare_ feature can be used as a substitute for P1P1.
  * \*\* The application should support all special events that provide log entries (i.e., MWM, Qualifiers, etc.), although not all events have been tested.

![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Premier.png?raw=true)

## Run Steps: Windows Executable (Windows Only)
- **Step 1:** Download and unzip the `MTGA_Draft_17Lands-main.zip` file, clone the repository, or download the latest executable (e.g., `MTGA_Draft_Tool_V0285_Setup.exe`) from the releases page (https://github.com/bstaple1/MTGA_Draft_17Lands/releases).

- **Step 2:** In Arena, go to Adjust Options, Account, and then check the Detailed Logs (Plugin Support) check box.

- **Step 3:** Double-click `setup.exe` to start the installation. 
    - The MTGA_Draft_Tool_V####_Setup.exe and setup.exe files are the same.

- **Step 4:** (Optional) Go to the installed folder and right-click the executable (`MTGA_Draft_Tool.exe`), click properties, compatibility tab, and check Run this program as an administrator.
    - This step is only required if the application is installed in a directory with write restrictions (i.e., `Program Files` and `Program Files (x86)`).
    - This step isn't necessary if the application is installed in the main directory of a drive (i.e., `C:/` or `D:/`) or the `Users/<Username>/` directory

- **Step 5:** Double-click the `MTGA_Draft_Tool.exe` to start the program.

- **Step 6:** Download the sets that you plan on using (`Data->View Sets`).

- **Step 7:** Start the draft in Arena.


## Run Steps: Python (Windows/Mac)
- **Step 1:** Download and unzip the `MTGA_Draft_17Lands-main.zip` file or clone the repository.

- **Step 2:** In Arena, go to Adjust Options, Account, and then check the Detailed Logs (Plugin Support) check box.

- **Step 3:** Download and install the latest version of python 3.
    - Windows: https://www.python.org/downloads/windows/.
    - Mac: https://www.python.org/downloads/macos/.

- **Step 4:** Install the python package installer Pip by opening the terminal and entering ```python3.10 -m ensurepip --upgrade```.

- **Step 5:** Open the terminal and install the python libraries.
    - Windows: ```pip install -r requirements.txt```
    - Mac: ```pip install -r requirements_mac.txt```

- **Step 6:** (Mac Only) Install web certificates by going to `/Applications/Python 3.10/` and double-clicking the file `Install Certificates.command`.

- **Step 7:** Start the application by opening the terminal and entering ```python3.10 main.py```.

- **Step 8:** (Mac Only) Set Arena to window mode.

- **Step 9:** Download the sets that you plan on using (`Data->View Sets`).

- **Step 10:** Start the draft in Arena.

## Build Steps: setup.exe (Windows Only)
- **Step 1:** Download and install the latest version of python 3.

- **Step 2:** Install the python package installer Pip by opening the terminal and entering ```python3.10 -m ensurepip --upgrade```.

- **Step 3:** Open the terminal and enter ```pip install -r requirements.txt```.

- **Step 4:** Download Inno Setup from https://jrsoftware.org/isdl.php#stable

- **Step 5:** Build MTGA_Draft_Tool.exe by opening the terminal and entering ```pyinstaller main.py --onefile --noconsole -n MTGA_Draft_Tool```
    - Move the `MTGA_Draft_Tool.exe` file from the `dist` folder to the main `MTGA_Draft_17Lands` folder.
    
- **Step 6:** Open `Installer.iss` in Inno Setup and click Build->Compile.
    - In the `{app}` folder, rename the mysetup.exe file to `setup.exe` and move the file to the main `MTGA_Draft_17Lands` folder.

## UI Features

- **Current Draft:** Lists the current draft type (i.e., Premier, Quick, or Traditional) that the application has identified.
    - The application has been tested with Premier, Quick, and Traditional drafts.
    - In the Arena logs, P1P1 doesn't appear for Premier and Traditional drafts until after P1P2.

- **Data Source:** Lists the current draft type (i.e., Premier, Quick, or Traditional) from which the application is pulling the card data.
    - The application will attempt to pull data for the current draft type and set (e.g., data from NEO_PremierDraft_Data.json for a Premier Draft). If the user hasn't downloaded the data file for the current draft type and set, then the application will attempt to use a different data file from the same set (e.g., NEO_QuickDraft_Data.json if NEO_PremierDraft_Data.json isn't available).
    - This field will display "None" if the application is unable to find a valid data file for the current draft type and set.
  
- **Deck Filter:** A drop-down that lists all of the available deck color permutations that you can use to filter the deck card ratings.
    - The percentage next to the number represents the win rate for that color combination. These percentage values are collected from the color rating page on 17Lands. If there are no values, then that means the sample size was too small to determine the win rate (unpopular deck combination).
    - The "All Decks" option lists the combined rating across all of the deck color combinations
        -The "Auto" option will keep the filter at "All Decks" for the first 15 picks and then switch over to the filter that best matches your taken cards. See the auto averaging note in the card logic section.
- **Pack, Pick Table:** This table lists the cards contained in the current pack. 
    - The "All" column lists the card rating for the "All Decks" filter.
        - The last column will list the card rating for the chosen Deck Filter option.
        - The card rating is derived from the Games in Hand Win Rate, Average Last Seen At, and Improvement When Drawn fields from 17Lands. The individual values can be seen by clicking on the card in the table.
        - For Premier and Traditional drafts, P1P1 doesn't appear in the logs until after P1P2. Use the Card Compare feature to perform the card analysis.
	
- **Missing Cards Table:** This table will list the cards missing from a pack that has already been seen. 
    - The user's chosen card will have an asterisk next to the name.
	
- **Deck Stats Table:** This table lists the card distribution and total for creatures, noncreatures, and all cards.
    - The numbered columns represent the cost of the card (cmc).

## Menu Features

![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Draft_Menus.png?raw=true)

- **Read Draft Logs:** Read the log file from a draft by selecting `File->Open`. Select a file that has the following naming scheme `DraftLog_<Set>_<Draft Type>_<Timestamp>.log` file to read the file.

- **Download Set Data:** Get to the Add Sets window by selecting `Data->View Sets`. Enter the set information and click on the ADD SET button to begin downloading the set data.
    - The download can take several minutes.
    
- **List Taken Cards:** Get to the Taken Cards window by selecting `Cards->Taken Cards`. 
    - This table lists the cards that were taken by the user throughout the draft.

- **List Suggested Decks:** Get to the Suggested Decks window by selecting `Cards->Suggest Decks`. 
    - This table lists a 40-card deck that the application has built from your taken cards. You might see multiple decks if the application can build them.
    - The application might be unable to build any decks if this option is selected before the draft is over or if too few creatures were taken.
        - The application builds the decks based on several requirements including the Games in Hand Win Rate of the individual cards. The rating listed is the combined Games in Hand Win Rate of all the cards in the deck.

- **Card Compare:** Get to the Card Compare window by selecting `Cards->Compare Cards`. This window will allow you to compare cards that you've entered in.
    - This feature can be used to quickly compare cards for P1P1 of the Premier and Traditional drafts.
	
![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Card_Compare.png?raw=true)
    
## Additional Features

- **Hotkey:** The user can use the hotkey `CTRL+G` to toggle between minimizing and maximizing the main application window.
    - This feature doesn't work on Mac.
    - You need to run the executable as an administrator for this feature to work in Arena.

- **Top-Level Window:** The main application window, and subsequent windows, will act as an overlay and remain above all other windows, including the Arena screen.

- **Tier List:** A tier list can be added to the drop-downs by following the instructions in `./Tools/TierScraper17Lands/README.txt`.

- **Card Tooltips:** Clicking on any field that lists a card will display a tooltip that contains the following information: Card image, Average Last Seen At, Improvement When Drawn, and Games in Hand Win Rate.
	
![alt text](https://github.com/bstaple1/MTGA_Draft_17Lands/blob/main/Images/Tooltip.png?raw=true)	
	
## Settings

- **Column 2:** Configure column 2 of the pack table, missing table, compare table, and taken table. Any filter can be used.

- **Column 3:** Configure column 3 of the pack table, missing table, compare table, and taken table. Any filter can be used.

- **Column 4:** Configure column 4 of the pack table, missing table, compare table, and taken table. Any filter can be used. This configures the same column as the deck filter drop-down in the main window.

- **Deck Filter Format:** Used to switch the Deck Filter, Column 2, Column 3, and Column 4 values to either the color permutations (i.e., UB, BG, WUG, etc.) or the guild/shard/clan names (i.e., Dimir, Golgari, Bant, etc.)

- **Enable Deck Stats:** Displays the deck stats table and drop-down in the main window.

- **Enable Missing Cards:** Displays the missing cards table in the main window.

- **Enable Highest Rated:** Enables the highest rated card logic for the `Auto` filter configuration for column 4. See the auto highest rating note in the card logic section.

- **Enable Curve Bonus:** Enables the curve bonus logic for the `Auto` filter configuration for column 4. See the curve bonus note in the card logic section.

- **Enable Color Bonus:** Enables the color bonus logic for the `Auto` and `All Decks` filter configurations for column 4. See the color bonus note in the card logic section.

- **Enable Bayesian Average:** Enables the bayesian average logic for the card ratings. See the Bayesian average note in the card logic section.

- **Enable Draft Log:** Records the draft in a log file within the `./Logs` folder.

## Card Logic:

- **Card Ratings:** The application will identify the upper and lower GIHWR values of all of the set cards across all of the filters and perform the following calculation to determine a card's rating: ((card_gihwr - lower_gihwr) / (upper_gihwr - lower_gihwr)) * 5.0
    - Example: If the highest winrate of the set is 75.67% (Lae'zel, Githyanki Warrior (WR)) and the lowest winrate of the set is 41.73% (Ambitious Dragonborn (URG)), then the All Decks rating for The Hourglass Coven (71.97%) will be 4.5 (((71.97 - 41.73) / (75.67 - 41.73)) * 5.0 = 4.5)
    - If the color and curve bonuses are enabled, then the application will add those bonuses to the card rating

- **Bayesian Average:** A Bayesian average calculation applied to the Games In Hand Win Rate data based on some assumptions (expected range of 40-60% with a mean of 50%). 
    - Enabled: The application will perform this calculation on the GIHWR data. The adjustment made by this calculation will disappear as the Number of Games In Hand reaches 200.
    - Disabled: The application will not perform this calculation. If the Number of Games In Hand is fewer than 200, then the application will set the GIHWR to 0 (same as the 17Lands Card Ratings table).

- **Auto Highest Rating:** If the `Auto` filter is set, then the application will attempt to identify the user's deck (using two-color pairs) after 16 cards have been picked. If the tool is unable to identify a definitive leading color pair, then it will display the highest pick rating of the top two color pairs. The column header will display both color pairs separated by a slash.
    - Example: If the user has taken primarily black, blue, and green cards, and Generous Visitor has a BG rating of 3.5 and a UB rating of 0, then the displayed pick rating will be 3.5.

- **Curve Bonus:** If column 4 is set to a specific color filter, or the `Auto` filter is used, then the application will add a curve bonus if certain conditions are met.
    - Curve Bonus Conditions:
        - If the identified, or configured, color pair has fewer than 13 creatures, then the application will add a curve bonus ranging from 0.1 - 1.0.
        - If the identified, or configured, color pair has fewer than 4 2-drops, 3 3-drops, 2 4-drops, and 1 5-drop, then it will add a curve bonus ranging from 0.1 - 0.5 to cards that fit the distribution.
        - If the identified, or configured, color pair identifies a card in a pack that could potentially replace a taken card (due to higher GIHWR or lower CMC), then it will add a curve bonus ranging from 0.1 - 0.25.
        
- **Color Bonus:** If column 4 is set to `All Decks`, or `Auto` with fewer than 16 cards, then the application will add a color bonus based on the top 3 colors identified from the taken cards.
    - Color Bonus Factors:
        - The application will add a color bonus of 0.3 for each taken card that has a GIHWR equal to or above 65%
        - The application will add a color bonus of 0.2 for each taken card that has a GIHWR between 64.9% and 60%.
        - The application will add a color bonus of 0.1 for each taken card that has a GIHWR between 59.9% and 52%.
        - For colorless cards, the application will divide the highest color bonus by 2.
        
- **Deck Suggester:** For each viable color combination, the deck suggester will construct multiple decks (Aggro, Mid, and Control decks), using some generic deck building requirements, from a card pool of the highest win rate cards. The suggester will rate each deck and choose the highest rated deck for each viable color combination. The deck suggester will NOT identify card synergies and build an intentionally synergistic deck. 
    - Deck Building Requirements:
        - Aggro Deck:
            - The deck must have a minimum of 13 creatures and should have no less than 17 creatures.
            - The deck should have at least 2 1-drops, 5 2-drops, and 3 3-drops.
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
        - The deck distribution and CMC requirements can result in the inclusion of some poor-performing cards.
            Example: If the user has a pool of white and blue cards, and the only 3-drops are Acquisition Octopus (53.7% for WU) and Guardians of Oboro (50.7% for WU), then the suggester will include those two cards to fulfill the 3-drop requirement (3 Aggro/3 Mid/3 Control).
        - The rating consists of the combined GIHWR of all of the cards minus penalties for not adhering to the deck requirements.
        - The NEO creature sagas count as creatures.

- **Tier List Ratings:** The tier scraper Chrome extension, found in `./Tools/TierScraper17Lands`, converts the grades in a 17Lands tier list into ratings using the following table:

| Letter Grade     | Numeric Rating     |
|:----------------:|:------------------:|
| A+               | 5.0                |
| A                | 4.6                |
| A-               | 4.2                |
| B+               | 3.8                |
| B                | 3.5                |
| B-               | 3.1                |
| C+               | 2.7                |
| C                | 2.3                |
| C-               | 1.9                |
| D+               | 1.5                |
| D                | 1.2                |
| D-               | 0.8                |
| F                | 0.4                |
| SB               | 0.0                |
| TBD              | 0.0                |
