import functools
import json
import math
from itertools import combinations
from dataclasses import dataclass, asdict

@dataclass 
class DeckType:
    distribution: list
    maximum_card_count: int
    recommended_creature_count: int
    cmc_average : float

@dataclass
class Config:
    table_width : int=270
    column_2 : str="All ALSA"
    column_3 : str="All Decks"
    column_4 : str="Auto"
    hide_missing : bool=False
    hide_stats : bool=False
    hotkey_enabled : bool=True
    images_enabled : bool=True
    auto_average_disabled : bool=False
    curve_bonus_disabled : bool=False
    color_bonus_disabled : bool=False
    minimum_creatures : int=13
    minimum_noncreatures : int=6
    ratings_threshold : int=500
    alsa_weight : float=0.25
    iwd_weight :float=0.25

    deck_mid : DeckType=DeckType([0,0,4,3,2,1,0], 23, 15, 3.04)
    deck_aggro : DeckType=DeckType([0,1,4,4,1,0,0], 24, 17, 2.40)
    deck_control : DeckType=DeckType([0,0,3,3,3,1,1], 22, 14, 3.68)

def CompareRatings(a, b):
    try:
        #creature_types = ["Creature", "Planeswalker"]
        #a_creature = any(x in a["types"] for x in creature_types)
        #b_creature = any(x in b["types"] for x in creature_types)
        
        if(a["rating_filter_c"] == b["rating_filter_c"]):
            # Breaking ties with lower ALSA > Higher "All Decks"
            if(a["deck_colors"]["All Decks"]["alsa"] == b["deck_colors"]["All Decks"]["alsa"]):
                return b["deck_colors"]["All Decks"]["gihwr"] - a["deck_colors"]["All Decks"]["gihwr"]
            else:
                return a["deck_colors"]["All Decks"]["alsa"] - b["deck_colors"]["All Decks"]["alsa"]
        else:
            return b["rating_filter_c"] - a["rating_filter_c"]
    except Exception as error:
        print("CompareRatings Error: %s" % error)
    return 0

def ColorAffinity(colors, card):
    rating = card["rating"]
    if(rating  >= 1.5):
        for color in card["colors"]:
            if (color not in colors):
                colors[color] = 0
            colors[color] += rating
        
    return colors 
  
def ColorBonus (deck, deck_colors, card):

    color_bonus_factor = 0.0
    color_bonus_level = 0.0
    search_colors = ""
    combined_colors = "".join(deck_colors)
    combined_colors = "".join(set(combined_colors))
    try:                        
        card_colors = card["colors"]
        if(len(card_colors) == 0):
            color_bonus_factor = 0.5
            search_colors = list(deck_colors)[0]
        else:
            matching_colors = list(filter((lambda x : x in combined_colors), card_colors))
            color_bonus_factor = len(matching_colors) / len(card_colors)
            search_colors = matching_colors

        searched_cards = DeckColorSearch(deck, search_colors, ["Creature", "Planeswalker","Instant", "Sorcery","Enchantment","Artifact"], True, False, True)
        for card in searched_cards:
            if card["deck_colors"]["All Decks"]["gihwr"] >= 65.0:
                color_bonus_level += 0.3
            elif card["deck_colors"]["All Decks"]["gihwr"] >= 60.0:
                color_bonus_level += 0.2
            elif card["deck_colors"]["All Decks"]["gihwr"] >= 52.0:
                color_bonus_level += 0.1
        color_bonus_level = min(color_bonus_level, 1)
        
    except Exception as error:
        print(error)
    
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
    cmc_average = configuration.deck_mid.cmc_average
    minimum_creature_count = configuration.minimum_creatures
    minimum_noncreature_count = configuration.minimum_noncreatures
    minimum_distribution = configuration.deck_mid.distribution
    
    try:
        matching_colors = list(filter((lambda x : x in color_filter), card["colors"]))
        
        if len(matching_colors):
            if any(x in card["types"] for x in ["Creature", "Planeswalker"]):
                card_colors_sorted = DeckColorSearch(deck, color_filter, ["Creature", "Planeswalker"], True, True, False)
                card_colors_sorted = sorted(card_colors_sorted, key = lambda k: k["deck_colors"][color_filter]["gihwr"], reverse = True)
                
                cmc_total, count, distribution = ColorCmc(card_colors_sorted)
                curve_bonus = curve_bonus_levels[int(min(index, len(curve_bonus_levels) - 1))]
                
                curve_bonus_factor = 1
                if(count > minimum_creature_count):
                    replaceable = [x for x in card_colors_sorted if (card["cmc"] <= x["cmc"] and (card["deck_colors"][color_filter]["gihwr"]> x["deck_colors"][color_filter]["gihwr"]))]
                    curve_bonus_factor = 0
                    if len(replaceable):
                        index = int(min(card["cmc"], len(distribution) - 1))
                        
                        if(distribution[index] < minimum_distribution[index]):
                            curve_bonus_factor = 0.5
                        else:
                            curve_bonus_factor = 0.25
    except Exception as error:
        print("CurveBonus Error: %s" % error)
        
    return curve_bonus * curve_bonus_factor
    
def DeckColorSearch(deck, search_colors, card_types, include_types, include_colorless, include_partial):
    card_color_sorted = {}
    main_color = ""
    combined_cards = []
    for card in deck:
        try:
            card_colors = CardColors(card["mana_cost"])

            if not card_colors:
                card_colors = card["colors"]

            if include_partial and len(card_colors):
                card_colors = card_colors[0] #Just use the first color

            if bool(card_colors) and (set(card_colors) <= set(search_colors)):
                main_color = card_colors[0]

                if((include_types and any(x in card["types"][0] for x in card_types)) or
                (not include_types and not any(x in card["types"][0] for x in card_types))):

                    if main_color not in card_color_sorted.keys():
                        card_color_sorted[main_color] = []
                        
                    #if search_colors in card["deck_colors"].keys(): 
                    card_color_sorted[main_color].append(card)

            if (bool(card_colors) == False) and include_colorless:
            
                if((include_types and any(x in card["types"][0] for x in card_types)) or
                (not include_types and not any(x in card["types"][0] for x in card_types))):

                    #if search_colors in card["deck_colors"].keys(): 
                    combined_cards.append(card)
        except Exception as error:
            print("DeckColorSearch Error: %s" % error)

    for color in card_color_sorted:
        combined_cards.extend(card_color_sorted[color])
            
    return combined_cards
    
def ColorCmc(deck):
    cmc_total = 0
    count = 0
    distribution = [0, 0, 0, 0, 0, 0, 0]
    
    try:
        for card in deck:
            cmc_total += card["cmc"]
            count += 1
            index = int(min(card["cmc"], len(distribution) - 1))
            distribution[index] += 1
    
    except Exception as error:
        print("ColorCmc Error: %s" % error)
    
    return cmc_total, count, distribution
    
def ColorFilter(deck, color_selection, color_list, auto_average_disabled):
    color_data = color_selection
    filtered_color_list = [color_data]
    non_color_options = ["All GIHWR", "All IWD", "All ALSA"]
    try:
        if color_data == "Auto":
            filtered_color_list = AutoColors(deck, color_list, 2, auto_average_disabled)
        elif color_data == "AI":
            filtered_color_list = ["AI"]
        elif color_data in non_color_options:
            filtered_color_list = [color_data]
        else:
            filtered_color_list = [[key for key, value in color_list.items() if value == color_data][0]]
    except Exception as error:
        print("ColorFilter Error: %s" % error)
    return filtered_color_list
    
def DeckColors(deck, color_options, colors_max):
    try:
        deck_colors = {}
        
        colors = CalculateColorAffinity(deck,"All Decks",52)
        
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
        
        for color_option in color_options.keys():
            for color_string in color_dict.keys():
                if (len(color_string) == len(color_option)) and set(color_string).issubset(color_option):
                    deck_colors[color_option] = color_dict[color_string]

        deck_colors = dict(sorted(deck_colors.items(), key=lambda item: item[1], reverse=True))
        
    except Exception as error:
        print("DeckColors Error: %s" % error)
    
    return deck_colors
    
def AutoColors(deck, color_options, colors_max, auto_average_disabled):
    try:
        deck_colors_list = []
        deck_colors_list.append(next(iter(color_options)))
        colors_dict = {}
        deck_length = len(deck)
        if deck_length > 15:
            colors_dict = DeckColors(deck, color_options, colors_max)
            colors = list(colors_dict.keys())
            print(colors_dict)
            auto_select_threshold = 30 - deck_length
            if (len(colors) > 1) and ((colors_dict[colors[0]] - colors_dict[colors[1]]) > auto_select_threshold):
                deck_colors_list = colors[0:1]
            elif len(colors) == 1:
                deck_colors_list = colors[0:1]
            elif auto_average_disabled == False:
                deck_colors_list = colors[0:2]

    except Exception as error:
        print("AutoColors Error: %s" % error)
    
    return deck_colors_list

def CalculateColorAffinity(deck_cards, color_filter, threshold):
    #Identify deck colors  based on the number of high win rate cards
    colors = {}
    
    for card in deck_cards:
        try:
            gihwr = card["deck_colors"][color_filter]["gihwr"]
            if gihwr > threshold:
                for color in card["colors"]:
                    if color not in colors:
                        colors[color] = 0
                    colors[color] += (gihwr - threshold)
        except Exception as error:
            print("CalculateColorAffinity Error: %s" % error)
    return colors 

def CardFilter(cards, deck, filter_a, filter_b, filter_c, color_options, limits, tier_list, include_curve, include_color):
    configuration = ReadConfig()
    
    configuration.curve_bonus_disabled = configuration.curve_bonus_disabled if include_curve else True
    configuration.color_bonus_disabled = configuration.color_bonus_disabled if include_color else True
    
    filtered_cards = CardColorFilter(cards, tier_list, filter_a, filter_b, filter_c, limits, configuration, deck, color_options)
    return filtered_cards
    
def CardColorFilter(card_list, tier_list, filter_a, filter_b, filter_c, limits, configuration, deck, color_options):
    filtered_list = []
    non_color_options = ["All GIHWR", "All IWD", "All ALSA"]
    ratings_filter_dict = {"rating_filter_a" : filter_a, "rating_filter_b" : filter_b, "rating_filter_c" : filter_c}
    
    deck_colors = DeckColors(deck, color_options, 2)
    deck_colors = deck_colors.keys()
    
    for card in card_list:
        try:
            selected_card = card
            selected_card["rating_filter_a"] = 0.0
            selected_card["rating_filter_b"] = 0.0
            selected_card["rating_filter_c"] = 0.0
            selected_card["curve_bonus"] = []
            selected_card["color_bonus"] = []

            for key, value in ratings_filter_dict.items():
                disable_curve_bonus = True
                disable_color_bonus = True
                #Only include the color and curve bonuses for filter c
                if key == "rating_filter_c":
                    disable_curve_bonus = configuration.curve_bonus_disabled
                    disable_color_bonus = configuration.color_bonus_disabled
                if len(value) == 1:
                    if value[0] in non_color_options:
                        color, type = value[0].split(" ")
                        selected_card[key] = card["deck_colors"]["All Decks"][type.lower()]
                    elif value[0] == "Tier":
                        card_name = card["name"].split(" // ")
                        selected_card[key] = tier_list["ratings"][card_name[0]]
                    else:
                        for deck_color in card["deck_colors"].keys():
                            if deck_color == value[0]:
                                selected_card[key], curve_bonus, color_bonus = CardRating(card, limits, configuration, value[0], deck, deck_colors, disable_curve_bonus, disable_color_bonus)
                                if key == "rating_filter_c":
                                    selected_card["curve_bonus"].append(curve_bonus)
                                    selected_card["color_bonus"].append(color_bonus)
                else:
                    rated_colors = []
                    
                    for colors in value:
                        rating = 0
                        for deck_color in card["deck_colors"].keys():
                            if deck_color == colors:
                                rating, curve_bonus, color_bonus = CardRating(card, limits, configuration, colors, deck, deck_colors, disable_curve_bonus, disable_color_bonus)
                                break
                        rated_colors.append(rating)
                        if key == "rating_filter_c":
                            selected_card["curve_bonus"].append(curve_bonus)
                            selected_card["color_bonus"].append(color_bonus)
                    if len(rated_colors):
                        selected_card[key] = round(sum(rated_colors)/float(len(rated_colors)), 1) #Find the average of all of the ratings
            filtered_list.append(selected_card)
        except Exception as error:
            print("CardColorFilter Error: %s" % error)

    return filtered_list
 
def CardAIFilter(pack, deck, color_options, limits, alsa_weight, iwd_weight):
    try:
        filtered_list = []
        color_limit_start = 15

        pick_number = len(deck) + 1
        
        color_count = 3 if pick_number < color_limit_start else 2
        
        deck_colors = DeckColors(deck, color_options, color_count)
        deck_colors = deck_colors.keys()
        for card in pack:
            selected_card = card
            #selected_card["rating_all"] = CardRating(selected_card["deck_colors"]["All Decks"], limits["All Decks"], alsa_weight, iwd_weight, deck)
            
            selected_card["rating_filter_c"] = CardAIRating(selected_card,
                                                            deck,
                                                            deck_colors,
                                                            limits,
                                                            pick_number)
            filtered_list.append(selected_card)
    except Exception as error:
        print("CardAIFilter Error: %s" % error)
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
    
def DeckColorLimits(cards, color):
    upper_limit = 0
    lower_limit = 100
    for card in cards:
        try:
            gihwr = cards[card]["deck_colors"][color]["gihwr"]
            if gihwr > upper_limit:
                upper_limit = gihwr
            if gihwr < lower_limit and gihwr != 0:
                lower_limit = gihwr
        except Exception as error:
            error_string = "DeckColorLimits Error: %s" % error
    return upper_limit, lower_limit

def CardRating(card_data, limits, configuration, filter, deck, deck_colors, disable_curve_bonus, disable_color_bonus):
    rating = 0
    curve_bonus = 0.0
    color_bonus = 0.0
    winrate = card_data["deck_colors"][filter]["gihwr"]
    try:
        upper_limit = limits[filter]["upper"]
        lower_limit = limits[filter]["lower"]
        
        if (winrate != 0) and (upper_limit != lower_limit):
            #Curve bonus
            pick_number = len(deck)
            if (disable_curve_bonus == False) and (filter != "All Decks"):
                curve_bonus = CurveBonus(deck, card_data, pick_number, filter, configuration)
                
            #Color bonus
            if (disable_color_bonus == False) and (filter == "All Decks"):
                color_bonus = ColorBonus(deck, deck_colors, card_data)
        
            #Calculate the ALSA bonus
            alsa_bonus = ((15 - card_data["deck_colors"][filter]["alsa"]) / 10) * configuration.alsa_weight
            
            #Calculate IWD penalty
            iwd_penalty = 0
            
            if card_data["deck_colors"][filter]["iwd"] < 0:
                iwd_penalty = (max(card_data["deck_colors"][filter]["iwd"], -10) / 10) * configuration.iwd_weight     
            
            winrate = min(winrate, limits[filter]["upper"])
            winrate = max(winrate, limits[filter]["lower"])
            
            rating = ((winrate - lower_limit) / (upper_limit - lower_limit)) * 5.0
            
            #Make adjustments
            rating += alsa_bonus + iwd_penalty + curve_bonus + color_bonus
            
            rating = round(rating, 1)
            
            rating = min(rating, 5.0)
            rating = max(rating, 0)
            
    except Exception as error:
        print("CardRating Error: %s" % error)
    return rating, curve_bonus, color_bonus
    
def CardAIRating(card, deck, deck_colors, limits, pick_number):
    rating = 0
    curve_bonus = 0
    color_bonus = 0
    curve_start = 15
    color_type = "All Decks"
    
    try:
        #Identify color bonus
        color_bonus = ColorBonus(deck, deck_colors, card)
    
        #Identify curve bonus
        if(pick_number >= curve_start):
            #curve_bonus = CurveBonus(deck, deck_colors, card, (pick_number - curve_start))
            
            color_type = deck_colors[0] if color_bonus else "All Decks"
            
    
        winrate = card["deck_colors"][color_type]["gihwr"]

        #Calculate card rating
        upper_limit = limits[color_type]["upper"]
        lower_limit = limits[color_type]["lower"]
        
        if (winrate != 0) and (upper_limit != lower_limit):
            #Calculate the ALSA bonus
            alsa_bonus = ((9 - card["deck_colors"][color_type]["alsa"]) / 8) * 0.5
            
            #Calculate IWD penalty
            iwd_penalty = 0
            
            if card["deck_colors"][color_type]["iwd"] < 0:
                iwd_penalty = (max(card["deck_colors"][color_type]["iwd"], -10) / 10) * 3
        
            winrate = winrate + iwd_penalty + alsa_bonus + color_bonus + curve_bonus
            
            if winrate > limits[color_type]["upper"]:
                winrate = limits[color_type]["upper"]
            elif winrate < limits[color_type]["lower"]:
                winrate = limits[color_type]["lower"]
            
            rating = ((winrate - lower_limit) / (upper_limit - lower_limit)) * 5.0
            
            rating = round(rating, 1)
            
    except Exception as error:
        print("CardAIRating Error: %s" % error)
    return rating
    
def DeckColorStats(deck, color):
    creature_count = 0
    noncreature_count = 0

    try:
        creature_cards = DeckColorSearch(deck, color, ["Creature", "Planeswalker"], True, True, False)
        noncreature_cards = DeckColorSearch(deck, color, ["Creature", "Planeswalker"], False, True, False)
        
        creature_count = len(creature_cards)
        noncreature_count = len(noncreature_cards)
        
    except Exception as error:
        print("DeckColorStats Error: %s" % error)
    
    return creature_count, noncreature_count
    
def CardCmcSearch(deck, offset, starting_cmc, cmc_limit, remaining_count):
    cards = []
    unused = []
    try:
        for count, card in enumerate(deck[offset:]):
            card_cmc = card["cmc"]
            
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
        print("CardCmcSearch Error: %s" % error)
    
    return cards, unused
    
def DeckRating(deck, deck_type, color):
    rating = 0
    try:
        #Combined GIHWR of the cards
        for count, card in enumerate(deck):
            try:
                gihwr = card["deck_colors"][color]["gihwr"]
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
            total_cmc += card["cmc"]
        
        cmc = total_cmc / total_cards
        
        if cmc > cmc_average:
            rating -= 500
        
        #Cards fit distribution
        minimum_distribution = deck_type.distribution
        distribution = [0, 0, 0, 0, 0, 0, 0]
        for card in filtered_cards:
            index = int(min(card["cmc"], len(minimum_distribution) - 1))
            distribution[index] += 1
            
        for index, value in enumerate(distribution):
            if value < minimum_distribution[index]:
                rating -= 100
                
    except Exception as error:
        print("DeckRating Error: %s" % error)
    
    return rating
    
def CopyDeck(deck, sideboard, set_cards, set):
    deck_copy = ""
    starting_index = 0
    total_deck = len(deck)
    card_count = 0
    basic_lands = ["Mountain","Forest","Swamp","Plains","Island"]
    try:
        #Copy Deck
        deck_copy = "Deck\n"
        starting_index = min(set_cards.keys())
        #identify the arena_id for the cards
        for card in deck:
            for index, set_card in enumerate(set_cards):
                if card["name"] in basic_lands:
                    deck_copy += ("%d %s\n" % (card["count"],card["name"]))
                    card_count += 1
                    break;
                elif set_cards[set_card]["name"] == card["name"]:
                    deck_copy += ("%d %s (%s) %d\n" % (card["count"],card["name"],set, (index + 1)))
                    card_count += 1
                    break
        
        #Copy sideboard
        if sideboard != None:
            deck_copy += "\n"
            starting_index = min(set_cards.keys())
            #identify the arena_id for the cards
            for card in sideboard:
                for index, set_card in enumerate(set_cards):
                    if card["name"] in basic_lands:
                        deck_copy += ("%d %s\n" % (card["count"],card["name"]))
                        card_count += 1
                        break;
                    elif set_cards[set_card]["name"] == card["name"]:
                        deck_copy += ("%d %s (%s) %d\n" % (card["count"],card["name"],set, (index + 1)))
                        card_count += 1
                        break
        
    except Exception as error:
        print("CopyDeck Error: %s" % error)
        
    return deck_copy
   
    
def StackCards(cards, color):
    deck = {}
    deck_list = []
    for card in cards:
        try:
            name = card["name"]
            if name not in deck.keys(): 
                deck[name] = {}
                deck[name]["colors"] = card["colors"]
                deck[name]["types"] = card["types"]
                deck[name]["cmc"] = card["cmc"]
                deck[name]["count"] = 1
                deck[name]["name"] = name               
                deck[name]["image"] = card["image"]
                deck[name]["deck_colors"] = card["deck_colors"]
            else:
                deck[name]["count"] += 1
        except Exception as error:
            print("StackCards Error: %s" % error)    
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
def ColorSplash(cards, colors):
    color_affinity = {}
    splash_color = ""
    try:
        # Calculate affinity
        color_affinity = CalculateColorAffinity(cards,colors,65)
        
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
        print("ColorSplash Error: %s" % error)   
    return splash_color
    

#Identify the number of lands needed to fill the deck
def ManaBase(deck):
    maximum_deck_size = 40
    combined_deck = []
    mana_types = {"Swamp" : {"color" : "B", "count" : 0},
                  "Forest" : {"color" : "G", "count" : 0},
                  "Mountain" : {"color" : "R", "count" : 0},
                  "Island": {"color" : "U", "count" : 0},
                  "Plains" : {"color" : "W", "count" : 0}}
    total_count = 0
    try:
        number_of_lands = 0 if maximum_deck_size < len(deck) else maximum_deck_size - len(deck)
        
        #Go through the cards and count the mana types
        for card in deck:
            mana_types["Swamp"]["count"] += card["mana_cost"].count("B")
            mana_types["Forest"]["count"] += card["mana_cost"].count("G")
            mana_types["Mountain"]["count"] += card["mana_cost"].count("R")
            mana_types["Island"]["count"] += card["mana_cost"].count("U")
            mana_types["Plains"]["count"] += card["mana_cost"].count("W")
            
        for land in mana_types:
            total_count += mana_types[land]["count"]
        
        #Sort by lowest count
        mana_types = dict(sorted(mana_types.items(), key=lambda t: t[1]['count']))
        #Add x lands with a distribution set by the mana types
        for index, land in enumerate(mana_types):
            if (mana_types[land]["count"] == 1) and (number_of_lands > 1):
                land_count = 1
                number_of_lands -= 1
            else:
                land_count = round((mana_types[land]["count"] / total_count) * number_of_lands, 0)
                #Minimum of 2 lands for a  splash
                if (land_count == 1) and (number_of_lands > 1):
                    land_count = 2
                    number_of_lands -= 1
            
            if mana_types[land]["count"] != 0:
                card = {"colors" : mana_types[land]["color"], "types" : "Land", "cmc" : 0.0, "name" : land, "count" : land_count}
                combined_deck.append(card) 
            
    except Exception as error:
        print("ManaBase Error: %s" % error)
    #print(combined_deck)
    return combined_deck
    
def SuggestDeck(taken_cards, color_options, limits):
    colors_max = 3
    maximum_card_count = 23
    used_list = []
    sorted_decks = {}
    try:
        configuration = ReadConfig()
        deck_types = {"Mid" : configuration.deck_mid, "Aggro" : configuration.deck_aggro, "Control" :configuration.deck_control}
        #Calculate the base ratings
        filtered_cards = CardColorFilter(taken_cards, None, ["All Decks"],["All Decks"],["All Decks"], limits, configuration, taken_cards, color_options)
        
        #Identify the top color combinations
        colors = DeckColors(taken_cards, color_options, colors_max)
        colors = colors.keys()
        filtered_colors = []
        
        #Collect color stats and remove colors that don't meet the minimum requirements
        for color in colors:
            creature_count, noncreature_count = DeckColorStats(filtered_cards, color)
            if((creature_count >= configuration.minimum_creatures) and 
               (noncreature_count >= configuration.minimum_noncreatures) and
               (creature_count + noncreature_count >= maximum_card_count)):
                filtered_colors.append(color)
            
        decks = {}
        for color in filtered_colors:
            for type in deck_types.keys():
                deck, sideboard_cards = BuildDeck(deck_types[type], taken_cards, color, limits, configuration, color_options)
                rating = DeckRating(deck, deck_types[type], color)
                if rating >= configuration.ratings_threshold:
                    
                    if ((color not in decks.keys()) or 
                        (color in decks.keys() and rating > decks[color]["rating"] )):
                        decks[color] = {}
                        decks[color]["deck_cards"] = StackCards(deck, color)
                        decks[color]["sideboard_cards"] = StackCards(sideboard_cards, color)
                        decks[color]["rating"] = rating
                        decks[color]["type"] = type
                        print("Color: %s, Rating: %s" % (color, decks[color]["rating"]))
                        decks[color]["deck_cards"].extend(ManaBase(deck))
        
        sorted_colors  = sorted(decks, key=lambda x: decks[x]["rating"], reverse=True)
        for color in sorted_colors:
            sorted_decks[color] = decks[color]
    except Exception as error:
        print("SuggestDeck Error: %s" % error)

    return sorted_decks
    
def BuildDeck(deck_type, cards, color, limits, configuration, color_options):
    minimum_distribution = deck_type.distribution
    maximum_card_count = deck_type.maximum_card_count
    maximum_deck_size = 40
    cmc_average = deck_type.cmc_average
    recommended_creature_count = deck_type.recommended_creature_count
    used_list = []
    sideboard_list = cards[:] #Copy by value
    try:
        #filter cards using the correct deck's colors
        filtered_cards = CardColorFilter(cards, None, [color], [color], [color], limits, configuration, cards, color_options)
        
        #identify a splashable color
        color +=(ColorSplash(filtered_cards, color))
        
        card_colors_sorted = DeckColorSearch(filtered_cards, color, ["Creature", "Planeswalker"], True, True, False)
        card_colors_sorted = sorted(card_colors_sorted, key = lambda k: k["rating_filter_c"], reverse = True)
        
        #Identify creatures that fit distribution
        distribution = [0,0,0,0,0,0,0]
        unused_list = []
        used_list = []
        used_count = 0
        used_cmc_combined = 0
        for card in card_colors_sorted:
            index = int(min(card["cmc"], len(minimum_distribution) - 1))
            if(distribution[index] < minimum_distribution[index]):
                used_list.append(card)
                distribution[index] += 1
                used_count += 1
                used_cmc_combined += card["cmc"]
            else:
                unused_list.append(card)
                
                
        #Go back and identify remaining creatures that have the highest base rating but don't push average above the threshold
        unused_cmc_combined = cmc_average * recommended_creature_count - used_cmc_combined
        
        unused_list.sort(key=lambda x : x["rating_filter_c"], reverse = True)
        
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
            
        card_colors_sorted = DeckColorSearch(filtered_cards, color, ["Instant", "Sorcery","Enchantment","Artifact"], True, True, False)
        card_colors_sorted = sorted(card_colors_sorted, key = lambda k: k["rating_filter_c"], reverse = True)
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
        card_colors_sorted = DeckColorSearch(filtered_cards, color, ["Land"], True, True, False)
        card_colors_sorted = sorted(card_colors_sorted, key = lambda k: k["rating_filter_c"], reverse = True)
        for count, card in enumerate(card_colors_sorted):
            if total_card_count >= maximum_deck_size:
                break
                
            if card["rating_filter_c"] >= 2.0:    
                used_list.append(card)
                total_card_count += 1
            
        
        #Identify sideboard cards:
        for card in used_list:
            try:
                sideboard_list.remove(card)
            except Exception as error:
                print("%s error: %s" % (card["name"], error))
    except Exception as error:
        print("BuildDeck Error: %s" % error)
    return used_list, sideboard_list
    
def ReadConfig():
    config = Config()
    try:
        with open("config.json", 'r') as data:
            config_json = data.read()
            config_data = json.loads(config_json)
        config.hotkey_enabled = config_data["features"]["hotkey_enabled"]
        config.images_enabled = config_data["features"]["images_enabled"]
        config.table_width = int(config_data["settings"]["table_width"])
        config.column_2 = config_data["settings"]["column_2"]
        config.column_3 = config_data["settings"]["column_3"]
        config.column_4 = config_data["settings"]["column_4"]
        config.hide_missing = config_data["settings"]["hide_missing"]
        config.hide_stats = config_data["settings"]["hide_stats"]
        config.auto_average_disabled = config_data["settings"]["auto_average_disabled"]
        config.curve_bonus_disabled = config_data["settings"]["curve_bonus_disabled"]
        config.color_bonus_disabled = config_data["settings"]["color_bonus_disabled"]

    except Exception as error:
        print("ReadConfig Error: %s" % error)
    return config

def WriteConfig(config):
    try:
        with open("config.json", 'r') as data:
            config_json = data.read()
            config_data = json.loads(config_json)
        
        config_data["settings"]["column_2"] = config.column_2
        config_data["settings"]["column_3"] = config.column_3
        config_data["settings"]["column_4"] = config.column_4
        config_data["settings"]["hide_missing"] = config.hide_missing
        config_data["settings"]["hide_stats"] = config.hide_stats
        config_data["settings"]["auto_average_disabled"] = config.auto_average_disabled
        config_data["settings"]["curve_bonus_disabled"] = config.curve_bonus_disabled
        config_data["settings"]["color_bonus_disabled"] = config.color_bonus_disabled
        
        with open('config.json', 'w', encoding='utf-8') as file:
            json.dump(config_data, file, ensure_ascii=False, indent=4)
    
    except Exception as error:
        print("WriteConfig Error: %s" % error)

def ResetConfig():
    config = Config()
    data = {}
    
    try:
    
        data["features"] = {}
        data["features"]["hotkey_enabled"] = config.hotkey_enabled
        data["features"]["images_enabled"] = config.images_enabled
        
        data["settings"] = {}
        data["settings"]["table_width"] = config.table_width
        data["settings"]["column_2"] = config.column_2
        data["settings"]["column_3"] = config.column_3
        data["settings"]["column_4"] = config.column_4
        data["settings"]["hide_missing"] = config.hide_missing
        data["settings"]["hide_stats"] = config.hide_stats
        data["settings"]["auto_average_disabled"] = config.auto_average_disabled
        data["settings"]["curve_bonus_disabled"] = config.curve_bonus_disabled
        data["settings"]["color_bonus_disabled"] = config.color_bonus_disabled
        
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
        print("ResetConfig Error: %s" % error)