#!/usr/bin/python3

import argparse
from c_constants import currency
from c_functions import prepare_data, display_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--currency', action='store', type=str,
        help='show prices in particular currency - change the default in config.ini'
    )
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument(
        '-t', '--test', action='store_true',
        help='use locally saved data instead of getting it fresh from the apis (saves api calls while testing)'
    )

    args = parser.parse_args()
    currency = args.currency or currency
    coins = prepare_data(currency=currency.upper(), debug=args.debug, test=args.test)
    display_data(coins=sorted(coins))
