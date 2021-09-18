from pathlib import Path
import configparser
import requests
from collections import namedtuple

this_path = Path(__file__).parent
config_file = this_path / 'config.ini'
holdings_file = this_path / 'holdings.ini'

coins_list_json_file = this_path / 'coins_list.json'
coins_json_file = this_path / 'price_data.json'
validators_json_file = this_path / 'validators_data.json'

coingecko_base_url = 'https://api.coingecko.com/api/v3/'
coingecko_currencies_url = coingecko_base_url + 'simple/supported_vs_currencies'
coingecko_coins_url = coingecko_base_url + 'coins/list'
coingecko_markets_url = coingecko_base_url + 'coins/markets'
coingecko_prices_url = coingecko_base_url + 'simple/price'
coingecko_headers = {'accept': 'application/json'}

request_timeout = 10

cfg = configparser.RawConfigParser()

if not config_file.is_file():
    cfg['options'] = {
        'default currency': 'usd',
        'show individual validators': True,
        'show bitcoin if not held': True,
        'show market caps': True,
        'show market cap percentages': True,
        'compare to bitcoin': True,
        'compare to ethereum': True,
        'compare to': None
    }

    cfg['decimal places'] = {'fiat': '5', 'crypto': '5', 'percent': '3'}

    with config_file.open('w') as f:
        cfg.write(f)

    print(f'\n Config saved with default values. Open "{config_file}" to make changes.\n')

cfg.read(config_file)

currency = cfg['options'].get('default currency', fallback='usd')
split_validators = cfg['options'].getboolean('show individual validators', fallback=False)
show_bitcoin_if_not_held = cfg['options'].getboolean('show bitcoin if not held', fallback=True)
show_market_caps = cfg['options'].getboolean('show market caps', fallback=True)
show_market_cap_percentages = cfg['options'].getboolean('show market cap percentages', fallback=True)
compare_to_btc = cfg['options'].getboolean('compare to bitcoin', fallback=True)
compare_to_eth = cfg['options'].getboolean('compare to ethereum', fallback=True)
_compare_to = cfg['options'].get('compare to', fallback='')
compare_to = [x.strip() for x in _compare_to.split(',')]

# if compare_to is not None and not compare_to:
#     compare_to = []

dp = namedtuple('dp', 'fiat crypto percent')
dp.fiat = cfg['decimal places'].getint('fiat', fallback=5)
dp.crypto = cfg['decimal places'].getint('crypto', fallback=5)
dp.percent = cfg['decimal places'].getint('percent', fallback=3)

# table options
column_pad = 1
details_in_name_col = True
sort_vals_by_earnings = True
show_btc_in_validator_view = False
separate_thousands = True
