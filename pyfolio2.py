#!/usr/bin/python3

import argparse

from c_functions import prepare_data, display_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--currency', action='store', type=str, default='usd')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument(
        '-t', '--test', action='store_true', help='use locally saved data instead of getting fresh from the apis'
    )

    args = parser.parse_args()

    coins = prepare_data(currency=args.currency.upper(), debug=args.debug, test=args.test)

    display_data(coins=sorted(coins))
