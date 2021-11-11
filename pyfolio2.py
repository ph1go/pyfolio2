#!/usr/bin/python3

import argparse
from c_constants import currency
from c_functions import prepare_data, display_data, display_validators


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f', '--fiat-currency', action='store', type=str,
        help='show prices in a particular fiat currency - change the default in config.ini'
    )

    parser.add_argument(
        '-c', '--compare-to', action='store', type=str, nargs='+',
        help='compare fiat currency amounts to cryptocurrencies other than Bitcoin and Ethereum'
    )
    parser.add_argument(
        '-v', '--validators', action='store_true',
        help='show a table dedicated to Ethereum validators'
    )
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument(
        '-u', '--update-coins-list', action='store_true',
        help='download a fresh copy of the CoinGecko coins list (necessary if they add a new coin)'
    )
    parser.add_argument(
        '-t', '--test', action='store_true',
        help='use locally saved data instead of getting it fresh from the apis (saves api calls while testing)'
    )

    args = parser.parse_args()

    coins = prepare_data(fiat_currency=(args.fiat_currency or currency).upper(), args=args)

    if args.validators:
        for coin in coins:
            if coin.symbol == 'ETH':
                try:
                    validators = coin.validators

                except AttributeError:
                    print('eek')

                else:
                    display_validators(validators=validators)

                finally:
                    break

    else:
        display_data(coins=sorted(coins))
