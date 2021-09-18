import requests
import json
import time

from c_constants import (
    coins_list_json_file, coins_json_file, coingecko_headers,
    coingecko_currencies_url, coingecko_coins_url, coingecko_markets_url, request_timeout
)


def _do_request(url, params=None):
    try:
        response = requests.get(
            url=url, headers=coingecko_headers, params=params if params else {}, timeout=request_timeout
        )

    except requests.exceptions.ReadTimeout:
        print(f' timeout: {url}\n')
        exit()

    else:
        try:
            response_json = response.json()

        except Exception as e:
        # except json.decoder.JSONDecodeError:
            print(response.content, e.msg)
            exit()

        else:
            return response_json

    return None


def is_valid_currency(currency):
    if currency.lower() == 'usd':
        return True

    currencies = requests.get(coingecko_currencies_url, headers=coingecko_headers).json()

    return True if currency.lower() in currencies else False


def get_coins_list(debug=False):
    if debug:
        start = time.perf_counter()

    if coins_list_json_file.is_file():
        if debug:
            print(
                f' {time.strftime("%H:%M:%S")} coins file ("{coins_list_json_file}") found, loading... ',
                end='', flush=True
            )

        with coins_list_json_file.open() as f:
            coins_list = json.load(f)

    else:
        if debug:
            print(
                f' {time.strftime("%H:%M:%S")} coins file ("{coins_list_json_file}") not found, downloading... ',
                end='', flush=True
            )

        coins_list = requests.get(coingecko_coins_url, headers=coingecko_headers, timeout=request_timeout).json()

        with coins_list_json_file.open('w') as f:
            json.dump(coins_list, f)

    if debug:
        print(f'done ({time.perf_counter() - start:,.3f}s)')

    return coins_list


def get_coin_prices(coins, currency, debug=False, test=False):
    def get_coin_dict():
        return {
            'rank': coin_data['market_cap_rank'],
            'name': coin_data['name'],
            'symbol': coin_data['symbol'].upper(),
            'price': coin_data['current_price'],
            'market_cap': coin_data['market_cap']
        }

    if debug:
        start = time.perf_counter()

    update_saved_data = False

    if test and coins_json_file.is_file():
        if debug:
            print(
                f' {time.strftime("%H:%M:%S")} price data file ("{coins_json_file}") found, loading... ',
                end='', flush=True
            )

        with coins_json_file.open() as f:
            price_data = json.load(f)

    else:
        if debug:
            print(f' {time.strftime("%H:%M:%S")} downloading fresh price data... ', end='', flush=True)

        coin_ids = list(set(list(coins['holdings'].keys()) + list(coins['comparison'].keys())))
        params = {'ids': ','.join(coin_ids), 'vs_currency': currency}

        price_data = _do_request(url=coingecko_markets_url, params=params)
        #
        # price_data = requests.get(
        #     coingecko_markets_url, headers=coingecko_headers, params=params, timeout=request_timeout
        # ).json()
        update_saved_data = True

    for coin_data in price_data:
        if coin_data['id'] in coins['comparison']:
            # coins['comparison'][coin_data['id']] = get_coin_dict()
            coins['comparison'][coin_data['id']]['rank'] = coin_data['market_cap_rank']
            coins['comparison'][coin_data['id']]['name'] = coin_data['name']
            coins['comparison'][coin_data['id']]['symbol'] = coin_data['symbol'].upper()
            coins['comparison'][coin_data['id']]['price'] = coin_data['current_price']
            coins['comparison'][coin_data['id']]['market_cap'] = coin_data['market_cap']

        if coin_data['id'] in coins['holdings']:
            # coins['holdings'][coin_data['id']] = get_coin_dict()
            coins['holdings'][coin_data['id']]['rank'] = coin_data['market_cap_rank']
            coins['holdings'][coin_data['id']]['name'] = coin_data['name']
            coins['holdings'][coin_data['id']]['symbol'] = coin_data['symbol'].upper()
            coins['holdings'][coin_data['id']]['price'] = coin_data['current_price']
            coins['holdings'][coin_data['id']]['market_cap'] = coin_data['market_cap']

    if debug:
        print(f'done ({time.perf_counter() - start:,.3f}s)')

    if update_saved_data:
        if debug:
            start = time.perf_counter()
            print(f' {time.strftime("%H:%M:%S")} saving fresh price data ("{coins_json_file}")... ', end='', flush=True)

        with coins_json_file.open('w') as f:
            json.dump(price_data, f)

        if debug:
            print(f'done ({time.perf_counter() - start:,.3f}s)')

    return coins
