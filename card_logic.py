import json
import logging
import constants
import log_scanner as LS
from itertools import combinations
from dataclasses import dataclass, asdict

logic_logger = logging.getLogger(constants.LOG_TYPE_DEBUG)

@dataclass 
class DeckType:
    distribution: list
    maximum_card_count: int
    recommended_creature_count: int
    cmc_average : float

@dataclass
class Config:
    table_width : int=270
    column_2 : str=constants.COLUMNS_OPTIONS_MAIN_DICT[constants.COLUMN_2_DEFAULT]
    column_3 : str=constants.COLUMNS_OPTIONS_MAIN_DICT[constants.COLUMN_3_DEFAULT]
    column_4 : str=constants.COLUMNS_OPTIONS_MAIN_DICT[constants.COLUMN_4_DEFAULT]
    column_5 : str=constants.COLUMNS_OPTIONS_EXTRA_DICT[constants.COLUMN_5_DEFAULT]
    column_6 : str=constants.COLUMNS_OPTIONS_EXTRA_DICT[constants.COLUMN_6_DEFAULT]
    column_7 : str=constants.COLUMNS_OPTIONS_EXTRA_DICT[constants.COLUMN_7_DEFAULT]
    deck_filter : str=constants.DECK_FILTER_DEFAULT
    filter_format : str=constants.DECK_FILTER_FORMAT_COLORS
    result_format : str=constants.RESULT_FORMAT_WIN_RATE
    missing_enabled : bool=True
    stats_enabled : bool=True
    hotkey_enabled : bool=True
    images_enabled : bool=True
    auto_highest_enabled : bool=True
    curve_bonus_enabled : bool=False
    color_bonus_enabled : bool=False
    bayesian_average_enabled : bool=False
    draft_log_enabled: bool=False
    minimum_creatures : int=13
    minimum_noncreatures : int=6
    ratings_threshold : int=500
    alsa_weight : float=0.0
    iwd_weight :float=0.0

    deck_mid : DeckType=DeckType([0,0,4,3,2,1,0], 23, 15, 3.04)
    deck_aggro : DeckType=DeckType([0,2,5,3,0,0,0], 24, 17, 2.40)
    deck_control : DeckType=DeckType([0,0,3,3,3,1,1], 22, 14, 3.68)
    
    database_size : int=0
    

def CompareRatings(a, b):
    try:
        if(a["rating_filter_c"] == b["rating_filter_c"]):
            return a[constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_ALSA] - b[constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_ALSA]
        else:
            return b["rating_filter_c"] - a["rating_filter_c"]
    except Exception as error:
        logic_logger.info(f"CompareRatings Error: {error}")
    return 0

def ColorAffinity(colors, card):
    rating = card["rating"]
    if(rating  >= 1.5):
        for color in card[constants.DATA_FIELD_COLORS]:
            if (color not in colors):
                colors[color] = 0
            colors[color] += rating
        
    return colors 
  
def ColorBonus (deck, deck_colors, card, bayesian_enabled):

    color_bonus_factor = 0.0
    color_bonus_level = 0.0
    search_colors = ""
    combined_colors = "".join(deck_colors)
    combined_colors = "".join(set(combined_colors))
    try:                        
        card_colors = card[constants.DATA_FIELD_COLORS]
        if(len(card_colors) == 0):
            color_bonus_factor = 0.5
            search_colors = list(deck_colors)[0]
        else:
            matching_colors = list(filter((lambda x : x in combined_colors), card_colors))
            color_bonus_factor = len(matching_colors) / len(card_colors)
            search_colors = matching_colors

        searched_cards = DeckColorSearch(deck, search_colors, ["Creature", "Planeswalker","Instant", "Sorcery","Enchantment","Artifact"], True, False, True)
        for card in searched_cards:
            gihwr = CalculateWinRate(card[constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIHWR],
                                     card[constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIH],
                                     bayesian_enabled)
            if gihwr >= 65.0:
                color_bonus_level += 0.3
            elif gihwr >= 60.0:
                color_bonus_level += 0.2
            elif gihwr >= 52.0:
                color_bonus_level += 0.1
        color_bonus_level = min(color_bonus_level, 1)
        
    except Exception as error:
        logic_logger.info(f"ColorBonus Error: {error}")
    
    return round(color_bonus_factor * color_bonus_level,1)
    
def CurveBonus(deck, card, pick_number, color_filter, configuration):
    curve_bonus_levels = [0.1, 0.1, 0.1, 0.1, 0.1,
                          0.2, 0.2, 0.2, 0.2, 0.2,
                          0.3, 0.3, 0.3, 0.5, 0.5,
                          0.6, 0.6, 1.0, 1.0, 1.0]

    curve_start = 15
    index = max(pick_number - curve_start, 0)
    curve_bonus = 0.0
    curve_bonus_factor = 0.0
    minimum_creature_count = configuration.minimum_creatures
    minimum_distribution = configuration.deck_mid.distribution
    
    try:
        matching_colors = list(filter((lambda x : x in color_filter), card[constants.DATA_FIELD_COLORS]))
        
        if len(matching_colors) or len(card[constants.DATA_FIELD_COLORS]) == 0:
            if any(x in card[constants.DATA_FIELD_TYPES] for x in ["Creature", "Planeswalker"]):
                card_list = DeckColorSearch(deck, color_filter, ["Creature", "Planeswalker"], True, True, False)
                for card in card_list:
                    card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIHWR] = CalculateWinRate(card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIHWR],
                                                                                  card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIH],
                                                                                  configuration.bayesian_average_enabled)
                #card_list = [CalculateWinRate(x[constants.DATA_FIELD_DECK_COLORS][color_filter], configuration.bayesian_average_enabled) for x in card_list] 
                card_colors_sorted = sorted(card_list, key = lambda k: k[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIHWR], reverse = True)
                
                cmc_total, count, distribution = ColorCmc(card_colors_sorted)
                curve_bonus = curve_bonus_levels[int(min(index, len(curve_bonus_levels) - 1))]
                
                curve_bonus_factor = 1
                if(count > minimum_creature_count):
                    card_gihwr = CalculateWinRate(card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIHWR],
                                                  card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIH],
                                                  configuration.bayesian_average_enabled)
                    replaceable = [x for x in card_colors_sorted if (card[constants.DATA_FIELD_CMC] <= x[constants.DATA_FIELD_CMC] and (card_gihwr > x[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIHWR]))]
                    curve_bonus_factor = 0
                    if len(replaceable):
                        index = int(min(card[constants.DATA_FIELD_CMC], len(distribution) - 1))
                        
                        if(distribution[index] < minimum_distribution[index]):
                            curve_bonus_factor = 0.5
                        else:
                            curve_bonus_factor = 0.25
    except Exception as error:
        logic_logger.info(f"CurveBonus Error: {error}")
        
    return curve_bonus * curve_bonus_factor
    
def DeckColorSearch(deck, search_colors, card_types, include_types, include_colorless, include_partial):
    card_color_sorted = {}
    main_color = ""
    combined_cards = []
    for card in deck:
        try:
            card_colors = CardColors(card["mana_cost"])

            if not card_colors:
                card_colors = card[constants.DATA_FIELD_COLORS]

            if bool(card_colors) and (set(card_colors) <= set(search_colors)):
                main_color = card_colors[0]

                if((include_types and any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types)) or
                (not include_types and not any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types))):

                    if main_color not in card_color_sorted.keys():
                        card_color_sorted[main_color] = []
                        
                    #if search_colors in card[constants.DATA_FIELD_DECK_COLORS].keys(): 
                    card_color_sorted[main_color].append(card)

            elif set(search_colors).intersection(card_colors) and include_partial:
                for color in card_colors:
                    if((include_types and any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types)) or
                    (not include_types and not any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types))):
    
                        if color not in card_color_sorted.keys():
                            card_color_sorted[color] = []
                            
                        #if search_colors in card[constants.DATA_FIELD_DECK_COLORS].keys(): 
                        card_color_sorted[color].append(card)

            if (bool(card_colors) == False) and include_colorless:
            
                if((include_types and any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types)) or
                (not include_types and not any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types))):

                    #if search_colors in card[constants.DATA_FIELD_DECK_COLORS].keys(): 
                    combined_cards.append(card)
        except Exception as error:
            logic_logger.info(f"DeckColorSearch Error: {error}")

    for color in card_color_sorted:
        if color in search_colors:
            combined_cards.extend(card_color_sorted[color])
            
    return combined_cards
    
def ColorCmc(deck):
    cmc_total = 0
    count = 0
    distribution = [0, 0, 0, 0, 0, 0, 0]
    
    try:
        for card in deck:
            cmc_total += card[constants.DATA_FIELD_CMC]
            count += 1
            index = int(min(card[constants.DATA_FIELD_CMC], len(distribution) - 1))
            distribution[index] += 1
    
    except Exception as error:
        logic_logger.info(f"ColorCmc Error: {error}")
    
    return cmc_total, count, distribution
    
def OptionFilter(deck, option_selection, configuration):
    filtered_color_list = [option_selection]
    try:
        if constants.FILTER_OPTION_AUTO in option_selection:
            filtered_color_list = AutoColors(deck, 2, configuration)
        else:
            filtered_color_list = [option_selection]
    except Exception as error:
        logic_logger.info(f"OptionFilter Error: {error}")
    return filtered_color_list
    
def DeckColors(deck, colors_max, configuration):
    try:
        deck_colors = {}
        
        colors = CalculateColorAffinity(deck,constants.FILTER_OPTION_ALL_DECKS,52, configuration)
        
        # Modify the dictionary to include ratings
        color_list = list(map((lambda x : {"color" : x, "rating" : colors[x]}), colors.keys()))
        
        # Sort the list by decreasing ratings
        color_list = sorted(color_list, key = lambda k : k["rating"], reverse = True)
        
        # Remove extra colors beyond limit
        color_list = color_list[0:3]
        
        # Return colors 
        sorted_colors = list(map((lambda x : x["color"]), color_list))
        
        #Create color permutation
        color_combination = []
        
        for count in range(colors_max + 1):
            if count > 1:
                color_combination.extend(combinations(sorted_colors, count))
            else:
                color_combination.extend((sorted_colors))

        #Convert tuples to list of strings
        color_strings = [''.join(tups) for tups in color_combination]
        color_strings = [x for x in color_strings if len(x) <= colors_max]

        color_strings = list(set(color_strings))

        color_dict = {}
        for color_string in color_strings:
            for color in color_string:
                if color_string not in color_dict.keys():
                    color_dict[color_string] = 0
                color_dict[color_string] += colors[color]
        
        for color_option in constants.DECK_COLORS:
            for color_string in color_dict.keys():
                if (len(color_string) == len(color_option)) and set(color_string).issubset(color_option):
                    deck_colors[color_option] = color_dict[color_string]

        deck_colors = dict(sorted(deck_colors.items(), key=lambda item: item[1], reverse=True))
        
    except Exception as error:
        logic_logger.info(f"DeckColors Error: {error}")
    
    return deck_colors
    
def AutoColors(deck, colors_max, configuration):
    try:
        deck_colors_list = [constants.FILTER_OPTION_ALL_DECKS]
        colors_dict = {}
        deck_length = len(deck)
        if deck_length > 15:
            colors_dict = DeckColors(deck, colors_max, configuration)
            colors = list(colors_dict.keys())
            auto_select_threshold = 30 - deck_length
            if (len(colors) > 1) and ((colors_dict[colors[0]] - colors_dict[colors[1]]) > auto_select_threshold):
                deck_colors_list = colors[0:1]
            elif len(colors) == 1:
                deck_colors_list = colors[0:1]
            elif configuration.auto_highest_enabled == True:
                deck_colors_list = colors[0:2]

    except Exception as error:
        logic_logger.info(f"AutoColors Error: {error}")
    
    return deck_colors_list

def CalculateColorAffinity(deck_cards, color_filter, threshold, configuration):
    #Identify deck colors  based on the number of high win rate cards
    colors = {}
    
    for card in deck_cards:
        try:
            gihwr = CalculateWinRate(card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIHWR],
                                     card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIH],
                                     configuration.bayesian_average_enabled)
            if gihwr > threshold:
                for color in card[constants.DATA_FIELD_COLORS]:
                    if color not in colors:
                        colors[color] = 0
                    colors[color] += (gihwr - threshold)
        except Exception as error:
            logic_logger.info(f"CalculateColorAffinity Error: {error}")
    return colors 

def CardFilter(card_list, deck, filtered_colors, fields,  limits, tier_list, configuration, curve_bonus, color_bonus):
    filtered_list = []
    
    deck_colors = DeckColors(deck, 2, configuration)
    deck_colors = deck_colors.keys()
    
    for card in card_list:
        try:
            selected_card = card
            selected_card["results"] = [0.0] * len(fields)
            selected_card["curve_bonus"] = []
            selected_card["color_bonus"] = []

            for count, option in enumerate(fields.values()):
               
                for color in filtered_colors:
                    if constants.FILTER_OPTION_TIER in option:
                        card_name = card[constants.DATA_FIELD_NAME].split(" // ")
                        if card_name[0] in tier_list[option][constants.DATA_SECTION_RATINGS]:
                            selected_card["results"][count] = tier_list[option][constants.DATA_SECTION_RATINGS][card_name[0]]
                    elif (option in constants.WIN_RATE_OPTIONS) and (option in card[constants.DATA_FIELD_DECK_COLORS][color]):
                        rated_colors = []
                        rating_data = FormattedResult(card,
                                                      option, 
                                                      constants.WIN_RATE_FIELDS_DICT[option],
                                                      limits, 
                                                      configuration, 
                                                      color, 
                                                      deck, 
                                                      deck_colors, 
                                                      curve_bonus, 
                                                      color_bonus)
                        rated_colors.append(rating_data["result"])
                        if "curve_bonus" in rating_data:
                            selected_card["curve_bonus"].append(rating_data["curve_bonus"])
                        if "color_bonus" in rating_data:
                            selected_card["color_bonus"].append(rating_data["color_bonus"])
                        if len(rated_colors):
                            selected_card["results"][count] = sorted(rated_colors, reverse = True)[0]
                    elif option in card[constants.DATA_FIELD_DECK_COLORS][color]:
                        selected_card["results"][count] = card[constants.DATA_FIELD_DECK_COLORS][color][option]
                    elif option == constants.DATA_FIELD_COLORS:
                        selected_card["results"][count] = "".join(card[option])
                    elif option in card:
                        selected_card["results"][count] = card[option]
            filtered_list.append(selected_card)
        except Exception as error:
            logic_logger.info(f"CardFilter Error: {error}")

    return filtered_list

def RowColorTag(colors):
    row_tag = "goldcard"
    if len(colors) > 1:
        row_tag = "goldcard"
    elif "R" in colors:
        row_tag = "redcard"
    elif "U" in colors:
        row_tag = "bluecard"
    elif "B" in colors:
        row_tag = "blackcard"
    elif "W" in colors:
        row_tag = "whitecard"
    elif "G" in colors:
        row_tag = "greencard"
    return row_tag
    
def RatingsLimits(cards, bayesian_enabled):
    upper_limit = 0
    lower_limit = 100
    
    for card in cards:
        for color in constants.DECK_COLORS:
            try:
                if color in cards[card][constants.DATA_FIELD_DECK_COLORS]:
                    gihwr = CalculateWinRate(cards[card][constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR],
                                             cards[card][constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIH],
                                             bayesian_enabled)
                    if gihwr > upper_limit:
                        upper_limit = gihwr
                    if gihwr < lower_limit and gihwr != 0:
                        lower_limit = gihwr
            except Exception as error:
                logic_logger.info(f"DeckRatingLimits Error: {error}")
    
    return upper_limit, lower_limit
    
def CalculateWinRate(winrate, count, bayesian_enabled):
    calculated_winrate = 0.0
    try:
        calculated_winrate = winrate
        
        if bayesian_enabled == True:
            win_count = winrate * count
            calculated_winrate = (win_count + 1000)/ (count + 20) #Bayesian average calculation
            calculated_winrate = round(calculated_winrate, 2)
        else:
            if count < 200:
                calculated_winrate = 0.0
    except Exception as error:
        logic_logger.info(f"CalculateWinRate Error: {error}")
    return calculated_winrate
    
def FormattedResult(card_data, winrate_field, winrate_count, limits, configuration, filter, deck, deck_colors, enable_curve_bonus, enable_color_bonus):
    rating_data = {"result" : 0}
    #Produce a result that matches the Result Format setting
    if configuration.result_format == constants.RESULT_FORMAT_RATING:
        rating_data = CardRating(card_data, winrate_field, winrate_count, limits, configuration, filter, deck, deck_colors, enable_curve_bonus, enable_color_bonus)
    else:
        rating_data["result"] = CalculateWinRate(card_data[constants.DATA_FIELD_DECK_COLORS][filter][winrate_field],
                                                 card_data[constants.DATA_FIELD_DECK_COLORS][filter][winrate_count],
                                                 configuration.bayesian_average_enabled)
        
    return rating_data
    
def CardRating(card_data, winrate_field, winrate_count, limits, configuration, filter, deck, deck_colors, enable_curve_bonus, enable_color_bonus):
    rating_data = {"result" : 0}
    try:
        gihwr = CalculateWinRate(card_data[constants.DATA_FIELD_DECK_COLORS][filter][winrate_field],
                                 card_data[constants.DATA_FIELD_DECK_COLORS][filter][winrate_count],
                                 configuration.bayesian_average_enabled)
        upper_limit = 0
        lower_limit = 0
        if "upper" in limits:
            upper_limit = limits["upper"]
            
        if "lower" in limits:
            lower_limit = limits["lower"]

        if (enable_curve_bonus) and (filter != constants.FILTER_OPTION_ALL_DECKS):
            rating_data["curve_bonus"] = 0.0

        if (enable_color_bonus) and (filter == constants.FILTER_OPTION_ALL_DECKS):
            rating_data["color_bonus"] = 0.0
        
        if (gihwr != 0) and (upper_limit != lower_limit):
            #Curve bonus
            pick_number = len(deck)
            if "curve_bonus" in rating_data:
                rating_data["curve_bonus"] = CurveBonus(deck, card_data, pick_number, filter, configuration)
                
            #Color bonus
            if "color_bonus" in rating_data:
                rating_data["color_bonus"] = ColorBonus(deck, deck_colors, card_data, configuration.bayesian_average_enabled)
        
            #Calculate the ALSA bonus
            alsa_bonus = ((15 - card_data[constants.DATA_FIELD_DECK_COLORS][filter][constants.DATA_FIELD_ALSA]) / 10) * configuration.alsa_weight
            
            #Calculate IWD penalty
            iwd_penalty = 0
            
            if card_data[constants.DATA_FIELD_DECK_COLORS][filter][constants.DATA_FIELD_IWD] < 0:
                iwd_penalty = (max(card_data[constants.DATA_FIELD_DECK_COLORS][filter][constants.DATA_FIELD_IWD], -10) / 10) * configuration.iwd_weight     
            
            gihwr = min(gihwr, upper_limit)
            gihwr = max(gihwr, lower_limit)
            
            rating_data["result"] = ((gihwr - lower_limit) / (upper_limit - lower_limit)) * 5.0
            
            #Make adjustments
            rating_data["result"] += alsa_bonus + iwd_penalty
            
            if "curve_bonus" in rating_data:
                rating_data["result"] += rating_data["curve_bonus"]
                
            if "color_bonus" in rating_data:
                rating_data["result"] += rating_data["color_bonus"]
            
            rating_data["result"] = round(rating_data["result"], 1)
            
            rating_data["result"] = min(rating_data["result"], 5.0)
            rating_data["result"] = max(rating_data["result"], 0)
            
    except Exception as error:
        logic_logger.info(f"CardRating Error: {error}")
    return rating_data
    
def DeckColorStats(deck, color):
    creature_count = 0
    noncreature_count = 0

    try:
        creature_cards = DeckColorSearch(deck, color, ["Creature", "Planeswalker"], True, True, False)
        noncreature_cards = DeckColorSearch(deck, color, ["Creature", "Planeswalker"], False, True, False)
        
        creature_count = len(creature_cards)
        noncreature_count = len(noncreature_cards)
        
    except Exception as error:
        logic_logger.info(f"DeckColorStats Error: {error}")
    
    return creature_count, noncreature_count
    
def CardCmcSearch(deck, offset, starting_cmc, cmc_limit, remaining_count):
    cards = []
    unused = []
    try:
        for count, card in enumerate(deck[offset:]):
            card_cmc = card[constants.DATA_FIELD_CMC]
            
            if card_cmc + starting_cmc <= cmc_limit:
                card_cmc += starting_cmc
                current_offset = offset + count
                current_remaining = int(max(remaining_count - 1, 0))
                if current_remaining == 0:
                    cards.append(card)
                    unused.extend(deck[current_offset + 1:])
                    break
                elif current_offset > (len(deck) - remaining_count):
                    unused.extend(deck[current_offset:])
                    break
                else:
                    current_offset += 1
                    cards, skipped = CardCmcSearch(deck, current_offset, card_cmc, cmc_limit, current_remaining)
                    if len(cards):
                        cards.append(card)
                        unused.extend(skipped)
                        break 
                    else:
                        unused.append(card) 
            else: 
                unused.append(card)
    except Exception as error:
        logic_logger.info(f"CardCmcSearch Error: {error}")
    
    return cards, unused
    
def DeckRating(deck, deck_type, color, bayesian_enabled):
    rating = 0
    try:
        #Combined GIHWR of the cards
        for card in deck:
            try:
                gihwr = CalculateWinRate(card[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR],
                                         card[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIH],
                                         bayesian_enabled)
                if gihwr > 50.0:
                    rating += gihwr
            except Exception as error:
                rating += 0
        #Deck contains the recommended number of creatures
        recommended_creature_count = deck_type.recommended_creature_count
        filtered_cards = DeckColorSearch(deck, color, ["Creature", "Planeswalker"], True, True, False)
        
        if len(filtered_cards) < recommended_creature_count:
            rating -= (recommended_creature_count - len(filtered_cards)) * 100
            
        #Average CMC of the creatures is below the ideal cmc average
        cmc_average = deck_type.cmc_average
        total_cards = len(filtered_cards)
        total_cmc = 0
        
        for card in filtered_cards:
            total_cmc += card[constants.DATA_FIELD_CMC]
        
        cmc = total_cmc / total_cards
        
        if cmc > cmc_average:
            rating -= 500
        
        #Cards fit distribution
        minimum_distribution = deck_type.distribution
        distribution = [0, 0, 0, 0, 0, 0, 0]
        for card in filtered_cards:
            index = int(min(card[constants.DATA_FIELD_CMC], len(minimum_distribution) - 1))
            distribution[index] += 1
            
        for index, value in enumerate(distribution):
            if value < minimum_distribution[index]:
                rating -= 100
                
    except Exception as error:
        logic_logger.info(f"DeckRating Error: {error}")
    
    return rating
    
def CopyDeck(deck, sideboard, set_cards):
    deck_copy = ""
    starting_index = 0
    total_deck = len(deck)
    card_count = 0
    basic_lands = ["Mountain","Forest","Swamp","Plains","Island"]
    try:
        #Copy Deck
        deck_copy = "Deck\n"
        #identify the arena_id for the cards
        for card in deck:
            deck_copy += ("%d %s\n" % (card[constants.DATA_FIELD_COUNT],card[constants.DATA_FIELD_NAME]))
        
        #Copy sideboard
        if sideboard != None:
            deck_copy += "\nSideboard\n"
            for card in sideboard:
                deck_copy += ("%d %s\n" % (card[constants.DATA_FIELD_COUNT],card[constants.DATA_FIELD_NAME]))
        
    except Exception as error:
        logic_logger.info(f"CopyDeck Error: {error}")
        
    return deck_copy
   
    
def StackCards(cards):
    deck = {}
    deck_list = []
    for card in cards:
        try:
            name = card[constants.DATA_FIELD_NAME]
            if name not in deck.keys():
                deck[name] = {constants.DATA_FIELD_COUNT : 1} 
                for field in constants.DATA_SET_FIELDS:
                    field = field
                    if field in card:
                        deck[name][field] = card[field]
            else:
                deck[name][constants.DATA_FIELD_COUNT] += 1
        except Exception as error:
            logic_logger.info(f"StackCards Error: {error}")   
    #Convert to list format
    for card in deck:
        deck_list.append(deck[card])

    return deck_list
    
def CardColors(mana_cost):
    colors = []
    try:
        if "B" in mana_cost:
            colors.append("B")
        
        if "G" in mana_cost:
            colors.append("G")
            
        if "R" in mana_cost:
            colors.append("R")
            
        if "U" in mana_cost:
            colors.append("U") 
            
        if "W" in mana_cost:
            colors.append("W")
    except Exception as error:
        print ("CardColors Error: %s" % error)
    return colors
    
#Identify splashable color
def ColorSplash(cards, colors, configuration):
    color_affinity = {}
    splash_color = ""
    try:
        # Calculate affinity
        color_affinity = CalculateColorAffinity(cards, colors, 65, configuration)
        
        # Modify the dictionary to include ratings
        color_affinity = list(map((lambda x : {"color" : x, "rating" : color_affinity[x]}), color_affinity.keys()))
        #Remove the current colors
        filtered_colors = color_affinity[:]
        for color in color_affinity:
            if color["color"] in colors:
                filtered_colors.remove(color)
        # Sort the list by decreasing ratings
        filtered_colors = sorted(filtered_colors, key = lambda k : k["rating"], reverse = True)
            
        if len(filtered_colors):
            splash_color = filtered_colors[0]["color"]
    except Exception as error:
        logic_logger.info(f"ColorSplash Error: {error}")   
    return splash_color
    

#Identify the number of lands needed to fill the deck
def ManaBase(deck):
    maximum_deck_size = 40
    combined_deck = []
    mana_types = {"Swamp" : {"color" : "B", constants.DATA_FIELD_COUNT : 0},
                  "Forest" : {"color" : "G", constants.DATA_FIELD_COUNT : 0},
                  "Mountain" : {"color" : "R", constants.DATA_FIELD_COUNT : 0},
                  "Island": {"color" : "U", constants.DATA_FIELD_COUNT : 0},
                  "Plains" : {"color" : "W", constants.DATA_FIELD_COUNT : 0}}
    total_count = 0
    try:
        number_of_lands = 0 if maximum_deck_size < len(deck) else maximum_deck_size - len(deck)
        
        #Go through the cards and count the mana types
        for card in deck:
            mana_types["Swamp"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count("B")
            mana_types["Forest"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count("G")
            mana_types["Mountain"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count("R")
            mana_types["Island"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count("U")
            mana_types["Plains"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count("W")
            
        for land in mana_types:
            total_count += mana_types[land][constants.DATA_FIELD_COUNT]
        
        #Sort by lowest count
        mana_types = dict(sorted(mana_types.items(), key=lambda t: t[1]['count']))
        #Add x lands with a distribution set by the mana types
        for index, land in enumerate(mana_types):
            if (mana_types[land][constants.DATA_FIELD_COUNT] == 1) and (number_of_lands > 1):
                land_count = 1
                number_of_lands -= 1
            else:
                land_count = round((mana_types[land][constants.DATA_FIELD_COUNT] / total_count) * number_of_lands, 0)
                #Minimum of 2 lands for a  splash
                if (land_count == 1) and (number_of_lands > 1):
                    land_count = 2
                    number_of_lands -= 1
            
            if mana_types[land][constants.DATA_FIELD_COUNT] != 0:
                card = {constants.DATA_FIELD_COLORS : mana_types[land]["color"], constants.DATA_FIELD_TYPES : "Land", constants.DATA_FIELD_CMC : 0.0, constants.DATA_FIELD_NAME : land, constants.DATA_FIELD_COUNT : land_count}
                combined_deck.append(card) 
            
    except Exception as error:
        logic_logger.info(f"ManaBase Error: {error}")
    return combined_deck
    
def SuggestDeck(taken_cards, limits, configuration):
    colors_max = 3
    maximum_card_count = 23
    sorted_decks = {}
    try:
        deck_types = {"Mid" : configuration.deck_mid, "Aggro" : configuration.deck_aggro, "Control" :configuration.deck_control}
        #Calculate the base ratings
        #fields = {"filtered_a" : constants.DATA_FIELD_GIHWR.upper(), "filtered_b" : constants.DATA_FIELD_GIHWR.upper(), "filtered_c" : constants.DATA_FIELD_GIHWR.upper()}
        #filtered_cards = CardFilter(taken_cards, taken_cards, [constants.FILTER_OPTION_ALL_DECKS], fields, limits, None, configuration, False, False)
        #Identify the top color combinations
        colors = DeckColors(taken_cards, colors_max, configuration)
        colors = colors.keys()
        filtered_colors = []
        
        #Collect color stats and remove colors that don't meet the minimum requirements
        for color in colors:
            creature_count, noncreature_count = DeckColorStats(taken_cards, color)
            if((creature_count >= configuration.minimum_creatures) and 
               (noncreature_count >= configuration.minimum_noncreatures) and
               (creature_count + noncreature_count >= maximum_card_count)):
                filtered_colors.append(color)
            
        decks = {}
        for color in filtered_colors:
            for type in deck_types.keys():
                deck, sideboard_cards = BuildDeck(deck_types[type], taken_cards, color, limits, configuration)
                rating = DeckRating(deck, deck_types[type], color, configuration.bayesian_average_enabled)
                if rating >= configuration.ratings_threshold:
                    
                    if ((color not in decks.keys()) or 
                        (color in decks.keys() and rating > decks[color]["rating"] )):
                        decks[color] = {}
                        decks[color]["deck_cards"] = StackCards(deck)
                        decks[color]["sideboard_cards"] = StackCards(sideboard_cards)
                        decks[color]["rating"] = rating
                        decks[color]["type"] = type
                        decks[color]["deck_cards"].extend(ManaBase(deck))
        
        sorted_colors  = sorted(decks, key=lambda x: decks[x]["rating"], reverse=True)
        for color in sorted_colors:
            sorted_decks[color] = decks[color]
    except Exception as error:
        logic_logger.info(f"SuggestDeck Error: {error}")

    return sorted_decks
    
def BuildDeck(deck_type, cards, color, limits, configuration):
    minimum_distribution = deck_type.distribution
    maximum_card_count = deck_type.maximum_card_count
    maximum_deck_size = 40
    cmc_average = deck_type.cmc_average
    recommended_creature_count = deck_type.recommended_creature_count
    used_list = []
    sideboard_list = cards[:] #Copy by value
    try:
        #filter cards using the correct deck's colors
        #fields = {"filtered_a" : constants.DATA_FIELD_GIHWR.upper(), "filtered_b" : constants.DATA_FIELD_GIHWR.upper(), "filtered_c" : constants.DATA_FIELD_GIHWR.upper()}
        #filtered_cards = CardFilter(cards, cards, [color], fields, limits, None, configuration, False, False)
        
        #identify a splashable color
        color +=(ColorSplash(cards, color, configuration))
        
        card_colors_sorted = DeckColorSearch(cards, color, ["Creature", "Planeswalker"], True, True, False)
        card_colors_sorted = sorted(card_colors_sorted, key = lambda k: k[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR], reverse = True)
        
        #Identify creatures that fit distribution
        distribution = [0,0,0,0,0,0,0]
        unused_list = []
        used_list = []
        used_count = 0
        used_cmc_combined = 0
        for card in card_colors_sorted:
            index = int(min(card[constants.DATA_FIELD_CMC], len(minimum_distribution) - 1))
            if(distribution[index] < minimum_distribution[index]):
                used_list.append(card)
                distribution[index] += 1
                used_count += 1
                used_cmc_combined += card[constants.DATA_FIELD_CMC]
            else:
                unused_list.append(card)
                
                
        #Go back and identify remaining creatures that have the highest base rating but don't push average above the threshold
        unused_cmc_combined = cmc_average * recommended_creature_count - used_cmc_combined
        
        unused_list.sort(key=lambda x : x[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR], reverse = True)
        
        #Identify remaining cards that won't exceed recommeneded CMC average
        cmc_cards, unused_list = CardCmcSearch(unused_list, 0, 0, unused_cmc_combined, recommended_creature_count - used_count)
        used_list.extend(cmc_cards)
        
        total_card_count = len(used_list)
        
        temp_unused_list = unused_list[:]
        if len(cmc_cards) == 0:
            for count, card in enumerate(unused_list):
                if total_card_count >= recommended_creature_count:
                    break
                    
                used_list.append(card)
                temp_unused_list.remove(card)
                total_card_count += 1
        unused_list = temp_unused_list[:]
            
        card_colors_sorted = DeckColorSearch(cards, color, ["Instant", "Sorcery","Enchantment","Artifact"], True, True, False)
        card_colors_sorted = sorted(card_colors_sorted, key = lambda k: k[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR], reverse = True)
        #Add non-creature cards
        for count, card in enumerate(card_colors_sorted):
            if total_card_count >= maximum_card_count:
                break
                
            used_list.append(card)
            total_card_count += 1
            
                
        #Fill the deck with remaining creatures
        for count, card in enumerate(unused_list):
            if total_card_count >= maximum_card_count:
                break
                
            used_list.append(card)
            total_card_count += 1
            

        #Add in special lands if they are on-color, off-color, and they have a card rating above 2.0
        land_cards = DeckColorSearch(cards, color, ["Land"], True, True, False)
        land_cards = [x for x in land_cards if x[constants.DATA_FIELD_NAME] not in constants.BASIC_LANDS]
        land_cards = sorted(land_cards, key = lambda k: k[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR], reverse = True)
        for card in land_cards:
            if total_card_count >= maximum_deck_size:
                break
                
            if card[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR] >= 55.0:    
                used_list.append(card)
                total_card_count += 1
            
        
        #Identify sideboard cards:
        for card in used_list:
            try:
                sideboard_list.remove(card)
            except Exception as error:
                print("%s error: %s" % (card[constants.DATA_FIELD_NAME], error))
                logic_logger.info(f"Sideboard {card['name']} Error: {error}")
    except Exception as error:
        logic_logger.info(f"BuildDeck Error: {error}")
    return used_list, sideboard_list
    
def ReadConfig():
    config = Config()
    try:
        with open("config.json", 'r') as data:
            config_json = data.read()
            config_data = json.loads(config_json)
        config.hotkey_enabled = config_data["features"]["hotkey_enabled"]
        config.images_enabled = config_data["features"]["images_enabled"]
        config.database_size = config_data["card_data"]["database_size"]
        config.table_width = int(config_data["settings"]["table_width"])
        config.deck_filter = config_data["settings"]["deck_filter"]
        config.column_2 = config_data["settings"]["column_2"]
        config.column_3 = config_data["settings"]["column_3"]
        config.column_4 = config_data["settings"]["column_4"]
        config.column_5 = config_data["settings"]["column_5"]
        config.column_6 = config_data["settings"]["column_6"]
        config.column_7 = config_data["settings"]["column_7"]
        config.filter_format = config_data["settings"]["filter_format"]
        config.result_format = config_data["settings"]["result_format"]
        config.missing_enabled = config_data["settings"]["missing_enabled"]
        config.stats_enabled = config_data["settings"]["stats_enabled"]
        config.auto_highest_enabled = config_data["settings"]["auto_highest_enabled"]
        config.curve_bonus_enabled = config_data["settings"]["curve_bonus_enabled"]
        config.color_bonus_enabled = config_data["settings"]["color_bonus_enabled"]
        config.bayesian_average_enabled = config_data["settings"]["bayesian_average_enabled"]
        config.draft_log_enabled = config_data["settings"]["draft_log_enabled"]
    except Exception as error:
        logic_logger.info(f"ReadConfig Error: {error}")
    return config

def WriteConfig(config):
    try:
        with open("config.json", 'r') as data:
            config_json = data.read()
            config_data = json.loads(config_json)
            
        config_data["card_data"]["database_size"] = config.database_size
        
        config_data["settings"]["column_2"] = config.column_2
        config_data["settings"]["column_3"] = config.column_3
        config_data["settings"]["column_4"] = config.column_4
        config_data["settings"]["column_5"] = config.column_5
        config_data["settings"]["column_6"] = config.column_6
        config_data["settings"]["column_7"] = config.column_7
        config_data["settings"]["deck_filter"] = config.deck_filter
        config_data["settings"]["filter_format"] = config.filter_format
        config_data["settings"]["result_format"] = config.result_format
        config_data["settings"]["missing_enabled"] = config.missing_enabled
        config_data["settings"]["stats_enabled"] = config.stats_enabled
        config_data["settings"]["auto_highest_enabled"] = config.auto_highest_enabled
        config_data["settings"]["curve_bonus_enabled"] = config.curve_bonus_enabled
        config_data["settings"]["color_bonus_enabled"] = config.color_bonus_enabled
        config_data["settings"]["bayesian_average_enabled"] = config.bayesian_average_enabled
        config_data["settings"]["draft_log_enabled"] = config.draft_log_enabled
        
        with open('config.json', 'w', encoding='utf-8') as file:
            json.dump(config_data, file, ensure_ascii=False, indent=4)
    
    except Exception as error:
        logic_logger.info(f"WriteConfig Error: {error}")

def ResetConfig():
    config = Config()
    data = {}
    
    try:
    
        data["features"] = {}
        data["features"]["hotkey_enabled"] = config.hotkey_enabled
        data["features"]["images_enabled"] = config.images_enabled
        
        data["card_data"] = {}
        data["card_data"]["database_size"] = config.database_size
        
        data["settings"] = {}
        data["settings"]["table_width"] = config.table_width
        data["settings"]["column_2"] = config.column_2
        data["settings"]["column_3"] = config.column_3
        data["settings"]["column_4"] = config.column_4
        data["settings"]["column_5"] = config.column_5
        data["settings"]["column_6"] = config.column_6
        data["settings"]["column_7"] = config.column_7
        data["settings"]["deck_filter"] = config.deck_filter
        data["settings"]["filter_format"] = config.filter_format
        data["settings"]["result_format"] = config.result_format
        data["settings"]["missing_enabled"] = config.missing_enabled
        data["settings"]["stats_enabled"] = config.stats_enabled
        data["settings"]["auto_highest_enabled"] = config.auto_highest_enabled
        data["settings"]["curve_bonus_enabled"] = config.curve_bonus_enabled
        data["settings"]["color_bonus_enabled"] = config.color_bonus_enabled
        data["settings"]["bayesian_average_enabled"] = config.bayesian_average_enabled
        data["settings"]["draft_log_enabled"] = config.draft_log_enabled
        
        data["card_logic"] = {}
        data["card_logic"]["alsa_weight"] = config.alsa_weight
        data["card_logic"]["iwd_weight"] = config.iwd_weight
        data["card_logic"]["minimum_creatures"] = config.minimum_creatures
        data["card_logic"]["minimum_noncreatures"] = config.minimum_noncreatures
        data["card_logic"]["ratings_threshold"] = config.ratings_threshold
        data["card_logic"]["deck_types"] = {}
        data["card_logic"]["deck_types"]["Mid"] = {}
        data["card_logic"]["deck_types"]["Mid"] = asdict(config.deck_mid)
        data["card_logic"]["deck_types"]["Aggro"] = {}
        data["card_logic"]["deck_types"]["Aggro"] = asdict(config.deck_aggro)
        data["card_logic"]["deck_types"]["Control"] = {}
        data["card_logic"]["deck_types"]["Control"] = asdict(config.deck_control)
    
        with open('config.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as error:
        logic_logger.info(f"ResetConfig Error: {error}")