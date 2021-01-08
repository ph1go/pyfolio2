from dataclasses import dataclass, field, InitVar
from typing import List, Dict, ClassVar, Optional
from functools import total_ordering
import json
import requests
import time

from c_constants import bc_json_file, dp


@dataclass
class Quantity:
    raw: float
    currency: str
    formatted: str = field(init=False)

    dec_places: InitVar[int] = None

    def __post_init__(self, dec_places: int):
        self.formatted = f'{self.raw:,.{dec_places}f} {self.currency}' if self.raw > 0 else ''

    def update_formatted_str(self, dec_places: int, padding: int):
        self.formatted = f'{self.raw:,.{dec_places}f} {self.currency:<{padding}}' if self.raw > 0 else ''


@dataclass
class Subtype:
    quantity: float
    s_str: str = ''
    in_fiat: Quantity = field(init=False)
    in_btc: Quantity = field(init=False)
    in_eth: Quantity = field(init=False)

    fiat_value_of_one: InitVar[float] = None

    def __post_init__(self, fiat_value_of_one: float):
        self.in_fiat = Quantity(
            raw=self.quantity * fiat_value_of_one, dec_places=dp.fiat, currency=Coin.currency
        )

        self.in_btc = Quantity(raw=self.in_fiat.raw / Coin.btc_price, dec_places=dp.crypto, currency='BTC')
        self.in_eth = Quantity(raw=self.in_fiat.raw / Coin.eth_price, dec_places=dp.crypto, currency='ETH')


@dataclass
class Validator:
    index: int



@total_ordering
@dataclass
class Coin:
    btc_price: ClassVar[float]
    eth_price: ClassVar[float]
    fiat_total: ClassVar[Quantity]
    total_held_in_btc: ClassVar[Quantity]
    total_held_in_eth: ClassVar[Quantity]
    currency: ClassVar[str] = 'USD'
    debug: ClassVar[bool] = False
    test: ClassVar[bool] = False

    rank: int = field(init=False)
    name: str = field(init=False)
    symbol: str = field(init=False)
    #total_held: float = field(init=False)
    total_held: Optional[Quantity] = field(init=False, default=None)

    value_of_one: Subtype = field(init=False)
    value_of_held: Subtype = field(init=False)

    perc_of_total: Quantity = field(init=False)

    qty_held: Optional[Subtype] = field(init=False, default=None)
    qty_staked: Optional[Subtype] = field(init=False, default=None)
    qty_earned: Optional[Subtype] = field(init=False, default=None)

    validators: List[str] = field(init=False, default_factory=list)

    cmc_data: InitVar[Dict] = None
    ini_data: InitVar[Dict] = None

    def __post_init__(self, cmc_data: Dict, ini_data: Dict):
        self.rank = cmc_data['cmc_rank']
        self.name = cmc_data['name']
        self.symbol = cmc_data['symbol']
        fiat_value_of_one = float(cmc_data['quote'][Coin.currency.upper()]['price'])

        self.value_of_one = Subtype(quantity=1, fiat_value_of_one=fiat_value_of_one)

        held = ini_data.get('held')

        # if self.name.lower() == 'bitcoin':
        #

        if self.name.lower() == 'ethereum':
            self.qty_held = Subtype(quantity=ini_data['held'], s_str='held  ', fiat_value_of_one=fiat_value_of_one)
            self.validators = ini_data.get('validators')

            if self.validators:
                bc_data = self.get_beaconchain_data()
                    
                balance = sum([v['balance'] for v in bc_data])
                self.qty_staked = Subtype(quantity=32 * len(bc_data), s_str='staked', fiat_value_of_one=fiat_value_of_one)
                earned = (balance / 1000000000) - self.qty_staked.quantity
                self.qty_earned = Subtype(quantity=earned, s_str='earned', fiat_value_of_one=fiat_value_of_one)

            else:
                self.qty_staked = None
                self.qty_earned = None

            total_held = (
                self.qty_held.quantity +
                (self.qty_staked.quantity if self.qty_staked else 0) +
                (self.qty_earned.quantity if self.qty_earned else 0)
            )

        else:
            total_held = ini_data['held']

        self.total_held = Quantity(raw=total_held, dec_places=dp.crypto, currency=self.symbol)
        self.value_of_held = Subtype(quantity=self.total_held.raw, fiat_value_of_one=fiat_value_of_one)

    def get_beaconchain_data(self):
        if Coin.test:
            with bc_json_file.open() as f:
                bc_data = json.load(f)

        else:
            if Coin.debug:
                print(f' {time.strftime("%H:%M:%S")} downloading beaconcha.in data... ', end='', flush=True)
                b_start = time.perf_counter()
                
            url = f'https://beaconcha.in/api/v1/validator/{",".join(self.validators)}'
            bc_data = requests.get(url).json()

            with bc_json_file.open('w') as f:
                json.dump(bc_data, f)
            
            if Coin.debug:
                print(f'done ({(time.perf_counter() - b_start):.3f}s)')            

        return bc_data['data']

    def pad_held_str(self, longest_symbol, perc_of_total):
        self.total_held.update_formatted_str(dec_places=dp.crypto, padding=longest_symbol)

        if self.name.lower() == 'ethereum':
            self.qty_held.in_eth.update_formatted_str(dec_places=dp.crypto, padding=longest_symbol)

            try:
                self.qty_staked.in_eth.update_formatted_str(dec_places=dp.crypto, padding=longest_symbol)

            except AttributeError:
                pass

            else:
                self.qty_earned.in_eth.update_formatted_str(dec_places=dp.crypto, padding=longest_symbol)

        self.perc_of_total = Quantity(raw=perc_of_total, currency='%', dec_places=dp.percent)

    def __eq__(self, other):
        return self.rank == other.rank

    def __lt__(self, other):
        return self.rank < other.rank


@dataclass
class ElementRow:
    left: str
    mid_thin: str
    mid_thick: str
    right: str


@dataclass
class Elements:
    top: ElementRow = ElementRow(left='\u2554', mid_thin='\u2564', mid_thick='\u2566', right='\u2557')
    mid_thin: ElementRow = ElementRow(left='\u255f', mid_thin='\u253c', mid_thick='\u256b', right='\u2562')
    mid_thick: ElementRow = ElementRow(left='\u2560', mid_thin='\u256a', mid_thick='\u256c', right='\u2563')
    bot: ElementRow = ElementRow(left='\u255a', mid_thin='\u2567', mid_thick='\u2569', right='\u255d')

    ver_thin: str = '\u2502'
    ver_thick: str = '\u2551'
    hor_thin: str = '\u2500'
    hor_thick: str = '\u2550'
