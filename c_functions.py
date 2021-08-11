import json
from operator import attrgetter

import requests
import time
import configparser
from typing import List

from c_constants import (
    cmc_json_file, holdings_file, cmc_headers, num_coins, split_validators, show_bitcoin_if_not_held, dp,
    details_in_name_col, sort_vals_by_earnings
)

from c_dataclasses import Coin, Validator, Quantity, Elements


def get_holdings():
    cfg = configparser.RawConfigParser()
    cfg.read(holdings_file)

    coins = {}

    try:
        eth = cfg['ethereum']

    except KeyError:
        try:
            eth = cfg['eth']

        except KeyError:
            eth = None

    if eth:
        coins['ethereum'] = {
            'held': eth.getfloat('held'), 'staked': eth.getfloat('staked'), 'validators': eth.get('validators', None)
        }

        if coins['ethereum']['validators']:
            coins['ethereum']['validators'] = [v.strip() for v in coins['ethereum']['validators'].split(',')]

    for k in cfg['other coins']:
        coins[k] = {'held': cfg['other coins'].getfloat(k)}

    if show_bitcoin_if_not_held and 'bitcoin' not in coins.keys() and 'btc' not in coins.keys():
        coins['bitcoin'] = {'held': 0, 'comparison_only': True}

    return coins


def get_coinmarketcap_data(currency, debug, test):
    if test:
        with cmc_json_file.open() as f:
            cmc_data = json.load(f)

    else:    
        if debug:                
            print(f' {time.strftime("%H:%M:%S")} downloading coinmarketcap data... ', end='', flush=True)    
            c_start = time.perf_counter()

        url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
        parameters = {'start': '1', 'limit': num_coins, 'convert': currency}
        try:
            cmc_data = requests.get(url, headers=cmc_headers, params=parameters).json()

        except json.decoder.JSONDecodeError:
            if cmc_json_file.is_file():
                print(' Bad JSON from coinmarketcap, loading locally price data from the last successful call...')
                with cmc_json_file.open() as f:
                    cmc_data = json.load(f)

            else:
                print(' Bad JSON from coinmarketcap, no locally saved price data found.')
                exit()

        else:
            with cmc_json_file.open('w') as f:
                json.dump(cmc_data, f)
            
        if debug:
            print(f'done ({(time.perf_counter() - c_start):.3f}s)')

    return cmc_data['data']


def print_message(msg):
    print(f' {time.strftime("%H:%M:%S")} {msg}')
    

def prepare_data(currency, args): #  debug=False, test=False):
    Coin.currency = currency
    Coin.debug = debug = args.debug
    Coin.test = test = args.test

    # print(debug, test, validators, currency)
    # exit()

    if debug:
        print(f' {time.strftime("%H:%M:%S")} loading holdings... ', end='', flush=True)
        
    holdings = get_holdings()

    # print(holdings)
    # exit()

    if debug:
        print('done')
        
    cmc_data = get_coinmarketcap_data(currency=currency, debug=debug, test=test)
        
    btc_found = False
    eth_found = False

    for coin_json in cmc_data:
        if coin_json['symbol'].lower() == 'btc':
            Coin.btc_price = coin_json['quote'][currency]['price']
            btc_found = True

        elif coin_json['symbol'].lower() == 'eth':
            Coin.eth_price = coin_json['quote'][currency]['price']
            eth_found = True

        if btc_found and eth_found:
            break

    coins = []
    for coin_name in holdings:
        coin_found = False
        for coin_json in cmc_data:
            if coin_name in [coin_json['name'].lower(), coin_json['symbol'].lower()]:
                coin = Coin(cmc_data=coin_json, ini_data=holdings[coin_name])

                if Coin.debug and not coin.comparison_only:
                    print(f' "{coin_name}" matched to {coin_json["name"]}')

                coins.append(coin)
                coin_found = True
                break

        if coin_found:
            continue

        print(f' No matching coin found for "{coin_name}".')

    Coin.fiat_total = Quantity(
        raw=sum([c.value_of_held.in_fiat.raw for c in coins]), dec_places=dp.fiat, currency=currency
    )

    Coin.total_held_in_btc = Quantity(
        raw=Coin.fiat_total.raw / Coin.btc_price, dec_places=dp.crypto, currency='BTC'
    )

    Coin.total_held_in_eth = Quantity(
        raw=Coin.fiat_total.raw / Coin.eth_price, dec_places=dp.crypto, currency='ETH'
    )

    longest_symbol = len(max([c.symbol for c in coins], key=len))

    for coin in coins:
        perc_of_total = (coin.value_of_held.in_fiat.raw / Coin.fiat_total.raw) * 100
        if not args.validators:
            coin.pad_held_str(longest_symbol, perc_of_total=perc_of_total)

    return coins


def display_validators(validators: List[Validator]):
    pad = 1

    l_rank = max(3, len(str(len(validators))))
    l_rank_w_pad = l_rank + (2 * pad) + 1

    l_index = max(5, len(max([v.index for v in validators], key=len)))
    l_index_w_pad = l_index + (2 * pad)

    total_pad = l_rank_w_pad + l_index_w_pad + 2

    staked_in_eth_total = Quantity(
        raw=sum([v.staked.in_eth.raw for v in validators]), dec_places=dp.fiat, currency='ETH'
    )

    staked_in_btc_total = Quantity(
        raw=sum([v.staked.in_btc.raw for v in validators]), dec_places=dp.fiat, currency='BTC'
    )

    staked_in_fiat_total = Quantity(
        raw=sum([v.staked.in_fiat.raw for v in validators]), dec_places=dp.fiat, currency=Coin.currency
    )

    earned_in_eth_total = Quantity(
        raw=sum([v.earned.in_eth.raw for v in validators]), dec_places=dp.fiat, currency='ETH'
    )

    earned_in_btc_total = Quantity(
        raw=sum([v.earned.in_btc.raw for v in validators]), dec_places=dp.fiat, currency='BTC'
    )

    earned_in_fiat_total = Quantity(
        raw=sum([v.earned.in_fiat.raw for v in validators]), dec_places=dp.fiat, currency=Coin.currency
    )

    total_in_eth_total = Quantity(
        raw=sum([v.total.in_eth.raw for v in validators]), dec_places=dp.fiat, currency='ETH'
    )

    total_in_btc_total = Quantity(
        raw=sum([v.total.in_btc.raw for v in validators]), dec_places=dp.fiat, currency='BTC'
    )

    total_in_fiat_total = Quantity(
        raw=sum([v.total.in_fiat.raw for v in validators]), dec_places=dp.fiat, currency=Coin.currency
    )

    for validator in validators:
        perc = (validator.total.in_eth.raw / total_in_eth_total.raw) * 100
        validator.percentage = Quantity(raw=perc, currency='%', dec_places=dp.percent)

    l_percentage = len(max([v.percentage.formatted for v in validators], key=len))
    l_percentage_w_pad = l_percentage + (2 * pad)

    staked_in_eth = max(6, len(staked_in_eth_total.formatted))
    staked_in_eth_w_pad = staked_in_eth + (2 * pad)
    staked_in_btc = max(6, len(staked_in_btc_total.formatted))
    staked_in_btc_w_pad = staked_in_btc + (2 * pad)
    staked_in_fiat = max(6, len(staked_in_fiat_total.formatted))
    staked_in_fiat_w_pad = staked_in_fiat + (2 * pad)

    earned_in_eth = max(6, len(earned_in_eth_total.formatted))
    earned_in_eth_w_pad = earned_in_eth + (2 * pad)
    earned_in_btc = max(6, len(earned_in_btc_total.formatted))
    earned_in_btc_w_pad = earned_in_btc + (2 * pad)
    earned_in_fiat = max(6, len(earned_in_fiat_total.formatted))
    earned_in_fiat_w_pad = earned_in_fiat + (2 * pad)

    total_in_eth = max(6, len(total_in_eth_total.formatted))
    total_in_eth_w_pad = total_in_eth + (2 * pad)
    total_in_btc = max(6, len(total_in_btc_total.formatted))
    total_in_btc_w_pad = total_in_btc + (2 * pad)
    total_in_fiat = max(6, len(total_in_fiat_total.formatted))
    total_in_fiat_w_pad = total_in_fiat + (2 * pad)

    col_pad = " " * pad

    e = Elements()

    show_btc = False

    staked_width = staked_in_eth_w_pad + staked_in_fiat_w_pad
    earned_width = earned_in_eth_w_pad + earned_in_fiat_w_pad
    total_width = total_in_eth_w_pad + total_in_fiat_w_pad

    staked_header = f'{col_pad}{"STAKED":>{staked_in_eth}}{col_pad}'
    earned_header = f'{col_pad}{"EARNED":>{earned_in_eth}}{col_pad}'
    total_header = f'{col_pad}{"TOTAL":>{total_in_eth}}{col_pad}'

    staked_total = f'{col_pad}{staked_in_eth_total.formatted:>{staked_in_eth}}{col_pad}'
    earned_total = f'{col_pad}{earned_in_eth_total.formatted:>{earned_in_eth}}{col_pad}'
    total_total = f'{col_pad}{total_in_eth_total.formatted:>{total_in_eth}}{col_pad}'

    if show_btc:
        staked_width += staked_in_btc_w_pad
        earned_width += earned_in_btc_w_pad
        total_width += total_in_btc_w_pad
        staked_header += f'{col_pad}{"in BTC":>{staked_in_btc}}{col_pad}'
        earned_header += f'{col_pad}{"in BTC":>{earned_in_btc}}{col_pad}'
        total_header += f'{col_pad}{"in BTC":>{total_in_btc}}{col_pad}'
        staked_total += f'{col_pad}{staked_in_btc_total.formatted:>{staked_in_btc}}{col_pad}'
        earned_total += f'{col_pad}{earned_in_btc_total.formatted:>{earned_in_btc}}{col_pad}'
        total_total += f'{col_pad}{total_in_btc_total.formatted:>{total_in_btc}}{col_pad}'

    staked_header += f'{col_pad}{f"in {Coin.currency}":>{staked_in_fiat}}{col_pad}'
    earned_header += f'{col_pad}{f"in {Coin.currency}":>{earned_in_fiat}}{col_pad}'
    total_header += f'{col_pad}{f"in {Coin.currency}":>{total_in_fiat}}{col_pad}'
    staked_total += f'{col_pad}{staked_in_fiat_total.formatted:>{staked_in_fiat}}{col_pad}'
    earned_total += f'{col_pad}{earned_in_fiat_total.formatted:>{earned_in_fiat}}{col_pad}'
    total_total += f'{col_pad}{total_in_fiat_total.formatted:>{total_in_fiat}}{col_pad}'

    total_total_line = (
        f'{"Total: ":>{total_pad}}{e.ver_thick}'
        f'{staked_total}{e.ver_thin}{earned_total}{e.ver_thin}{total_total}{e.ver_thick}'
    )

    top = (
        f'{e.top.left}{e.hor_thick * l_rank_w_pad}{e.top.mid_thick}{e.hor_thick * l_index_w_pad}{e.top.mid_thick}'
        f'{e.hor_thick * staked_width}{e.top.mid_thin}{e.hor_thick * earned_width}'
        f'{e.top.mid_thin}{e.hor_thick * total_width}'
        f'{e.top.right}'
    )

    header = (
        f'{e.ver_thick}{col_pad}Rank{col_pad}{e.ver_thick}{col_pad}{"Index":<{l_index}}{col_pad}{e.ver_thick}'
        f'{staked_header}{e.ver_thin}{earned_header}{e.ver_thin}{total_header}'
        f'{e.ver_thick}'
    )

    body_top = (
        f'{e.mid_thick.left}{e.hor_thick * l_rank_w_pad}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * l_index_w_pad}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * staked_width}{e.mid_thick.mid_thin}'
        f'{e.hor_thick * earned_width}{e.mid_thick.mid_thin}'
        f'{e.hor_thick * total_width}'
        f'{e.mid_thick.mid_thick}{e.hor_thick * l_percentage_w_pad}{e.top.right}'
    )

    body_bottom = (
        f'{e.bot.left}{e.hor_thick * l_rank_w_pad}'
        f'{e.bot.mid_thick}{e.hor_thick * l_index_w_pad}'
        f'{e.mid_thick.mid_thick}{e.hor_thick * staked_width}'
        f'{e.mid_thick.mid_thin}{e.hor_thick * earned_width}'
        f'{e.mid_thick.mid_thin}{e.hor_thick * total_width}'
        f'{e.mid_thick.mid_thick}{e.hor_thick * l_percentage_w_pad}{e.bot.right}'
    )

    bottom = (
        f'{" " * total_pad}{e.bot.left}'
        f'{e.hor_thick * staked_width}{e.bot.mid_thin}'
        f'{e.hor_thick * earned_width}{e.bot.mid_thin}'
        f'{e.hor_thick * total_width}{e.bot.right}'
    )

    if sort_vals_by_earnings:
        validators.sort(key=attrgetter('earned.quantity'), reverse=True)

    else:
        validators.sort()

    print(f'\n {time.strftime("%A - %Y/%m/%d - %X")}\n\n {top}\n {header}\n {body_top}')

    for idx, validator in enumerate(validators):
        staked_line = f'{col_pad}{validator.staked.in_eth.formatted:>{staked_in_eth}}{col_pad}'
        earned_line = f'{col_pad}{validator.earned.in_eth.formatted:>{earned_in_eth}}{col_pad}'
        total_line = f'{col_pad}{validator.total.in_eth.formatted:>{total_in_eth}}{col_pad}'

        if show_btc:
            staked_line += f'{col_pad}{validator.staked.in_btc.formatted:>{staked_in_btc}}{col_pad}'
            earned_line += f'{col_pad}{validator.earned.in_btc.formatted:>{earned_in_btc}}{col_pad}'
            total_line += f'{col_pad}{validator.total.in_btc.formatted:>{total_in_btc}}{col_pad}'

        staked_line += f'{col_pad}{validator.staked.in_fiat.formatted:>{staked_in_fiat}}{col_pad}'
        earned_line += f'{col_pad}{validator.earned.in_fiat.formatted:>{earned_in_fiat}}{col_pad}'
        total_line += f'{col_pad}{validator.total.in_fiat.formatted:>{total_in_fiat}}{col_pad}'

        validator_line = (
            f' {e.ver_thick}{col_pad}{idx+1:>{l_rank}}){col_pad}{e.ver_thick}'
            f'{col_pad}{validator.index:>{l_index}}{col_pad}{e.ver_thick}'
            f'{staked_line}{e.ver_thin}{earned_line}{e.ver_thin}{total_line}{e.ver_thick}'
            f'{col_pad}{validator.percentage.formatted:>{l_percentage}}{col_pad}{e.ver_thick}'
        )

        print(validator_line)

    print(f' {body_bottom}\n {total_total_line}\n {bottom}')


def display_data(coins: List[Coin]):
    pad = 1

    min_name_width = 9 if Coin.is_staking_eth else 4
    l_rank = max(3, len(str(max([c.rank for c in coins]))))
    l_rank_w_pad = l_rank + (2 * pad) + 1
    l_name = max(min_name_width, len(str(max([c.name for c in coins], key=len))))
    l_name_w_pad = l_name + (2 * pad)
    l_symbol = len(str(max([c.symbol for c in coins], key=len)))
    l_symbol_w_pad = l_symbol + (2 * pad)
    l_1_fiat = max(10, len(max([c.value_of_one.in_fiat.formatted for c in coins], key=len)))
    l_1_fiat_w_pad = l_1_fiat + (2 * pad)
    l_1_btc = len(max([c.value_of_one.in_btc.formatted for c in coins], key=len))
    l_1_btc_w_pad = l_1_btc + (2 * pad)
    l_1_eth = len(max([c.value_of_one.in_eth.formatted for c in coins], key=len))
    l_1_eth_w_pad = l_1_eth + (2 * pad)
    l_held = len(max([c.total_held.formatted for c in coins], key=len))
    l_held_w_pad = l_held + (2 * pad)
    l_all_fiat = max(10, len(Coin.fiat_total.formatted))
    l_all_fiat_w_pad = l_all_fiat + (2 * pad)
    l_all_btc = len(Coin.total_held_in_btc.formatted)
    l_all_btc_w_pad = l_all_btc + (2 * pad)
    l_all_eth = len(Coin.total_held_in_eth.formatted)
    l_all_eth_w_pad = l_all_eth + (2 * pad)
    l_perc = len(max([c.perc_of_total.formatted for c in coins], key=len))
    l_perc_w_pad = l_perc + (2 * pad)

    col_pad = " " * pad

    e = Elements()

    top = (
        f'{e.top.left}{e.hor_thick * l_rank_w_pad}{e.top.mid_thin}{e.hor_thick * l_name_w_pad}{e.top.mid_thin}'
        f'{e.hor_thick * (l_1_fiat_w_pad + l_1_btc_w_pad + l_1_eth_w_pad)}{e.top.mid_thick}'
        f'{e.hor_thick * l_held_w_pad}{e.top.mid_thick}'
        f'{e.hor_thick * (l_all_fiat_w_pad + l_all_btc_w_pad + l_all_eth_w_pad)}{e.top.right}'
    )

    header = (
        f'{e.ver_thick}{col_pad}Rank{col_pad}{e.ver_thin}{col_pad}{"Name":<{l_name}}{col_pad}{e.ver_thin}'
        f'{col_pad}{"Price of 1":>{l_1_fiat}}{col_pad}'
        f'{col_pad}{"in BTC":>{l_1_btc}}{col_pad}'
        f'{col_pad}{"in ETH":>{l_1_eth}}{col_pad}{e.ver_thick}'
        f'{col_pad}{"Held":^{l_held}}{col_pad}{e.ver_thick}'
        f'{col_pad}{"Value held":>{l_all_fiat}}{col_pad}'
        f'{col_pad}{"in BTC":>{l_all_btc}}{col_pad}'
        f'{col_pad}{"in ETH":>{l_all_eth}}{col_pad}{e.ver_thick}'
    )

    big_gap = l_1_fiat + l_1_btc + l_1_eth + (pad * 4)
    whole_1 = l_1_fiat_w_pad + l_1_btc_w_pad + l_1_eth_w_pad
    whole_all = l_all_fiat_w_pad + l_all_btc_w_pad + l_all_eth_w_pad

    mid_thick = (
        f'{e.mid_thick.left}{e.hor_thick * l_rank_w_pad}{e.mid_thick.mid_thin}'
        f'{e.hor_thick * l_name_w_pad}{e.mid_thick.mid_thin}'
        f'{e.hor_thick * whole_1}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * l_held_w_pad}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * whole_all}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * l_perc_w_pad}{e.top.right}'
    )

    mid_thin = (
        f'{e.mid_thin.left}{e.hor_thin * l_rank_w_pad}{e.mid_thin.mid_thin}{e.hor_thin * l_name_w_pad}'
        f'{e.mid_thin.mid_thin}{e.hor_thin * whole_1}'
        f'{e.mid_thin.mid_thick}{e.hor_thin * l_held_w_pad}{e.mid_thin.mid_thick}'
        f'{e.hor_thin * whole_all}{e.mid_thin.mid_thick}'
        f'{e.hor_thin * l_perc_w_pad}{e.mid_thin.right}'
    )

    blank_line = (
        f'{e.ver_thick}{" " * l_rank_w_pad}{e.ver_thin}{" " * l_name_w_pad}'
        f'{e.ver_thin}{" " * whole_1}'
        f'{e.ver_thick}{" " * l_held_w_pad}{e.ver_thick}'
        f'{" " * whole_all}{e.ver_thick}'
        f'{" " * l_perc_w_pad}{e.ver_thick}'
    )

    print(f'\n {time.strftime("%A - %Y/%m/%d - %X")}\n\n {top}\n {header}\n {mid_thick}')

    for idx, c in enumerate(coins):
        is_eth = True if c.name.lower() == 'ethereum' else False
        value_1_in_eth = "" if is_eth else c.value_of_one.in_eth.formatted
        value_all_in_eth = "" if is_eth else c.value_of_held.in_eth.formatted
        is_btc = True if c.name.lower() == 'bitcoin' else False
        value_1_in_btc = "" if is_btc else c.value_of_one.in_btc.formatted
        value_all_in_btc = "" if is_btc else c.value_of_held.in_btc.formatted

        if is_eth:
            top_str = (
                f' {e.ver_thick}{col_pad}{c.rank:>{l_rank}}){col_pad}{e.ver_thin}'
                f'{col_pad}{c.name:<{l_name}}{col_pad}{e.ver_thin}'
                f'{col_pad}{c.value_of_one.in_fiat.formatted:>{l_1_fiat}}{col_pad}'
                f'{col_pad}{value_1_in_btc:>{l_1_btc}}{col_pad}'
                f'{col_pad}{value_1_in_eth:>{l_1_eth}}{col_pad}{e.ver_thick}'
            )

            if Coin.is_staking_eth:
                if idx > 0:
                    print(f' {mid_thin}')

                top_str += (
                    f'{" " * l_held_w_pad}{e.ver_thick}'
                    f'{" " * whole_all}{e.ver_thick}'
                    f'{" " * l_perc_w_pad}{e.ver_thick}'
                )

            else:
                top_str += (
                    f'{col_pad}{c.total_held.formatted:>{l_held}}{col_pad}{e.ver_thick}'
                    f'{col_pad}{c.value_of_held.in_fiat.formatted:>{l_all_fiat}}{col_pad}'
                    f'{col_pad}{value_all_in_btc:>{l_all_btc}}{col_pad}'
                    f'{col_pad}{value_all_in_eth:>{l_all_eth}}{col_pad}{e.ver_thick}'
                    f'{col_pad}{c.perc_of_total.formatted:>{l_perc}}{col_pad}{e.ver_thick}'
                )

        else:
            top_str = (
                f' {e.ver_thick}{col_pad}{c.rank:>{l_rank}}){col_pad}{e.ver_thin}'
                f'{col_pad}{c.name:<{l_name}}{col_pad}{e.ver_thin}'
                f'{col_pad}{c.value_of_one.in_fiat.formatted:>{l_1_fiat}}{col_pad}'
                f'{col_pad}{value_1_in_btc:>{l_1_btc}}{col_pad}'
                f'{col_pad}{value_1_in_eth:>{l_1_eth}}{col_pad}{e.ver_thick}'
                f'{col_pad}{c.total_held.formatted:>{l_held}}{col_pad}{e.ver_thick}'
                f'{col_pad}{c.value_of_held.in_fiat.formatted:>{l_all_fiat}}{col_pad}'
                f'{col_pad}{value_all_in_btc:>{l_all_btc}}{col_pad}'
                f'{col_pad}{value_all_in_eth:>{l_all_eth}}{col_pad}{e.ver_thick}'
                f'{col_pad}{c.perc_of_total.formatted:>{l_perc}}{col_pad}{e.ver_thick}'
            )

        print(top_str)

        sub_line_start = f' {e.ver_thick}{col_pad}{"":{l_rank}} {col_pad}{e.ver_thin}'

        if is_eth and c.qty_held and Coin.is_staking_eth:
            # print(f' {blank_line}')

            for s in [c.qty_held, c.qty_staked]:
                if details_in_name_col:
                    s_details_str = (
                        f'{col_pad} - {s.short_str:<{l_name-3}}{col_pad}{e.ver_thin}'
                        f'{col_pad}{" " * big_gap}{col_pad}'
                    )

                else:
                    s_details_str = (
                        f'{"":{l_name_w_pad}}{e.ver_thin}{col_pad}{s.long_str:>{big_gap}}{col_pad}'
                    )

                print(
                    f'{sub_line_start}{s_details_str}{e.ver_thick}'
                    f'{col_pad}{s.in_eth.formatted:>{l_held}}{col_pad}{e.ver_thick}'
                    f'{col_pad}{s.in_fiat.formatted:>{l_all_fiat}}{col_pad}'
                    f'{col_pad}{s.in_btc.formatted:>{l_all_btc}}{col_pad}'
                    f'{col_pad}{"":{l_all_eth}}{col_pad}{e.ver_thick}'
                    f'{col_pad}{"":{l_perc}}{col_pad}{e.ver_thick}'
                )

            if split_validators and len(c.validators) > 1:
                print(f' {blank_line}')

                if sort_vals_by_earnings:
                    vals = sorted(c.validators, key=attrgetter('earned.quantity'), reverse=True)

                else:
                    vals = sorted(c.validators)

                for v in vals:
                    if details_in_name_col:
                        v_details_str = (
                            f'{col_pad}  - {v.index:<{l_name - 4}}{col_pad}{e.ver_thin}'
                            f'{col_pad}{" " * big_gap}{col_pad}'
                        )

                    else:
                        v_details_str = (
                            f'{"":{l_name_w_pad}}{e.ver_thin}{col_pad}{v.val_str:>{big_gap}}{col_pad}'
                        )

                    print(
                        f'{sub_line_start}{v_details_str}{e.ver_thick}'
                        f'{col_pad}{v.earned.in_eth.formatted:>{l_held}}{col_pad}{e.ver_thick}'
                        f'{col_pad}{v.earned.in_fiat.formatted:>{l_all_fiat}}{col_pad}'
                        f'{col_pad}{v.earned.in_btc.formatted:>{l_all_btc}}{col_pad}'
                        f'{col_pad}{" " * l_all_eth}{col_pad}{e.ver_thick}'
                        f'{col_pad}{" " * l_perc}{col_pad}{e.ver_thick}'
                    )

                print(f' {blank_line}')

            if details_in_name_col:
                e_details_str = (
                    f'{col_pad} - {c.qty_earned.short_str:<{l_name-3}}{col_pad}{e.ver_thin}'
                    f'{col_pad}{" " * big_gap}{col_pad}'
                )

            else:
                e_details_str = (
                    f'{"":{l_name_w_pad}}{e.ver_thin}{col_pad}{c.qty_earned.long_str:>{big_gap}}{col_pad}'
                )

            print(
                f'{sub_line_start}{e_details_str}{e.ver_thick}'
                f'{col_pad}{c.qty_earned.in_eth.formatted:>{l_held}}{col_pad}{e.ver_thick}'
                f'{col_pad}{c.qty_earned.in_fiat.formatted:>{l_all_fiat}}{col_pad}'
                f'{col_pad}{c.qty_earned.in_btc.formatted:>{l_all_btc}}{col_pad}'
                f'{col_pad}{" " * l_all_eth}{col_pad}{e.ver_thick}'
                f'{col_pad}{" " * l_perc}{col_pad}{e.ver_thick}'
            )

            print(f' {blank_line}')

            if details_in_name_col:
                t_details_str = (
                    f'{col_pad}{"TOTAL ETH":<{l_name}}{col_pad}{e.ver_thin}{col_pad}{" " * big_gap}{col_pad}'
                )

            else:
                t_details_str = (
                    f'{"":{l_name_w_pad}}{e.ver_thin}{col_pad}{"TOTAL ETH HELD":>{big_gap}}{col_pad}'
                )

            print(
                f'{sub_line_start}{t_details_str}{e.ver_thick}'
                f'{col_pad}{c.total_held.formatted:>{l_held}}{col_pad}{e.ver_thick}'
                f'{col_pad}{c.value_of_held.in_fiat.formatted:>{l_all_fiat}}{col_pad}'
                f'{col_pad}{value_all_in_btc:>{l_all_btc}}{col_pad}'
                f'{col_pad}{value_all_in_eth:>{l_all_eth}}{col_pad}{e.ver_thick}'
                f'{col_pad}{c.perc_of_total.formatted:>{l_perc}}{col_pad}{e.ver_thick}'
            )

            if idx + 1 < len(coins) and Coin.is_staking_eth:
                print(f' {mid_thin}')

    bottom = (
        f'{e.bot.left}{e.hor_thick * l_rank_w_pad}{e.bot.mid_thin}{e.hor_thick * l_name_w_pad}'
        f'{e.bot.mid_thin}{e.hor_thick * whole_1}{e.bot.mid_thick}{e.hor_thick * l_held_w_pad}'
        f'{e.mid_thick.mid_thick}{e.hor_thick * whole_all}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * l_perc_w_pad}{e.bot.right}'
    )

    bottom_gap = l_rank_w_pad + l_name_w_pad + whole_1 + l_held_w_pad + 4

    abs_bottom = (
        f'{" " * (bottom_gap - 7)}Total: {e.ver_thick}'
        f'{col_pad}{Coin.fiat_total.formatted:>{l_all_fiat}}{col_pad}'
        f'{col_pad}{Coin.total_held_in_btc.formatted:>{l_all_btc}}{col_pad}'
        f'{col_pad}{Coin.total_held_in_eth.formatted:>{l_all_eth}}{col_pad}{e.ver_thick}\n '
        f'{" " * bottom_gap}{e.bot.left}{e.hor_thick * whole_all}{e.bot.right}'
    )

    print(f' {bottom}\n {abs_bottom}\n ')