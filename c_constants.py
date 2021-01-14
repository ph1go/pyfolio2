from pathlib import Path
import configparser
import requests
from collections import namedtuple

this_path = Path(__file__).parent
config_file = this_path / 'config.ini'
holdings_file = this_path / 'holdings.ini'

cmc_json_file = this_path / 'cmc_data.json'
bc_json_file = this_path / 'bc_data.json'


def api_key_test(api_key):
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': api_key}
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info'
    parameters = {'slug': 'bitcoin'}
    cmc_data = requests.get(url, headers=headers, params=parameters).json()

    return cmc_data['status']


cfg = configparser.RawConfigParser()

if not config_file.is_file():
    print(
        '\n You need a CoinMarketCap API key in order to use this application. '
        'Goto https://pro.coinmarketcap.com/ if you need to create one.\n'
    )

    while True:
        api_key = input(' Enter your CoinMarketCap API key: ')
        status = api_key_test(api_key)

        if status['error_code'] == 0:
            break

        print(f' Invalid API key: {api_key}')

    cfg['coinmarketcap api'] = {}
    cfg['coinmarketcap api']['api key'] = api_key
    cfg['options'] = {
        'default currency': 'usd', 'number of coins': '200',
        'show individual validators': False, 'show bitcoin if not held': True
    }

    cfg['decimal places'] = {'fiat': '5', 'crypto': '5', 'percent': '3'}

    with config_file.open('w') as f:
        cfg.write(f)

    print(f'\n Config saved with default values. Open "{config_file}" to make changes.\n')

cfg.read(config_file)

api_key = cfg['coinmarketcap api'].get('api key', fallback=None)

if not api_key:
    print(' No CoinMarketCap API key found.')
    exit()

cmc_headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': api_key}

num_coins = cfg['options'].getint('number of coins', fallback=200)
currency = cfg['options'].get('default currency', fallback='usd')
split_validators = cfg['options'].getboolean('show individual validators', fallback=False)
show_bitcoin_if_not_held = cfg['options'].getboolean('show bitcoin if not held', fallback=True)

dp = namedtuple('dp', 'fiat crypto percent')
dp.fiat = cfg['decimal places'].getint('fiat', fallback=5)
dp.crypto = cfg['decimal places'].getint('crypto', fallback=5)
dp.percent = cfg['decimal places'].getint('percent', fallback=3)

details_in_name_col = True