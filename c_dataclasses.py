from dataclasses import dataclass, field, InitVar
from typing import List, Dict, ClassVar, Optional, Union
from functools import total_ordering
from operator import attrgetter
import json
import requests
import time

from c_constants import validators_json_file, dp, sort_vals_by_earnings, column_pad, separate_thousands


@dataclass
class Quantity:
    raw: float
    currency: str
    is_validator: bool = False
    formatted: str = field(init=False)

    dec_places: InitVar[int] = None
    pad_symbol: InitVar[bool] = False

    def __post_init__(self, dec_places: int, pad_symbol: bool):
        currency_pad = Coin.longest_symbol if pad_symbol else len(self.currency)
        if separate_thousands:
            self.formatted = (
                f'{self.raw:,.{dec_places}f} {self.currency:{currency_pad}}'
                if self.raw > 0 or self.is_validator else ''
            )

        else:
            self.formatted = (
                f'{self.raw:.{dec_places}f} {self.currency:{currency_pad}}'
                if self.raw > 0 or self.is_validator else ''
            )


    # def update_formatted_str(self, dec_places: int, padding: int):
    #     self.formatted = (
    #         f'{self.raw:,.{dec_places}f} {self.currency:<{padding}}' if self.raw > 0 or self.is_validator else ''
    #     )


@dataclass
class EthSubtype:
    short_str: str = ''
    long_str: str = ''
    quantity: Quantity = field(init=False)
    in_fiat: Quantity = field(init=False)
    comp_list_values_of_held: List[Union[str, Quantity]] = field(init=False, default_factory=list)

    raw: InitVar[float] = None
    fiat_value_of_one: InitVar[float] = None
    is_validator: InitVar[bool] = False

    def __post_init__(self, raw: float, fiat_value_of_one: float, is_validator: bool):
        self.quantity = Quantity(
            raw=raw, dec_places=dp.crypto, currency='ETH', is_validator=is_validator, pad_symbol=True
        )

        self.in_fiat = Quantity(
            raw=self.quantity.raw * fiat_value_of_one,
            dec_places=dp.fiat_total, currency=Coin.fiat_currency, is_validator=is_validator
        )

        for comp in Coin.comparison_coins:
            if comp.name.lower() == 'ethereum':
                self.comp_list_values_of_held.append('')

            else:
                self.comp_list_values_of_held.append(
                    Quantity(
                        raw=self.in_fiat.raw / comp.value_of_one.raw, currency=comp.symbol, dec_places=dp.crypto,
                    ).formatted
                )


@total_ordering
@dataclass
class Validator:
    index: str = field(init=False)
    public_key: str = field(init=False)
    val_str: str = field(init=False)
    balance: float = field(init=False)
    staked: EthSubtype = field(init=False)
    total: EthSubtype = field(init=False)
    earned: EthSubtype = field(init=False)
    percentage: Quantity = field(init=False, default=0)
    comp_list_staked_eth: List[Union[str, Quantity]] = field(init=False, default_factory=list)
    comp_list_earned_eth: List[Union[str, Quantity]] = field(init=False, default_factory=list)
    comp_list_total_eth: List[Union[str, Quantity]] = field(init=False, default_factory=list)

    val_dict: InitVar[Dict] = None
    fiat_value_of_one: InitVar[float] = None
    longest_val_index: InitVar[int] = None

    def __post_init__(self, val_dict: Dict, fiat_value_of_one: float, longest_val_index: int):
        self.index = str(val_dict['validatorindex'])
        self.public_key = val_dict['pubkey']
        self.val_str = f'Validator #{self.index} earnings'
        self.balance = val_dict['balance'] / 1000000000
        self.staked = EthSubtype(
            raw=32.0, short_str=f'{self.index:>{longest_val_index}}',
            fiat_value_of_one=fiat_value_of_one, is_validator=True
        )
        self.earned = EthSubtype(
            raw=self.balance - self.staked.quantity.raw, short_str=f'{self.index:>{longest_val_index}}',
            fiat_value_of_one=fiat_value_of_one, is_validator=True
        )
        self.total = EthSubtype(
            raw=self.balance, short_str=f'{self.index:>{longest_val_index}}',
            fiat_value_of_one=fiat_value_of_one, is_validator=True
        )

    def __eq__(self, other):
        return self.index == other.index

    def __lt__(self, other):
        return self.index < other.index


@total_ordering
@dataclass
class CoinBase:
    rank: int = field(init=False)
    name: str = field(init=False)
    symbol: str = field(init=False)
    market_cap: Quantity = field(init=False)
    value_of_one: Quantity = field(init=False)

    coin_data: InitVar[Dict] = None

    def __post_init__(self, coin_data: Dict):
        self.rank = coin_data['rank']
        self.name = coin_data['name']
        self.symbol = coin_data['symbol']
        self.market_cap = Quantity(raw=coin_data['market_cap'], currency=Coin.fiat_currency, dec_places=0)
        self.value_of_one = Quantity(raw=float(coin_data['price']), currency=Coin.fiat_currency, dec_places=dp.fiat)

    def __eq__(self, other):
        return self.rank == other.rank

    def __lt__(self, other):
        return self.rank < other.rank


@total_ordering
@dataclass
class Coin(CoinBase):
    comparison_coins: ClassVar[List[CoinBase]]
    total_held_in_fiat: ClassVar[Quantity]
    fiat_currency: ClassVar[str] = 'USD'
    comp_list_total_values: ClassVar[List[Quantity]] = []
    max_width_m_cap_percs: ClassVar[List[int]] = []
    max_width_prices_of_1: ClassVar[List[int]] = []
    max_width_values_of_held: ClassVar[List[int]] = []
    max_width_vals_staked: ClassVar[List[int]] = []
    max_width_vals_earned: ClassVar[List[int]] = []
    max_width_vals_total: ClassVar[List[int]] = []
    longest_symbol: ClassVar[int]
    is_staking_eth: ClassVar[bool] = False
    debug: ClassVar[bool] = False
    test: ClassVar[bool] = False

    comp_list_m_cap_percs: List[str] = field(init=False, default_factory=list)
    comp_list_prices_of_1: List[str] = field(init=False, default_factory=list)
    comp_list_values_of_held: List[str] = field(init=False, default_factory=list)
    comp_list_vals_staked: ClassVar[List[str]] = []
    comp_list_vals_earned: ClassVar[List[str]] = []
    comp_list_vals_total: ClassVar[List[str]] = []

    total_held: Optional[Quantity] = field(init=False, default=None)
    value_of_held: Quantity = field(init=False)
    perc_of_total: Quantity = field(init=False, default=0)

    qty_held: Optional[EthSubtype] = field(init=False, default=None)
    qty_staked: Optional[EthSubtype] = field(init=False, default=None)
    qty_earned: Optional[EthSubtype] = field(init=False, default=None)

    validator_indexes: List[str] = field(init=False, default_factory=list)
    validators: List[Validator] = field(init=False, default_factory=list)

    def __post_init__(self, coin_data: Dict):
        super().__post_init__(coin_data=coin_data)

        if self.name.lower() == 'ethereum':
            self.qty_held = EthSubtype(
                raw=coin_data['held'], short_str='Held', long_str='Held', fiat_value_of_one=self.value_of_one.raw
            )

            self.validator_indexes = coin_data.get('validators')

            if self.validator_indexes:
                bc_data = self.get_beaconchain_data()

                longest_val_index = len(str(max([str(x['validatorindex']) for x in bc_data], key=len)))

                self.validators = [
                    Validator(
                        val_dict=v, fiat_value_of_one=self.value_of_one.raw, longest_val_index=longest_val_index
                    )
                    for v in bc_data
                ]

                if sort_vals_by_earnings:
                    self.validators.sort(key=attrgetter('earned.quantity.raw'), reverse=True)

                else:
                    self.validators.sort()

                self.qty_staked = EthSubtype(
                    raw=sum([v.staked.quantity.raw for v in self.validators]),
                    short_str='Staked', long_str='Total staked',
                    fiat_value_of_one=self.value_of_one.raw
                )

                self.qty_earned = EthSubtype(
                    raw=sum([v.earned.quantity.raw for v in self.validators]),
                    short_str='Earned', long_str='Total earned',
                    fiat_value_of_one=self.value_of_one.raw, is_validator=True
                )

                Coin.is_staking_eth = True

            else:
                self.qty_staked = None
                self.qty_earned = None

            total_held = (
                self.qty_held.quantity.raw +
                (self.qty_staked.quantity.raw if self.qty_staked else 0) +
                (self.qty_earned.quantity.raw if self.qty_earned else 0)
            )

        else:
            total_held = coin_data['held']

        self.total_held = Quantity(raw=total_held, dec_places=dp.crypto, currency=self.symbol, pad_symbol=True)
        self.value_of_held = Quantity(
            raw=self.total_held.raw * self.value_of_one.raw, currency=Coin.fiat_currency, dec_places=dp.fiat_total
        )

        for comp in Coin.comparison_coins:
            if self.name == comp.name:
                self.comp_list_m_cap_percs.append('')
                self.comp_list_prices_of_1.append('')
                self.comp_list_values_of_held.append('')

            else:
                if self.name.lower() == 'ethereum' and Coin.is_staking_eth:
                    for v in self.validators:
                        v.comp_list_staked_eth.append(
                            Quantity(
                                raw=v.staked.in_fiat.raw / comp.value_of_one.raw,
                                currency=comp.symbol, dec_places=dp.crypto
                            ).formatted
                        )

                        v.comp_list_earned_eth.append(
                            Quantity(
                                raw=v.earned.in_fiat.raw / comp.value_of_one.raw,
                                currency=comp.symbol, dec_places=dp.crypto
                            ).formatted
                        )

                        v.comp_list_total_eth.append(
                            Quantity(
                                raw=v.total.in_fiat.raw / comp.value_of_one.raw,
                                currency=comp.symbol, dec_places=dp.crypto
                            ).formatted
                        )

                self.comp_list_m_cap_percs.append(
                    Quantity(
                        raw=(self.market_cap.raw / comp.market_cap.raw) * 100, currency='%', dec_places=dp.percent,
                    ).formatted
                )

                self.comp_list_prices_of_1.append(
                    Quantity(
                        raw=self.value_of_one.raw / comp.value_of_one.raw, currency=comp.symbol, dec_places=dp.crypto,
                    ).formatted
                )

                self.comp_list_values_of_held.append(
                    Quantity(
                        raw=self.value_of_held.raw / comp.value_of_one.raw, currency=comp.symbol, dec_places=dp.crypto,
                    ).formatted
                )

        if self.name.lower() == 'ethereum' and Coin.is_staking_eth:
            for comp in Coin.comparison_coins:
                self.comp_list_vals_staked.append(
                    Quantity(
                        raw=self.qty_staked.in_fiat.raw / comp.value_of_one.raw,
                        currency=comp.symbol, dec_places=dp.crypto
                    ).formatted
                )

                self.comp_list_vals_earned.append(
                    Quantity(
                        raw=self.qty_earned.in_fiat.raw / comp.value_of_one.raw,
                        currency=comp.symbol, dec_places=dp.crypto
                    ).formatted
                )

                self.comp_list_vals_total.append(
                    Quantity(
                        raw=(self.qty_staked.in_fiat.raw + self.qty_earned.in_fiat.raw) / comp.value_of_one.raw,
                        currency=comp.symbol, dec_places=dp.crypto
                    ).formatted
                )

            Coin.max_width_vals_staked = [len(x) for x in Coin.comp_list_vals_staked]
            Coin.max_width_vals_earned = [len(x) for x in Coin.comp_list_vals_earned]
            Coin.max_width_vals_total = [len(x) for x in Coin.comp_list_vals_total]

    def get_beaconchain_data(self):
        start = time.perf_counter()
        update_saved_data = False

        if Coin.test and validators_json_file.is_file():
            if Coin.debug:
                print(
                    f' {time.strftime("%H:%M:%S")} beaconcha.in data file ("{validators_json_file}") found, loading... ',
                    end='', flush=True
                )

            with validators_json_file.open() as f:
                bc_data = json.load(f)

        else:
            if Coin.debug:
                print(f' {time.strftime("%H:%M:%S")} downloading fresh beaconcha.in data... ', end='', flush=True)
                
            url = f'https://beaconcha.in/api/v1/validator/{",".join(self.validator_indexes)}'

            try:
                bc_data = requests.get(url).json()

            except json.decoder.JSONDecodeError:
                if validators_json_file.is_file():
                    print(
                        ' Bad JSON from beaconcha.in, loading locally saved validator balances from the last '
                        'successful call...'
                    )
                    with validators_json_file.open() as f:
                        bc_data = json.load(f)

                else:
                    print(' Bad JSON from beaconcha.in, no locally saved validator balances found.')
                    exit()

            else:
                update_saved_data = True
            
        if Coin.debug:
            print(f'done ({(time.perf_counter() - start):.3f}s)')

        if update_saved_data:
            if Coin.debug:
                start = time.perf_counter()
                print(f' {time.strftime("%H:%M:%S")} saving fresh beaconcha.in data ("{validators_json_file}")... ',
                      end='', flush=True)

            with validators_json_file.open('w') as f:
                json.dump(bc_data, f)

            if Coin.debug:
                print(f'done ({time.perf_counter() - start:,.3f}s)')

        data = bc_data['data']

        if Coin.debug:
            print()

        return data if isinstance(data, list) else [data]

    def __eq__(self, other):
        return self.rank == other.rank

    def __lt__(self, other):
        return self.rank < other.rank


@dataclass
class TableCol:
    width: int
    w_pad: int = field(init=False)

    def __post_init__(self):
        self.w_pad = self.width + (2 * column_pad)


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

    bot_left: str = '\u2558'
