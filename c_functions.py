import json
import requests
import time
import configparser
from typing import List

from c_constants import cmc_json_file, holdings_file, cmc_headers, num_coins, show_bitcoin_if_not_held, dp
from c_dataclasses import Coin, Quantity, Elements


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
        coins['bitcoin'] = {'held': 0}

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
        cmc_data = requests.get(url, headers=cmc_headers, params=parameters).json()

        with cmc_json_file.open('w') as f:
            json.dump(cmc_data, f)
            
        if debug:
            print(f'done ({(time.perf_counter() - c_start):.3f}s)')

    return cmc_data['data']


def print_message(msg):
    print(f' {time.strftime("%H:%M:%S")} {msg}')
    

def prepare_data(currency, debug=False, test=False):
    Coin.currency = currency
    Coin.debug = debug
    Coin.test = test
    
    if debug:
        print(f' {time.strftime("%H:%M:%S")} loading holdings... ', end='', flush=True)
        
    holdings = get_holdings()

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
                if Coin.debug:
                    print(f' {coin_name} matched to {coin_json["name"]}')

                coins.append(Coin(cmc_data=coin_json, ini_data=holdings[coin_name]))
                coin_found = True
                break

        if coin_found:
            continue

        print('fuck. coin not found:', coin_name)

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
        coin.pad_held_str(longest_symbol, perc_of_total=perc_of_total)

    return coins


def display_data(coins: List[Coin]):
    pad = 1
    l_rank = max(3, len(str(max([c.rank for c in coins]))))
    l_rank_w_pad = l_rank + (2 * pad) + 1
    l_name = len(str(max([c.name for c in coins], key=len)))
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

    print(f'\n {time.strftime("%A - %Y/%m/%d - %X")}\n\n {top}\n {header}\n {mid_thick}')

    for idx, c in enumerate(coins):
        is_eth = True if c.name.lower() == 'ethereum' else False
        value_1_in_eth = "" if is_eth else c.value_of_one.in_eth.formatted
        value_all_in_eth = "" if is_eth else c.value_of_held.in_eth.formatted
        is_btc = True if c.name.lower() == 'bitcoin' else False
        value_1_in_btc = "" if is_btc else c.value_of_one.in_btc.formatted
        value_all_in_btc = "" if is_btc else c.value_of_held.in_btc.formatted

        if is_eth and idx > 0:
            print(f' {mid_thin}')

        print(
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

        if is_eth and c.qty_held and c.qty_staked and c.qty_earned:
            big_gap_left = l_1_fiat + l_1_btc + l_1_eth + (pad * 4)
            big_gap_right = l_name + l_symbol + l_1_fiat + l_1_btc + (pad * 4)

            for s in [c.qty_held, c.qty_staked, c.qty_earned]:
                print(
                    f' {e.ver_thick}{col_pad}{" " * l_rank} {col_pad}{e.ver_thin}'
                    f'{col_pad}- {s.s_str:<{l_name-2}}{col_pad}{e.ver_thin}'
                    f'{col_pad}{" " * big_gap_left}{col_pad}{e.ver_thick}'
                    f'{col_pad}{s.in_eth.formatted:>{l_held}}{col_pad}{e.ver_thick}'
                    f'{col_pad}{s.in_fiat.formatted:>{l_all_fiat}}{col_pad}'
                    f'{col_pad}{s.in_btc.formatted:>{l_all_btc}}{col_pad}'
                    f'{col_pad}{" " * l_all_eth}{col_pad}{e.ver_thick}'
                    f'{col_pad}{" " * l_perc}{col_pad}{e.ver_thick}'
                )
        
            if idx + 1 < len(coins):
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