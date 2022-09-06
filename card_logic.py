"""This module contains the functions that are used for processing the collected cards"""
from itertools import combinations
from dataclasses import dataclass, asdict
import json
import logging
import math
import numpy
import constants

logic_logger = logging.getLogger(constants.LOG_TYPE_DEBUG)


@dataclass
class Metrics:
    mean: float = 0.0
    standard_deviation: float = 0.0


@dataclass
class DeckType:
    """This class holds the data for the various deck types (Aggro, Mid, and Control)"""
    distribution: list
    maximum_card_count: int
    recommended_creature_count: int
    cmc_average: float


@dataclass
class Config:
    """This class holds the data that's stored in the config.json file"""
    table_width: int = 270
    column_2: str = constants.COLUMNS_OPTIONS_MAIN_DICT[constants.COLUMN_2_DEFAULT]
    column_3: str = constants.COLUMNS_OPTIONS_MAIN_DICT[constants.COLUMN_3_DEFAULT]
    column_4: str = constants.COLUMNS_OPTIONS_MAIN_DICT[constants.COLUMN_4_DEFAULT]
    column_5: str = constants.COLUMNS_OPTIONS_EXTRA_DICT[constants.COLUMN_5_DEFAULT]
    column_6: str = constants.COLUMNS_OPTIONS_EXTRA_DICT[constants.COLUMN_6_DEFAULT]
    column_7: str = constants.COLUMNS_OPTIONS_EXTRA_DICT[constants.COLUMN_7_DEFAULT]
    deck_filter: str = constants.DECK_FILTER_DEFAULT
    filter_format: str = constants.DECK_FILTER_FORMAT_COLORS
    result_format: str = constants.RESULT_FORMAT_WIN_RATE
    card_colors_enabled: bool = False
    missing_enabled: bool = True
    stats_enabled: bool = False
    hotkey_enabled: bool = True
    images_enabled: bool = True
    auto_highest_enabled: bool = True
    curve_bonus_enabled: bool = False
    color_bonus_enabled: bool = False
    bayesian_average_enabled: bool = False
    draft_log_enabled: bool = False
    color_identity_enabled: bool = False
    taken_alsa_enabled: bool = False
    taken_ata_enabled: bool = False
    taken_gpwr_enabled: bool = False
    taken_ohwr_enabled: bool = False
    taken_gdwr_enabled: bool = False
    taken_gndwr_enabled: bool = False
    taken_iwd_enabled: bool = False
    minimum_creatures: int = 13
    minimum_noncreatures: int = 6
    ratings_threshold: int = 500
    alsa_weight: float = 0.0
    iwd_weight: float = 0.0

    deck_mid: DeckType = DeckType([0, 0, 4, 3, 2, 1, 0], 23, 15, 3.04)
    deck_aggro: DeckType = DeckType([0, 2, 5, 3, 0, 0, 0], 24, 17, 2.40)
    deck_control: DeckType = DeckType([0, 0, 3, 3, 3, 1, 1], 22, 14, 3.68)

    database_size: int = 0


class CardResult:
    """This class processes a card list and produces results based on a list of fields (i.e., ALSA, GIHWR, COLORS, etc.)"""

    def __init__(self, set_metrics, tier_data, configuration, pick_number):
        self.metrics = set_metrics
        self.tier_data = tier_data
        self.configuration = configuration
        self.pick_number = pick_number

    def return_results(self, card_list, colors, fields):
        """This function processes a card list and returns a list with the requested field results"""
        return_list = []
        wheel_sum = 0
        if constants.DATA_FIELD_WHEEL in fields.values():
            wheel_sum = self._retrieve_wheel_sum(card_list)

        for card in card_list:
            try:
                selected_card = card
                selected_card["results"] = ["NA"] * len(fields)

                for count, option in enumerate(fields.values()):
                    if constants.FILTER_OPTION_TIER in option:
                        selected_card["results"][count] = self._process_tier(
                            card, option)
                    elif option == constants.DATA_FIELD_COLORS:
                        selected_card["results"][count] = self._process_colors(
                            card)
                    elif option == constants.DATA_FIELD_WHEEL:
                        selected_card["results"][count] = self._process_wheel_normalized(
                            card, wheel_sum)
                        #selected_card["results"][count] = self._process_wheel(card)
                    elif option in card:
                        selected_card["results"][count] = card[option]
                    else:
                        selected_card["results"][count] = self._process_filter_fields(
                            card, option, colors)

                return_list.append(selected_card)
            except Exception as error:
                logic_logger.info("return_results error: %s", error)
        return return_list

    def _process_tier(self, card, option):
        """Retrieve tier list rating for this card"""
        result = "NA"
        try:
            card_name = card[constants.DATA_FIELD_NAME].split(" // ")
            if card_name[0] in self.tier_data[option][constants.DATA_SECTION_RATINGS]:
                result = self.tier_data[option][constants.DATA_SECTION_RATINGS][card_name[0]]
        except Exception as error:
            logic_logger.info("_process_tier error: %s", error)

        return result

    def _process_colors(self, card):
        """Retrieve card colors"""
        result = "NA"

        try:
            result = "".join(card[constants.DATA_FIELD_COLORS])
        except Exception as error:
            logic_logger.info("_process_colors error: %s", error)

        return result

    def _retrieve_wheel_sum(self, card_list):
        """Calculate the sum of all wheel percentage values for the card list"""
        total_sum = 0

        for card in card_list:
            total_sum += self._process_wheel(card)

        return total_sum

    def _process_wheel(self, card):
        """Calculate wheel percentage"""
        result = 0

        try:
            if self.pick_number <= len(constants.WHEEL_COEFFICIENTS):
                # 0 is treated as pick 1 for PremierDraft P1P1
                self.pick_number = max(self.pick_number, 1)
                alsa = card[constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_ALSA]
                coefficients = constants.WHEEL_COEFFICIENTS[self.pick_number - 1]
                # Exclude ALSA values below 2
                result = round(numpy.polyval(coefficients, alsa),
                               1) if alsa >= 2 else 0
                result = max(result, 0)
        except Exception as error:
            logic_logger.info("_process_wheel error: %s", error)

        return result

    def _process_wheel_normalized(self, card, total_sum):
        """Calculate the normalized wheel percentage using the sum of all percentages within the card list"""
        result = 0

        try:
            result = self._process_wheel(card)

            result = round((result / total_sum)*100, 1) if total_sum > 0 else 0
        except Exception as error:
            logic_logger.info("_process_wheel_normalized error: %s", error)

        return result

    def _process_filter_fields(self, card, option, colors):
        """Retrieve win rate result based on the application settings"""
        result = "NA"

        try:
            rated_colors = []
            for color in colors:
                if option in card[constants.DATA_FIELD_DECK_COLORS][color]:
                    if (option in constants.WIN_RATE_OPTIONS):
                        rating_data = self._format_win_rate(card,
                                                             option,
                                                             constants.WIN_RATE_FIELDS_DICT[option],
                                                             color)
                        rated_colors.append(rating_data)
                    else:  # Field that's not a win rate (ALSA, IWD, etc)
                        result = card[constants.DATA_FIELD_DECK_COLORS][color][option]
            if rated_colors:
                result = sorted(
                    rated_colors, key=field_process_sort, reverse=True)[0]
        except Exception as error:
            logic_logger.info("_process_filter_fields error: %s", error)

        return result

    def _format_win_rate(self, card, winrate_field, winrate_count, color):
        """The function will return a grade, rating, or win rate depending on the application's Result Format setting"""
        result = 0
        # Produce a result that matches the Result Format setting
        if self.configuration.result_format == constants.RESULT_FORMAT_RATING:
            result = self._card_rating(
                card, winrate_field, winrate_count, color)
        elif self.configuration.result_format == constants.RESULT_FORMAT_GRADE:
            result = self._card_grade(
                card, winrate_field, winrate_count, color)
        else:
            result = calculate_win_rate(card[constants.DATA_FIELD_DECK_COLORS][color][winrate_field],
                                        card[constants.DATA_FIELD_DECK_COLORS][color][winrate_count],
                                        self.configuration.bayesian_average_enabled)

        return result

    def _card_rating(self, card, winrate_field, winrate_count, color):
        """The function will take a card's win rate and calculate a 5-point rating"""
        result = 0
        try:
            winrate = calculate_win_rate(card[constants.DATA_FIELD_DECK_COLORS][color][winrate_field],
                                         card[constants.DATA_FIELD_DECK_COLORS][color][winrate_count],
                                         self.configuration.bayesian_average_enabled)

            deviation_list = list(constants.GRADE_DEVIATION_DICT.values())
            upper_limit = self.metrics.mean + \
                self.metrics.standard_deviation * deviation_list[0]
            lower_limit = self.metrics.mean + \
                self.metrics.standard_deviation * deviation_list[-1]

            if (winrate != 0) and (upper_limit != lower_limit):
                result = round(
                    ((winrate - lower_limit) / (upper_limit - lower_limit)) * 5.0, 1)
                result = min(result, 5.0)
                result = max(result, 0)

        except Exception as error:
            logic_logger.info("_card_rating error: %s", error)
        return result

    def _card_grade(self, card, winrate_field, winrate_count, color):
        """The function will take a card's win rate and assign a letter grade based on the number of standard deviations from the mean"""
        result = constants.LETTER_GRADE_NA
        try:
            winrate = calculate_win_rate(card[constants.DATA_FIELD_DECK_COLORS][color][winrate_field],
                                         card[constants.DATA_FIELD_DECK_COLORS][color][winrate_count],
                                         self.configuration.bayesian_average_enabled)

            if ((winrate != 0) and (self.metrics.standard_deviation != 0)):
                result = constants.LETTER_GRADE_F
                for grade, deviation in constants.GRADE_DEVIATION_DICT.items():
                    standard_score = (
                        winrate - self.metrics.mean) / self.metrics.standard_deviation
                    if standard_score >= deviation:
                        result = grade
                        break

        except Exception as error:
            logic_logger.info("_card_grade error: %s", error)
        return result


def field_process_sort(field_value):
    """This function collects the numeric order of a letter grade for the purpose of sorting"""
    processed_value = field_value

    try:
        if field_value in constants.GRADE_ORDER_DICT:
            processed_value = constants.GRADE_ORDER_DICT[field_value]
    except ValueError:
        pass
    return processed_value


def format_tier_results(value, old_format, new_format):
    """This function converts the tier list ratings, from old tier lists, back to letter grades"""
    new_value = value
    try:
        # ratings to grades
        if (old_format == constants.RESULT_FORMAT_RATING) and (new_format == constants.RESULT_FORMAT_GRADE):
            new_value = constants.LETTER_GRADE_NA
            for grade, threshold in constants.TIER_CONVERSION_RATINGS_GRADES_DICT.items():
                if value > threshold:
                    new_value = grade
                    break
    except Exception as error:
        logic_logger.info("format_tier_results error: %s", error)

    return new_value


def deck_card_search(deck, search_colors, card_types, include_types, include_colorless, include_partial):
    """This function retrieves a subset of cards that meet certain criteria (type, color, etc.)"""
    card_color_sorted = {}
    main_color = ""
    combined_cards = []
    for card in deck:
        try:
            colors = card_colors(card["mana_cost"])

            if not colors:
                colors = card[constants.DATA_FIELD_COLORS]

            if bool(colors) and (set(colors) <= set(search_colors)):
                main_color = colors[0]

                if ((include_types and any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types)) or
                   (not include_types and not any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types))):

                    if main_color not in card_color_sorted:
                        card_color_sorted[main_color] = []

                    card_color_sorted[main_color].append(card)

            elif set(search_colors).intersection(colors) and include_partial:
                for color in colors:
                    if ((include_types and any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types)) or
                       (not include_types and not any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types))):

                        if color not in card_color_sorted:
                            card_color_sorted[color] = []

                        card_color_sorted[color].append(card)

            if not bool(card_colors) and include_colorless:

                if ((include_types and any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types)) or
                   (not include_types and not any(x in card[constants.DATA_FIELD_TYPES][0] for x in card_types))):

                    combined_cards.append(card)
        except Exception as error:
            logic_logger.info("deck_card_search error: %s", error)

    for key, value in card_color_sorted.items():
        if key in search_colors:
            combined_cards.extend(value)

    return combined_cards


def deck_metrics(deck):
    """This function determines the total CMC, count, and distribution of a collection of cards"""
    cmc_total = 0
    count = len(deck)
    distribution = [0, 0, 0, 0, 0, 0, 0]

    try:
        for card in deck:
            cmc_total += card[constants.DATA_FIELD_CMC]
            index = int(
                min(card[constants.DATA_FIELD_CMC], len(distribution) - 1))
            distribution[index] += 1

    except Exception as error:
        logic_logger.info("deck_metrics error: %s", error)

    return cmc_total, count, distribution


def option_filter(deck, option_selection, metrics, configuration):
    """This function returns a list of colors based on the deck filter option"""
    filtered_color_list = [option_selection]
    try:
        if constants.FILTER_OPTION_AUTO in option_selection:
            filtered_color_list = auto_colors(deck, 2, metrics, configuration)
        else:
            filtered_color_list = [option_selection]
    except Exception as error:
        logic_logger.info("option_filter error: %s", error)
    return filtered_color_list


def deck_colors(deck, colors_max, metrics, configuration):
    """This function determines the prominent colors for a collection of cards"""
    colors_result = {}
    try:
        colors = calculate_color_affinity(
            deck, constants.FILTER_OPTION_ALL_DECKS, metrics.mean, configuration)

        # Modify the dictionary to include ratings
        color_list = list(
            map((lambda x: {"color": x, "rating": colors[x]}), colors.keys()))

        # Sort the list by decreasing ratings
        color_list = sorted(
            color_list, key=lambda k: k["rating"], reverse=True)

        # Remove extra colors beyond limit
        color_list = color_list[0:3]

        # Return colors
        sorted_colors = list(map((lambda x: x["color"]), color_list))

        # Create color permutation
        color_combination = []

        for count in range(colors_max + 1):
            if count > 1:
                color_combination.extend(combinations(sorted_colors, count))
            else:
                color_combination.extend((sorted_colors))

        # Convert tuples to list of strings
        color_strings = [''.join(tups) for tups in color_combination]
        color_strings = [x for x in color_strings if len(x) <= colors_max]

        color_strings = list(set(color_strings))

        color_dict = {}
        for color_string in color_strings:
            for color in color_string:
                if color_string not in color_dict:
                    color_dict[color_string] = 0
                color_dict[color_string] += colors[color]

        for color_option in constants.DECK_COLORS:
            for key, value in color_dict.items():
                if (len(key) == len(color_option)) and set(key).issubset(color_option):
                    colors_result[color_option] = value

        colors_result = dict(
            sorted(colors_result.items(), key=lambda item: item[1], reverse=True))

    except Exception as error:
        logic_logger.info("deck_colors error: %s", error)

    return colors_result


def auto_colors(deck, colors_max, metrics, configuration):
    """When the Auto deck filter is selected, this function identifies the prominent color pairs from the collected cards"""
    try:
        deck_colors_list = [constants.FILTER_OPTION_ALL_DECKS]
        colors_dict = {}
        deck_length = len(deck)
        if deck_length > 15:
            colors_dict = deck_colors(deck, colors_max, metrics, configuration)
            colors = list(colors_dict.keys())
            auto_select_threshold = 30 - deck_length
            if (len(colors) > 1) and ((colors_dict[colors[0]] - colors_dict[colors[1]]) > auto_select_threshold):
                deck_colors_list = colors[0:1]
            elif len(colors) == 1:
                deck_colors_list = colors[0:1]
            elif configuration.auto_highest_enabled:
                deck_colors_list = colors[0:2]

    except Exception as error:
        logic_logger.info("auto_colors error: %s", error)

    return deck_colors_list


def calculate_color_affinity(deck_cards, color_filter, threshold, configuration):
    """This function identifies the main deck colors based on the GIHWR of the collected cards"""
    colors = {}

    for card in deck_cards:
        try:
            gihwr = calculate_win_rate(card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIHWR],
                                       card[constants.DATA_FIELD_DECK_COLORS][color_filter][constants.DATA_FIELD_GIH],
                                       configuration.bayesian_average_enabled)
            if gihwr > threshold:
                for color in card[constants.DATA_FIELD_COLORS]:
                    if color not in colors:
                        colors[color] = 0
                    colors[color] += (gihwr - threshold)
        except Exception as error:
            logic_logger.info("calculate_color_affinity error: %s", error)
    return colors


def row_color_tag(colors):
    """This function selects"""
    row_tag = constants.CARD_ROW_COLOR_GOLD_TAG
    if len(colors) > 1:
        row_tag = constants.CARD_ROW_COLOR_GOLD_TAG
    elif constants.CARD_COLOR_SYMBOL_RED in colors:
        row_tag = constants.CARD_ROW_COLOR_RED_TAG
    elif constants.CARD_COLOR_SYMBOL_BLUE in colors:
        row_tag = constants.CARD_ROW_COLOR_BLUE_TAG
    elif constants.CARD_COLOR_SYMBOL_BLACK in colors:
        row_tag = constants.CARD_ROW_COLOR_BLACK_TAG
    elif constants.CARD_COLOR_SYMBOL_WHITE in colors:
        row_tag = constants.CARD_ROW_COLOR_WHITE_TAG
    elif constants.CARD_COLOR_SYMBOL_GREEN in colors:
        row_tag = constants.CARD_ROW_COLOR_GREEN_TAG
    return row_tag


def calculate_mean(cards, bayesian_enabled):
    """The function calculates the mean win rate of a collection of cards"""
    card_count = 0
    card_sum = 0
    mean = 0
    for card in cards:
        try:
            winrate = calculate_win_rate(cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIHWR],
                                         cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIH],
                                         bayesian_enabled)

            if winrate == 0:
                continue

            card_sum += winrate
            card_count += 1

        except Exception as error:
            logic_logger.info("calculate_mean error: %s", error)

    mean = float(card_sum / card_count) if card_count else 0

    return mean


def calculate_standard_deviation(cards, mean, bayesian_enabled):
    """The function calculates the standard deviation from the win rate of a collection of cards"""
    standard_deviation = 0
    card_count = 0
    sum_squares = 0
    for card in cards:
        try:
            winrate = calculate_win_rate(cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIHWR],
                                         cards[card][constants.DATA_FIELD_DECK_COLORS][constants.FILTER_OPTION_ALL_DECKS][constants.DATA_FIELD_GIH],
                                         bayesian_enabled)

            if winrate == 0:
                continue

            squared_deviations = (winrate - mean) ** 2

            sum_squares += squared_deviations
            card_count += 1

        except Exception as error:
            logic_logger.info("calculate_standard_deviation error: %s", error)

    # Find the variance
    variance = (sum_squares / (card_count - 1)) if card_count > 2 else 0

    standard_deviation = math.sqrt(variance)

    return standard_deviation


def ratings_limits(cards, bayesian_enabled):
    """The function identifies the upper and lower win rates from a collection of cards"""
    upper_limit = 0
    lower_limit = 100

    for card in cards:
        for color in constants.DECK_COLORS:
            try:
                if color in cards[card][constants.DATA_FIELD_DECK_COLORS]:
                    gihwr = calculate_win_rate(cards[card][constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR],
                                               cards[card][constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIH],
                                               bayesian_enabled)
                    if gihwr > upper_limit:
                        upper_limit = gihwr
                    if gihwr < lower_limit and gihwr != 0:
                        lower_limit = gihwr
            except Exception as error:
                logic_logger.info("ratings_limits error: %s", error)

    return upper_limit, lower_limit


def calculate_win_rate(winrate, count, bayesian_enabled):
    """The function will modify a card's win rate by applying the Bayesian Average algorithm or by zeroing a value with a low sample size"""
    calculated_winrate = 0.0
    try:
        calculated_winrate = winrate

        if bayesian_enabled:
            win_count = winrate * count
            # Bayesian average calculation
            calculated_winrate = (win_count + 1000) / (count + 20)
            calculated_winrate = round(calculated_winrate, 2)
        else:
            # Drop values that have fewer than 200 samples (same as 17Lands card_ratings page)
            if count < 200:
                calculated_winrate = 0.0
    except Exception as error:
        logic_logger.info("calculate_win_rate error: %s", error)
    return calculated_winrate


def deck_color_stats(deck, color):
    """The function will identify the number of creature and noncreature cards in a collection of cards"""
    creature_count = 0
    noncreature_count = 0

    try:
        creature_cards = deck_card_search(
            deck, color, constants.CARD_TYPE_DICT[constants.CARD_TYPE_SELECTION_CREATURES], True, True, False)
        noncreature_cards = deck_card_search(
            deck, color, constants.CARD_TYPE_DICT[constants.CARD_TYPE_SELECTION_CREATURES], False, True, False)

        creature_count = len(creature_cards)
        noncreature_count = len(noncreature_cards)

    except Exception as error:
        logic_logger.info("deck_color_stats error: %s", error)

    return creature_count, noncreature_count


def card_cmc_search(deck, offset, starting_cmc, cmc_limit, remaining_count):
    """The function will use recursion to search through a collection of cards and produce a list of cards with a mean CMC that is below a specific limit"""
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
                    cards, skipped = card_cmc_search(
                        deck, current_offset, card_cmc, cmc_limit, current_remaining)
                    if cards:
                        cards.append(card)
                        unused.extend(skipped)
                        break
                    else:
                        unused.append(card)
            else:
                unused.append(card)
    except Exception as error:
        logic_logger.info("card_cmc_search error: %s", error)

    return cards, unused


def deck_rating(deck, deck_type, color, threshold, bayesian_enabled):
    """The function will produce a deck rating based on the combined GIHWR value for each card with a GIHWR value above a certain threshold"""
    rating = 0
    try:
        # Combined GIHWR of the cards
        for card in deck:
            try:
                gihwr = calculate_win_rate(card[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR],
                                           card[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIH],
                                           bayesian_enabled)
                if gihwr > threshold:
                    rating += gihwr
            except Exception:
                pass
        # Deck contains the recommended number of creatures
        recommended_creature_count = deck_type.recommended_creature_count
        filtered_cards = deck_card_search(
            deck, color, constants.CARD_TYPE_DICT[constants.CARD_TYPE_SELECTION_CREATURES], True, True, False)

        if len(filtered_cards) < recommended_creature_count:
            rating -= (recommended_creature_count - len(filtered_cards)) * 100

        # Average CMC of the creatures is below the ideal cmc average
        cmc_average = deck_type.cmc_average
        total_cards = len(filtered_cards)
        total_cmc = 0

        for card in filtered_cards:
            total_cmc += card[constants.DATA_FIELD_CMC]

        cmc = total_cmc / total_cards

        if cmc > cmc_average:
            rating -= 500

        # Cards fit distribution
        minimum_distribution = deck_type.distribution
        distribution = [0, 0, 0, 0, 0, 0, 0]
        for card in filtered_cards:
            index = int(min(card[constants.DATA_FIELD_CMC],
                        len(minimum_distribution) - 1))
            distribution[index] += 1

        for index, value in enumerate(distribution):
            if value < minimum_distribution[index]:
                rating -= 100

    except Exception as error:
        logic_logger.info("deck_rating error: %s", error)

    rating = int(rating)
    
    return rating


def copy_deck(deck, sideboard):
    """The function will produce a deck/sideboard list that is formatted in such a way that it can be copied to Arena and Sealdeck.tech"""
    deck_copy = ""
    try:
        # Copy Deck
        deck_copy = "Deck\n"
        # identify the arena_id for the cards
        for card in deck:
            deck_copy += f"{card[constants.DATA_FIELD_COUNT]} {card[constants.DATA_FIELD_NAME]}\n"

        # Copy sideboard
        if sideboard is not None:
            deck_copy += "\nSideboard\n"
            for card in sideboard:
                deck_copy += f"{card[constants.DATA_FIELD_COUNT]} {card[constants.DATA_FIELD_NAME]}\n"

    except Exception as error:
        logic_logger.info("copy_deck error: %s", error)

    return deck_copy


def stack_cards(cards):
    """The function will produce a list consisting of unique cards and the number of copies of each card"""
    deck = {}
    deck_list = []
    for card in cards:
        try:
            name = card[constants.DATA_FIELD_NAME]
            if name not in deck:
                deck[name] = {constants.DATA_FIELD_COUNT: 1}
                for field in constants.DATA_SET_FIELDS:
                    if field in card:
                        deck[name][field] = card[field]
            else:
                deck[name][constants.DATA_FIELD_COUNT] += 1
        except Exception as error:
            logic_logger.info("stack_cards error: %s", error)
    # Convert to list format
    deck_list = list(deck.values())

    return deck_list


def card_colors(mana_cost):
    """The function parses a mana cost string and returns a list of mana symbols"""
    colors = []
    try:
        if constants.CARD_COLOR_SYMBOL_BLACK in mana_cost:
            colors.append(constants.CARD_COLOR_SYMBOL_BLACK)

        if constants.CARD_COLOR_SYMBOL_GREEN in mana_cost:
            colors.append(constants.CARD_COLOR_SYMBOL_GREEN)

        if constants.CARD_COLOR_SYMBOL_RED in mana_cost:
            colors.append(constants.CARD_COLOR_SYMBOL_RED)

        if constants.CARD_COLOR_SYMBOL_BLUE in mana_cost:
            colors.append(constants.CARD_COLOR_SYMBOL_BLUE)

        if constants.CARD_COLOR_SYMBOL_WHITE in mana_cost:
            colors.append(constants.CARD_COLOR_SYMBOL_WHITE)
    except Exception as error:
        logic_logger.info("card_colors error: %s", error)
    return colors


def color_splash(cards, colors, splash_threshold, configuration):
    """The function will parse a list of cards to determine if there are any cards that might justify a splash"""
    color_affinity = {}
    splash_color = ""
    try:
        # Calculate affinity to rank colors based on splash threshold (minimum GIHWR)
        color_affinity = calculate_color_affinity(
            cards, colors, splash_threshold, configuration)

        # Modify the dictionary to include ratings
        color_affinity = list(
            map((lambda x: {"color": x, "rating": color_affinity[x]}), color_affinity.keys()))
        # Remove the current colors
        filtered_colors = color_affinity[:]
        for color in color_affinity:
            if color["color"] in colors:
                filtered_colors.remove(color)
        # Sort the list by decreasing ratings
        filtered_colors = sorted(
            filtered_colors, key=lambda k: k["rating"], reverse=True)

        if filtered_colors:
            splash_color = filtered_colors[0]["color"]
    except Exception as error:
        logic_logger.info("color_splash error: %s", error)
    return splash_color


def mana_base(deck):
    """The function will identify the number of lands that are needed to fill out a deck"""
    maximum_deck_size = 40
    combined_deck = []
    mana_types = {"Swamp": {"color": constants.CARD_COLOR_SYMBOL_BLACK, constants.DATA_FIELD_COUNT: 0},
                  "Forest": {"color": constants.CARD_COLOR_SYMBOL_GREEN, constants.DATA_FIELD_COUNT: 0},
                  "Mountain": {"color": constants.CARD_COLOR_SYMBOL_RED, constants.DATA_FIELD_COUNT: 0},
                  "Island": {"color": constants.CARD_COLOR_SYMBOL_BLUE, constants.DATA_FIELD_COUNT: 0},
                  "Plains": {"color": constants.CARD_COLOR_SYMBOL_WHITE, constants.DATA_FIELD_COUNT: 0}}
    total_count = 0
    try:
        number_of_lands = 0 if maximum_deck_size < len(
            deck) else maximum_deck_size - len(deck)

        # Go through the cards and count the mana types
        for card in deck:
            mana_types["Swamp"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count(
                constants.CARD_COLOR_SYMBOL_BLACK)
            mana_types["Forest"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count(
                constants.CARD_COLOR_SYMBOL_GREEN)
            mana_types["Mountain"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count(
                constants.CARD_COLOR_SYMBOL_RED)
            mana_types["Island"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count(
                constants.CARD_COLOR_SYMBOL_BLUE)
            mana_types["Plains"][constants.DATA_FIELD_COUNT] += card["mana_cost"].count(
                constants.CARD_COLOR_SYMBOL_WHITE)

        for land in mana_types.values():
            total_count += land[constants.DATA_FIELD_COUNT]

        # Sort by lowest count
        mana_types = dict(
            sorted(mana_types.items(), key=lambda t: t[1]['count']))
        # Add x lands with a distribution set by the mana types
        for land in mana_types:
            if (mana_types[land][constants.DATA_FIELD_COUNT] == 1) and (number_of_lands > 1):
                land_count = 1
                number_of_lands -= 1
            else:
                land_count = int(round(
                    (mana_types[land][constants.DATA_FIELD_COUNT] / total_count) * number_of_lands, 0))
                # Minimum of 2 lands for a  splash
                if (land_count == 1) and (number_of_lands > 1):
                    land_count = 2
                    number_of_lands -= 1

            if mana_types[land][constants.DATA_FIELD_COUNT] != 0:
                card = {constants.DATA_FIELD_COLORS: mana_types[land]["color"],
                        constants.DATA_FIELD_TYPES: constants.CARD_TYPE_LAND,
                        constants.DATA_FIELD_CMC: 0,
                        constants.DATA_FIELD_NAME: land,
                        constants.DATA_FIELD_COUNT: land_count}
                combined_deck.append(card)

    except Exception as error:
        logic_logger.info("mana_base error: %s", error)
    return combined_deck


def suggest_deck(taken_cards, metrics, configuration):
    """The function will analyze the list of taken cards and produce several viable decks based on specific criteria"""
    colors_max = 3
    maximum_card_count = 23
    sorted_decks = {}
    try:
        deck_types = {"Mid": configuration.deck_mid,
                      "Aggro": configuration.deck_aggro, "Control": configuration.deck_control}
        # Identify the top color combinations
        colors = deck_colors(taken_cards, colors_max, metrics, configuration)
        colors = colors.keys()
        filtered_colors = []

        # Collect color stats and remove colors that don't meet the minimum requirements
        for color in colors:
            creature_count, noncreature_count = deck_color_stats(
                taken_cards, color)
            if ((creature_count >= configuration.minimum_creatures) and
               (noncreature_count >= configuration.minimum_noncreatures) and
               (creature_count + noncreature_count >= maximum_card_count)):
                filtered_colors.append(color)

        decks = {}
        for color in filtered_colors:
            for key, value in deck_types.items():
                deck, sideboard_cards = build_deck(
                    value, taken_cards, color, metrics, configuration)
                rating = deck_rating(
                    deck, value, color, metrics.mean, configuration.bayesian_average_enabled)
                if rating >= configuration.ratings_threshold:

                    if ((color not in decks) or
                            (color in decks and rating > decks[color]["rating"])):
                        decks[color] = {}
                        decks[color]["deck_cards"] = stack_cards(deck)
                        decks[color]["sideboard_cards"] = stack_cards(
                            sideboard_cards)
                        decks[color]["rating"] = rating
                        decks[color]["type"] = key
                        decks[color]["deck_cards"].extend(mana_base(deck))

        sorted_colors = sorted(
            decks, key=lambda x: decks[x]["rating"], reverse=True)
        for color in sorted_colors:
            sorted_decks[color] = decks[color]
    except Exception as error:
        logic_logger.info("suggest_deck error: %s", error)

    return sorted_decks


def build_deck(deck_type, cards, color, metrics, configuration):
    """The function will build a deck list that meets specific criteria"""
    minimum_distribution = deck_type.distribution
    maximum_card_count = deck_type.maximum_card_count
    maximum_deck_size = 40
    cmc_average = deck_type.cmc_average
    recommended_creature_count = deck_type.recommended_creature_count
    used_list = []
    sideboard_list = cards[:]  # Copy by value
    try:
        for card in cards:
            card["results"] = [calculate_win_rate(card[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIHWR],
                                                  card[constants.DATA_FIELD_DECK_COLORS][color][constants.DATA_FIELD_GIH],
                                                  configuration.bayesian_average_enabled)]

        # identify a splashable color
        splash_threshold = metrics.mean + \
            2.33 * metrics.standard_deviation
        color += (color_splash(cards, color, splash_threshold, configuration))

        card_colors_sorted = deck_card_search(
            cards, color, constants.CARD_TYPE_DICT[constants.CARD_TYPE_SELECTION_CREATURES], True, True, False)
        card_colors_sorted = sorted(
            card_colors_sorted, key=lambda k: k["results"][0], reverse=True)

        # Identify creatures that fit distribution
        distribution = [0, 0, 0, 0, 0, 0, 0]
        unused_list = []
        used_list = []
        used_count = 0
        used_cmc_combined = 0
        for card in card_colors_sorted:
            index = int(min(card[constants.DATA_FIELD_CMC],
                        len(minimum_distribution) - 1))
            if distribution[index] < minimum_distribution[index]:
                used_list.append(card)
                distribution[index] += 1
                used_count += 1
                used_cmc_combined += card[constants.DATA_FIELD_CMC]
            else:
                unused_list.append(card)

        # Go back and identify remaining creatures that have the highest base rating but don't push average above the threshold
        unused_cmc_combined = cmc_average * recommended_creature_count - used_cmc_combined

        unused_list.sort(key=lambda x: x["results"][0], reverse=True)

        # Identify remaining cards that won't exceed recommeneded CMC average
        cmc_cards, unused_list = card_cmc_search(
            unused_list, 0, 0, unused_cmc_combined, recommended_creature_count - used_count)
        used_list.extend(cmc_cards)

        total_card_count = len(used_list)

        temp_unused_list = unused_list[:]
        if len(cmc_cards) == 0:
            for card in unused_list:
                if total_card_count >= recommended_creature_count:
                    break

                used_list.append(card)
                temp_unused_list.remove(card)
                total_card_count += 1
        unused_list = temp_unused_list[:]

        card_colors_sorted = deck_card_search(cards, color, [
            constants.CARD_TYPE_INSTANT, constants.CARD_TYPE_SORCERY, constants.CARD_TYPE_ENCHANTMENT, constants.CARD_TYPE_ARTIFACT], True, True, False)
        card_colors_sorted = sorted(
            card_colors_sorted, key=lambda k: k["results"][0], reverse=True)
        # Add non-creature cards
        for card in card_colors_sorted:
            if total_card_count >= maximum_card_count:
                break

            used_list.append(card)
            total_card_count += 1

        # Fill the deck with remaining creatures
        for card in unused_list:
            if total_card_count >= maximum_card_count:
                break

            used_list.append(card)
            total_card_count += 1

        # Add in special lands if they are on-color, off-color, and they have a card rating above 2.0
        land_cards = deck_card_search(
            cards, color, [constants.CARD_TYPE_LAND], True, True, False)
        land_cards = [
            x for x in land_cards if x[constants.DATA_FIELD_NAME] not in constants.BASIC_LANDS]
        land_cards = sorted(
            land_cards, key=lambda k: k["results"][0], reverse=True)
        for card in land_cards:
            if total_card_count >= maximum_deck_size:
                break

            if card["results"][0] >= metrics.mean:
                used_list.append(card)
                total_card_count += 1

        # Identify sideboard cards:
        for card in used_list:
            try:
                sideboard_list.remove(card)
            except Exception as error:
                logic_logger.info("%s error: %s",
                                  card[constants.DATA_FIELD_NAME], error)
                logic_logger.info("Sideboard %s error: %s",
                                  {card['name']}, error)
    except Exception as error:
        logic_logger.info("build_deck error: %s", error)
    return used_list, sideboard_list


def read_config():
    """The function will retrieve settings values from a configuration file"""
    config = Config()
    try:
        with open("config.json", 'r', encoding="utf8") as data:
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
        config.taken_alsa_enabled = config_data["settings"]["taken_alsa_enabled"]
        config.taken_ata_enabled = config_data["settings"]["taken_ata_enabled"]
        config.taken_gpwr_enabled = config_data["settings"]["taken_gpwr_enabled"]
        config.taken_ohwr_enabled = config_data["settings"]["taken_ohwr_enabled"]
        config.taken_iwd_enabled = config_data["settings"]["taken_iwd_enabled"]
        config.taken_gdwr_enabled = config_data["settings"]["taken_gdwr_enabled"]
        config.taken_gndwr_enabled = config_data["settings"]["taken_gndwr_enabled"]
        config.card_colors_enabled = config_data["settings"]["card_colors_enabled"]
        config.bayesian_average_enabled = config_data["settings"]["bayesian_average_enabled"]
        config.draft_log_enabled = config_data["settings"]["draft_log_enabled"]
        config.color_identity_enabled = config_data["settings"]["color_identity_enabled"]
    except Exception as error:
        logic_logger.info("read_config error: %s", error)
    return config


def write_config(config):
    """The function will write configuration values to a configuration file"""
    try:
        with open("config.json", 'r', encoding="utf8") as data:
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
        config_data["settings"]["taken_alsa_enabled"] = config.taken_alsa_enabled
        config_data["settings"]["taken_ata_enabled"] = config.taken_ata_enabled
        config_data["settings"]["taken_gpwr_enabled"] = config.taken_gpwr_enabled
        config_data["settings"]["taken_ohwr_enabled"] = config.taken_ohwr_enabled
        config_data["settings"]["taken_gdwr_enabled"] = config.taken_gdwr_enabled
        config_data["settings"]["taken_gndwr_enabled"] = config.taken_gndwr_enabled
        config_data["settings"]["taken_iwd_enabled"] = config.taken_iwd_enabled
        config_data["settings"]["card_colors_enabled"] = config.card_colors_enabled
        config_data["settings"]["bayesian_average_enabled"] = config.bayesian_average_enabled
        config_data["settings"]["draft_log_enabled"] = config.draft_log_enabled
        config_data["settings"]["color_identity_enabled"] = config.color_identity_enabled

        with open('config.json', 'w', encoding='utf-8') as file:
            json.dump(config_data, file, ensure_ascii=False, indent=4)

    except Exception as error:
        logic_logger.info("write_config error: %s", error)


def reset_config():
    """The function will reset the application's configuration values back to the hard-coded default values"""
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
        data["settings"]["taken_alsa_enabled"] = config.taken_alsa_enabled
        data["settings"]["taken_ata_enabled"] = config.taken_ata_enabled
        data["settings"]["taken_gpwr_enabled"] = config.taken_gpwr_enabled
        data["settings"]["taken_ohwr_enabled"] = config.taken_ohwr_enabled
        data["settings"]["taken_gdwr_enabled"] = config.taken_gdwr_enabled
        data["settings"]["taken_gndwr_enabled"] = config.taken_gndwr_enabled
        data["settings"]["taken_iwd_enabled"] = config.taken_iwd_enabled
        data["settings"]["card_colors_enabled"] = config.card_colors_enabled
        data["settings"]["color_identity_enabled"] = config.color_identity_enabled

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
        data["card_logic"]["deck_types"]["Control"] = asdict(
            config.deck_control)

        with open('config.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as error:
        logic_logger.info("reset_config error: %s", error)
