import itertools
import re

KEY_TO_ATTR_MAPPING = {
    '5': 'projectNumber',
    '900': 'stationName',
    '12': 'stationName',
    '802': 'siteTypeCode',
    '6': 'districtCode',
    '41': 'countryCode',
    '7': 'stateFipsCode',
    '8': 'countyCode',
    '42': 'minorCivilDivisionCode',
    '9': 'latitude',
    '10': 'longitude',
    '11': 'coordinateAccuracyCode',
    '35': 'coordinateMethodCode',
    '36': 'coordinateDatumCode',
    '16': 'altitude',
    '18': 'altitudeAccuracyValue',
    '17': 'altitudeMethodCode',
    '22': 'altitudeDatumCode',
    '13': 'landNet',
    '19': 'topographicCode',
    '20': 'hydrologicUnitCode',
    '801': 'basinCode',
    '813': 'timeZoneCode',
    '814': 'daylightSavingsTimeFlag',
    '14': 'mapName',
    '15': 'mapScale',
    '803': 'agencyUseCode',
    '39': 'nationalWaterUseCode',
    '804': 'dataTypesCode',
    '805': 'instrumentsCode',
    '711': 'siteEstablishmentDate',
    '806': 'remarks',
    '32': 'siteWebReadyCode',
    '3': 'dataReliabilityCode',
    '21': 'firstConstructionDate',
    '23': 'primaryUseOfSiteCode',
    '301': 'secondaryUseOfSiteCode',
    '302': 'tertiaryUseOfSiteCode',
    '24': 'primaryUseOfWaterCode',
    '25': 'secondaryUseOfWaterCode',
    '26': 'tertiaryUseOfWaterCode',
    '713': 'aquiferTypeCode',
    '714': 'aquiferCode',
    '715': 'nationalAquiferCode',
    '27': 'holeDepth',
    '28': 'wellDepth',
    '29': 'sourceOfDepthCode',
    '808': 'drainageArea',
    '809': 'contributingDrainageArea',
    '712': 'gwFileCode',
    'R': 'databaseTableIdentifier',
    'T': 'transactionType'
}

DATABASE_TABLE_ID_TOKEN = 'R='

MAX_TRANSACTIONS = 30000

class ParseError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'ParseError, message: {0}'.format(self.message)


def get_lines(content):
    """
    :param str content:
    :rtype: list of str
    :return: List of lines within content that contain ddot data
    :raises ParseError if any of the lines fail line validation
    """
    if not content:
        raise ParseError('No contents found')
    # Handles lines ending with carriage return-linefeed as well as just a linefeed
    lines = re.split('\r\n|\n', content)[1:]

    if not lines:
        raise ParseError('No transactions found')

    # Remove trailing line feed
    if not lines[len(lines) - 1]:
        lines = lines[0:len(lines) - 1]

    validation_errors = validate_lines(lines)

    if len(validation_errors) > 0:
        raise ParseError(validation_errors)
    
    return lines

def validate_lines(lines):
    """
    :param list of str lines:
    :rtype: list of dicts for each location in content
    :return: Returns a string containing any validation errors (lines with 
    length > 80, with length < 21, and with invalid site numbers - no space 
    in position 21). An empty string indicates successful validation.
    """
    too_long_lines = []
    too_short_lines = []
    bad_site_lines = []
    error_message = ""
    for index, line in enumerate(lines):
        if len(line) > 80:
            too_long_lines.append(index + 2)
        elif len(line) < 21:
            too_short_lines.append(index + 2)
        elif line[20] != ' ':
            bad_site_lines.append(index + 2)

    if too_long_lines:
        error_message += "Contains lines exceeding 80 characters: lines {0}. ".format(', '.join([str(line) for line in too_long_lines]))

    if too_short_lines:
        error_message += "Contains lines with an invalid agency code / site number format (fewer than 21 characters): lines {0}. ".format(', '.join([str(line) for line in too_short_lines]))
    
    if bad_site_lines:
        error_message += "Contains lines with invalid site number format: lines {0}. ".format(', '.join([str(line) for line in bad_site_lines]))
        
    return error_message

def get_transactions(lines):
    """
    :param list of str lines:
    :rtype: list of dicts for each location in content
    :return: Returns a list of dictionaries. Each dictionary has four properties:
        agencyCode contains a string agency code, siteNumber contains the string site number,
        key_value_pairs' returns all of the key value pairs concatenated for the location, and
        'line_numbers returns the line numbers that this transaction appears in the ddot file.
    """

    # line indexes are incremented by two to account for the intro line and that the array starts at zero
    parsed_lines = [(line[0:20], line[21:], index + 2) for index, line in enumerate(lines)]
    result = []

    for location, location_group in itertools.groupby(parsed_lines, lambda x: x[0]):
        line_numbers = []
        key_value_pairs = []
        for line in location_group:
            # This checks to see if a new transaction on the same site has been detected
            if DATABASE_TABLE_ID_TOKEN == line[1][0:2] and key_value_pairs:
                transaction = {
                    'agencyCode': location[0:5],
                    'siteNumber': location[5:20],
                    'key_value_pairs': ' '.join(key_value_pairs),
                    'line_numbers': line_numbers
                }
                result.append(transaction)
                line_numbers = []
                key_value_pairs = []

            key_value_pairs.append(line[1])
            line_numbers.append(line[2])
        transaction = {
            'agencyCode': location[0:5],
            'siteNumber': location[5:20],
            'key_value_pairs': ' '.join(key_value_pairs),
            'line_numbers': line_numbers
        }
        result.append(transaction)

    return result


def parse_key_value_pairs(kv_pairs_str):
    """
    :param kv_pairs_str:
    :return:list of tuples with the form [(d.Code, value)...]
    :raises ParseError if the string does not contain valid key value pairs. Possible errors
        include not finding a separator token or not finding an ending token
    """

    SEPARATOR_TOKENS = re.compile('[=#]')
    VALUE_ENDING_TOKENS = re.compile('[\*\$]\s*')

    test_string = kv_pairs_str
    result = []
    if not kv_pairs_str:
        raise ParseError('No key value pairs found')

    while test_string:
        separator_match = SEPARATOR_TOKENS.search(test_string)
        if not separator_match:
            raise ParseError('Incomplete key value pair with no separator in {0}'.format(test_string))

        key = test_string[0:separator_match.start()]
        value_ending_match = VALUE_ENDING_TOKENS.search(test_string)
        if value_ending_match:
            value = test_string[separator_match.end():value_ending_match.start()]
        else:
            raise ParseError('Could not find value ending token in {0}'.format(test_string))
        result.append((key, value))

        test_string = test_string[value_ending_match.end():]

    return result


def has_duplicate_station_name_keys(kv_pairs):
    """
    :param list of tuples kv_pairs:
    :return: Boolean
    """
    found = False
    has_duplicate = False
    for (key, value) in kv_pairs:
        if KEY_TO_ATTR_MAPPING.get(key) == 'stationName':
            if found:
                has_duplicate = True
                break
            else:
                found = True
    return has_duplicate


def has_transaction_type(kv_pairs):
    """
    :param list of tuples kv_pairs:
    :return: Boolean
    """
    return 1 == len([key for (key, value) in kv_pairs if key == 'T'])


def invalid_key_codes(kv_pairs):
    """
        :param list of tuples kv_pairs:
        :return: tuple of invalid codes
    """
    return [key for (key, value) in kv_pairs if key not in KEY_TO_ATTR_MAPPING]


def translate_keys_to_attributes(kv_pairs):
    """
    :param list of tuples kv_pairs:
    :return: dict
    """
    result = {KEY_TO_ATTR_MAPPING.get(key): value for (key, value) in kv_pairs if key in KEY_TO_ATTR_MAPPING}
    return result


def remove_leading_and_trailing_single_quotes(value):
    """
    :param str value:
    :return: str: Returns value unless the first and last characters are single quotes, then it removes the single
        quotes and returns the resulting string.
    """
    if value.startswith('\'') and value.endswith('\''):
        result = value[1:len(value) - 1]
    else:
        result = value
    return result

def update_c_code_to_y_code(value):
    """
    :param str value:
    :return: str: Returns value unless value is a 'C', then returns a 'Y'.
    """
    result = 'Y' if value == 'C' else value

    return result


def add_leading_space(value):
    """
    If the first character of value is not a space or '-' then, prepend a space to value
    and return the result, otherwise return value.
    :param str value:
    :return: str
    """
    return value if len(value) == 0 or (value[0] == ' ' or value[0] == '-') else ' ' + value

def add_leading_zero(value):
    """
    If the second character of value is not a '1' then, prepend a zero to value after the space or '-'
    and return the result, otherwise return value.
    :param str value:
    :return: str
    """
    return value if len(value) == 0 or (value[1] == '1' or value[1] == '0') else '{0}0{1}'.format(value[:1], value[1:])

def too_many_transactions(value):
    """
    If the number of transactions (value) is greater than 30,000 return the true, otherwise return false.
    :param int value:
    :return: boolean
    """
    return True if value > MAX_TRANSACTIONS else False

def parse(file_contents):
    """
    :param file_contents:
    :return: array of dictionary. Each dictionary contains a transaction for a site parsed from file_contents
    :raises: ParseError with an appropriate message if unable to parse file.
    """

    lines = get_lines(file_contents)
    transactions = get_transactions(lines)
    results = []

    if too_many_transactions(len(transactions)):
        raise ParseError(
            'Ddot file contains more than the maximum-allowed {0} transactions. Please split the file into multiple ddot files of fewer than {0} transactions.'.format(
                MAX_TRANSACTIONS))

    for transaction in transactions:
        try:
            kv_pairs = parse_key_value_pairs(transaction.get('key_value_pairs'))
        except ParseError as err:
            raise ParseError('Parsing error on lines{0}: line {1}'.format(transaction.get('line_numbers'), err.message))

        if has_duplicate_station_name_keys(kv_pairs):
            raise ParseError('Parsing error on lines {0}: Duplicate station name codes'.format(transaction.get('line_numbers')))
        if not has_transaction_type(kv_pairs):
            raise ParseError('Parsing error on lines {0}: Missing "T" (transaction type) component'.format(transaction.get('line_numbers')))

        invalid_codes = invalid_key_codes(kv_pairs)
        if invalid_codes:
            raise ParseError('Parsing error on lines {0}: Invalid component codes {1}'.format(transaction.get('line_numbers'), ', '.join(invalid_codes)))

        this_result = translate_keys_to_attributes(kv_pairs)
        this_result['agencyCode'] = transaction.get('agencyCode')
        this_result['siteNumber'] = transaction.get('siteNumber')

        if this_result.get('transactionType', '') not in ['A', 'M']:
            raise ParseError('Parsing error on lines {0}: Invalid transaction type'.format(transaction.get('line_numbers')))

        # Any special processing on values
        if 'stationName' in this_result:
            this_result['stationName'] = remove_leading_and_trailing_single_quotes(this_result['stationName'])

        if 'latitude' in this_result:
            this_result['latitude'] = add_leading_space(this_result['latitude'])

        if 'longitude' in this_result:
            this_result['longitude'] = add_leading_space(this_result['longitude'])
            this_result['longitude'] = add_leading_zero(this_result['longitude'])

        if 'siteWebReadyCode' in this_result:
            this_result['siteWebReadyCode'] = update_c_code_to_y_code(this_result['siteWebReadyCode'])

        results.append(this_result)

    # Filter out any transaction that is not for the sitefile
    site_results = [result for result in results if result.get('databaseTableIdentifier') == '0']

    # Do another check for duplicate transactions
    sites = [(site_result.get('agencyCode'), site_result.get('siteNumber')) for site_result in site_results]
    duplicate_sites = set([site for site in sites if sites.count(site) > 1])
    if duplicate_sites:
        raise ParseError('Duplicate transaction for sites: {0}'.format(duplicate_sites))

    return site_results


