import json
from operator import attrgetter

import time
import configparser
from typing import List

from c_api import is_valid_currency, get_coins_list, get_coin_prices

from c_constants import (
    holdings_file, split_validators, show_bitcoin_if_not_held, dp, show_btc_in_validator_view,
    details_in_name_col, sort_vals_by_earnings, show_market_caps, show_market_cap_percentages,
    compare_to_btc, compare_to_eth, compare_to, column_pad
)

from c_dataclasses import Coin, CoinBase, Validator, Quantity, Elements, TableCol


def get_holdings(debug=False, comparison_coins=None, validator_mode=False):
    def match_coin(coin_id):
        coin_ids = []
        for coin in coins_list:
            if coin_id.lower() in [coin['id'].lower(), coin['symbol'].lower(), coin['name'].lower()]:
                coin_ids.append(coin)

        if coin_ids:
            if len(coin_ids) > 1:
                print(f' Multiple holdings found matching "{coin_id}":')
                options = [str(x) for x in range(1, len(coin_ids)+1)]
                for idx, coin in enumerate(coin_ids, start=1):
                    print(f'{idx:>3}) {coin["name"]}')

                print()

                while True:
                    selection = input(' Select the number of the one you want from the list: ')
                    if selection in options:
                        sel_coin_id = coin_ids[int(selection)-1]['id'].lower()
                        break

            else:
                sel_coin_id = coin_ids[0]['id'].lower()

        else:
            print(f' No match found for "{coin_id}".')
            sel_coin_id = None

        return sel_coin_id

    coins_list = get_coins_list(debug=debug)

    matched_comp_coins = []
    for c in comparison_coins:
        if c and c is not None:
            matched_coin = match_coin(c)
            if matched_coin:
                matched_comp_coins.append(matched_coin)

    comparison = {}
    if len(matched_comp_coins) > 1:
        for c in matched_comp_coins:
            comparison[c] = {}

    else:
        if compare_to_btc:
            comparison['bitcoin'] = {}

        if compare_to_eth and not validator_mode:
            comparison['ethereum'] = {}

        if matched_comp_coins:
            comparison[match_coin(matched_comp_coins[0])] = {}

    if len(comparison) < 3:
        if 'bitcoin' not in comparison and compare_to_btc:
            comparison['bitcoin'] = {}

    if len(comparison) < 3 and not validator_mode:
        if 'ethereum' not in comparison and compare_to_eth:
            comparison['ethereum'] = {}

    start = time.perf_counter()
    if debug:
        print(
            f' {time.strftime("%H:%M:%S")} holdings file ("{holdings_file}") found, loading... ', end='', flush=True
        )

    cfg = configparser.RawConfigParser()
    cfg.read(holdings_file)

    holdings = {}

    if debug:
        print(f'done ({time.perf_counter() - start:,.3f}s)')

    try:
        eth = cfg['ethereum']

    except KeyError:
        try:
            eth = cfg['eth']

        except KeyError:
            eth = None

    if eth:
        if debug:
            print(f' {time.strftime("%H:%M:%S")} found "ethereum"')

        holdings['ethereum'] = {
            'held': eth.getfloat('held'), 'staked': eth.getfloat('staked'), 'validators': eth.get('validators', None)
        }

        if holdings['ethereum']['validators']:
            holdings['ethereum']['validators'] = [v.strip() for v in holdings['ethereum']['validators'].split(',')]

    other_coins = list(cfg['other coins'].keys())

    cfg_updated = False
    for other_coin_id in other_coins:
        selected_coin_id = match_coin(other_coin_id)
        selected_coin_holdings = cfg['other coins'].getfloat(other_coin_id)
        holdings[selected_coin_id] = {'held': selected_coin_holdings}

        if other_coin_id == selected_coin_id:
            if debug:
                print(f' {time.strftime("%H:%M:%S")} found "{selected_coin_id}"')

        else:
            cfg.remove_option('other coins', other_coin_id)
            cfg.set('other coins', selected_coin_id, selected_coin_holdings)

            if debug:
                print(f' {time.strftime("%H:%M:%S")} updated "{other_coin_id}" to "{selected_coin_id}"')

            cfg_updated = True

    if show_bitcoin_if_not_held and 'bitcoin' not in holdings.keys() and 'btc' not in holdings.keys():
        holdings['bitcoin'] = {'held': 0, 'comparison_only': True}

    if cfg_updated:
        if debug:
            start = time.perf_counter()
            print(f' {time.strftime("%H:%M:%S")} updating holdings file ("{holdings_file}")... ', end='', flush=True)

        with holdings_file.open('w') as f:
            cfg.write(f)

        if debug:
            print(f'done ({time.perf_counter() - start:,.3f}s)')

    return {'holdings': holdings, 'comparison': comparison}


def prepare_data(fiat_currency, args):
    print(f'\n {time.strftime("%A - %Y/%m/%d - %X")}\n')

    Coin.debug = debug = args.debug
    Coin.test = test = args.test

    if not is_valid_currency(fiat_currency):
        print(f' {time.strftime("%H:%M:%S")} invalid currency "{fiat_currency}" specified - reverting to "USD".')
        fiat_currency = 'USD'

        if not debug:
            print()

    Coin.fiat_currency = fiat_currency

    coins_json = get_holdings(
        debug=debug, comparison_coins=args.compare_to if args.compare_to else compare_to, validator_mode=args.validators
    )
    coins_json = get_coin_prices(coins=coins_json, currency=Coin.fiat_currency, debug=debug, test=test)

    if args.validators:
        Coin.longest_symbol = 3

    else:
        Coin.longest_symbol = len(max([coins_json['holdings'][c]['symbol'] for c in coins_json['holdings']], key=len))

    Coin.comparison_coins = [CoinBase(coin_data=coins_json['comparison'][c]) for c in coins_json['comparison']]
    Coin.comparison_coins.sort()

    coins = [Coin(coin_data=coins_json['holdings'][c]) for c in coins_json['holdings']]

    Coin.total_held_in_fiat = Quantity(
        raw=sum([c.value_of_held.raw for c in coins]), dec_places=dp.fiat, currency=Coin.fiat_currency
    )

    for coin in coins:
        perc_of_total = (coin.value_of_held.raw / Coin.total_held_in_fiat.raw) * 100
        coin.perc_of_total = Quantity(raw=perc_of_total, currency='%', dec_places=dp.percent)

    for c in Coin.comparison_coins:
        Coin.comp_list_total_values.append(
            Quantity(
                raw=Coin.total_held_in_fiat.raw / c.value_of_one.raw, currency=c.symbol, dec_places=dp.crypto
            ).formatted
        )

    for idx, comp in enumerate(Coin.comparison_coins):
        Coin.max_width_m_cap_percs.append(len(max([hold.comp_list_m_cap_percs[idx] for hold in coins], key=len)))
        Coin.max_width_prices_of_1.append(len(max([hold.comp_list_prices_of_1[idx] for hold in coins], key=len)))
        inc_totals = [hold.comp_list_values_of_held[idx] for hold in coins] + [Coin.comp_list_total_values[idx]]
        Coin.max_width_values_of_held.append(len(max(inc_totals, key=len)))

    return sorted(coins)


def display_data(coins):
    thin_held_sides = False
    col_pad = " " * column_pad
    e = Elements()

    len_rank = TableCol(width=max(3, len(str(max([c.rank for c in coins]))))+1)
    len_name = TableCol(width=max(9 if Coin.is_staking_eth else 4, len(str(max([c.name for c in coins], key=len)))))
    len_m_cap = TableCol(width=len(max([c.market_cap.formatted for c in coins], key=len)))
    len_price_of_1 = TableCol(width=max(10, len(max([c.value_of_one.formatted for c in coins], key=len))))
    len_held = TableCol(width=len(max([c.total_held.formatted for c in coins], key=len)))
    len_value_of_held = TableCol(width=max(10, len(Coin.total_held_in_fiat.formatted)))
    len_perc = TableCol(width=len(max([c.perc_of_total.formatted for c in coins], key=len)))

    extra_cols_perc = [TableCol(x) for x in Coin.max_width_m_cap_percs]
    extra_cols_price_of_1 = [TableCol(x) for x in Coin.max_width_prices_of_1]
    extra_cols_value_of_held = [TableCol(x) for x in Coin.max_width_values_of_held]

    header_str_m_cap = f'{e.ver_thick}{col_pad}{"Market cap":^{len_m_cap.width}}{col_pad}' if show_market_caps else ''
    header_str_price_of_1 = f'{col_pad}{"Price of 1":^{len_price_of_1.width}}{col_pad}'
    header_str_value_of_held = f'{col_pad}{"Value held":^{len_value_of_held.width}}{col_pad}'
    footer_str_total = f'{col_pad}{Coin.total_held_in_fiat.formatted:>{len_value_of_held.width}}{col_pad}'

    for idx, comp in enumerate(Coin.comp_list_total_values):
        footer_str_total += f'{col_pad}{comp:>{Coin.max_width_values_of_held[idx]}}{col_pad}'

    section_width_m_cap = len_m_cap.w_pad

    if show_market_caps and show_market_cap_percentages:
        section_width_m_cap += sum([c.w_pad for c in extra_cols_perc])

    section_width_price_of_1 = len_price_of_1.w_pad + sum([c.w_pad for c in extra_cols_price_of_1])
    section_width_value_held = len_value_of_held.w_pad + sum([c.w_pad for c in extra_cols_value_of_held])

    for idx, comp_coin in enumerate(Coin.comparison_coins):
        if show_market_caps and show_market_cap_percentages:
            _m_cap = f'{f"% of {comp_coin.symbol}":>{Coin.max_width_m_cap_percs[idx]}}'
            header_str_m_cap += f'{col_pad}{_m_cap}{col_pad}'

        _price_of_1 = f'{f"in {comp_coin.symbol}":>{Coin.max_width_prices_of_1[idx]}}'
        header_str_price_of_1 += f'{col_pad}{_price_of_1}{col_pad}'
        _value_of_held = f'{f"in {comp_coin.symbol}":>{Coin.max_width_values_of_held[idx]}}'
        header_str_value_of_held += f'{col_pad}{_value_of_held}{col_pad}'

    m_cap_top = e.top.mid_thick
    m_cap_mid_thick = e.mid_thick.mid_thick
    m_cap_mid_thin = e.mid_thin.mid_thick
    m_cap_blank = e.ver_thick
    m_cap_bottom = e.bot.mid_thick
    len_m_cap_bottom = 0

    if show_market_caps:
        m_cap_top += f'{e.hor_thick * section_width_m_cap}{e.top.mid_thick}'
        m_cap_mid_thick += f'{e.hor_thick * section_width_m_cap}{e.mid_thick.mid_thick}'
        m_cap_mid_thin += f'{e.hor_thin * section_width_m_cap}{e.mid_thin.mid_thick}'
        m_cap_blank += f'{" " * section_width_m_cap}{e.ver_thick}'
        m_cap_bottom += f'{e.hor_thick * section_width_m_cap}{e.bot.mid_thick}'
        len_m_cap_bottom += section_width_m_cap + 1

    held_top = e.top.mid_thin if thin_held_sides else e.top.mid_thick
    held_ver = e.ver_thin if thin_held_sides else e.ver_thick
    held_mid_thick = e.mid_thick.mid_thin if thin_held_sides else e.mid_thick.mid_thick
    held_mid_thin = e.mid_thin.mid_thin if thin_held_sides else e.mid_thin.mid_thick
    held_bottom_cross = e.mid_thick.mid_thin if thin_held_sides else e.mid_thick.mid_thick
    held_bottom = e.bot.mid_thin if thin_held_sides else e.bot.mid_thick

    top = (
        f'{e.top.left}{e.hor_thick * len_rank.w_pad}{e.top.mid_thick}'
        f'{e.hor_thick * len_name.w_pad}{m_cap_top}'
        f'{e.hor_thick * section_width_price_of_1}'
        f'{held_top}{e.hor_thick * len_held.w_pad}{held_top}'
        f'{e.hor_thick * section_width_value_held}{e.top.right}'
    )

    header = (
        f'{e.ver_thick}{col_pad}Rank{col_pad}'
        f'{e.ver_thick}{col_pad}{"Name":<{len_name.width}}{col_pad}'
        f'{header_str_m_cap}'
        f'{e.ver_thick}{header_str_price_of_1}'
        f'{held_ver}{col_pad}{"Held":^{len_held.width}}{col_pad}{held_ver}'
        f'{header_str_value_of_held}{e.ver_thick}'
    )

    mid_thick = (
        f'{e.mid_thick.left}{e.hor_thick * len_rank.w_pad}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * len_name.w_pad}{m_cap_mid_thick}'
        f'{e.hor_thick * section_width_price_of_1}'
        f'{held_mid_thick}{e.hor_thick * len_held.w_pad}{held_mid_thick}'
        f'{e.hor_thick * section_width_value_held}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * len_perc.w_pad}{e.top.right}'
    )

    mid_thin = (
        f'{e.mid_thin.left}{e.hor_thin * len_rank.w_pad}{e.mid_thin.mid_thick}'
        f'{e.hor_thin * len_name.w_pad}{m_cap_mid_thin}'
        f'{e.hor_thin * section_width_price_of_1}'
        f'{held_mid_thin}{e.hor_thin * len_held.w_pad}{held_mid_thin}'
        f'{e.hor_thin * section_width_value_held}{e.mid_thin.mid_thick}'
        f'{e.hor_thin * len_perc.w_pad}{e.mid_thin.right}'
    )

    blank_line = (
        f'{e.ver_thick}{" " * len_rank.w_pad}{e.ver_thick}{" " * len_name.w_pad}'
        f'{m_cap_blank}{" " * section_width_price_of_1}'
        f'{held_ver}{" " * len_held.w_pad}{held_ver}'
        f'{" " * section_width_value_held}{e.ver_thick}'
        f'{" " * len_perc.w_pad}{e.ver_thick}'
    )

    bottom = (
        f'{e.bot.left}{e.hor_thick * len_rank.w_pad}{e.bot.mid_thick}{e.hor_thick * len_name.w_pad}'
        f'{m_cap_bottom}{e.hor_thick * section_width_price_of_1}'
        f'{held_bottom}{e.hor_thick * len_held.w_pad}{held_bottom_cross}'
        f'{e.hor_thick * section_width_value_held}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * len_perc.w_pad}{e.bot.right}'
    )

    bottom_gap = (
        len_rank.w_pad + len_name.w_pad +
        section_width_price_of_1 + len_held.w_pad + 4 + len_m_cap_bottom
    )

    abs_bottom = (
        f'{" " * (bottom_gap - 7)}Total: {held_ver}'
        f'{footer_str_total}{e.ver_thick}\n '
        f'{" " * bottom_gap}{e.bot_left if thin_held_sides else e.bot.left}'
        f'{e.hor_thick * section_width_value_held}{e.bot.right}'
    )

    print(f' {top}\n {header}\n {mid_thick}')

    for coin_idx, coin in enumerate(coins):
        is_eth = True if coin.name.lower() == 'ethereum' else False
        coin_str_m_cap = e.ver_thick
        coin_str_m_cap_gap = e.ver_thick

        if show_market_caps:
            coin_str_m_cap = f'{e.ver_thick}{col_pad}{coin.market_cap.formatted:>{len_m_cap.width}}{col_pad}'
            coin_str_m_cap_gap = f'{e.ver_thick}{" " * section_width_m_cap}'

            if show_market_cap_percentages:
                for idx, m_cap_perc in enumerate(coin.comp_list_m_cap_percs):
                    coin_str_m_cap += f'{col_pad}{m_cap_perc:>{Coin.max_width_m_cap_percs[idx]}}{col_pad}'

            coin_str_m_cap += e.ver_thick
            coin_str_m_cap_gap += e.ver_thick

        coin_str_price_of_1 = f'{col_pad}{coin.value_of_one.formatted:>{len_price_of_1.width}}{col_pad}'
        for idx, price_of_1 in enumerate(coin.comp_list_prices_of_1):
            coin_str_price_of_1 += f'{col_pad}{price_of_1:>{Coin.max_width_prices_of_1[idx]}}{col_pad}'

        coin_str_value_of_held = f'{col_pad}{coin.value_of_held.formatted:>{len_value_of_held.width}}{col_pad}'
        for idx, value_of_held in enumerate(coin.comp_list_values_of_held):
            coin_str_value_of_held += f'{col_pad}{value_of_held:>{Coin.max_width_values_of_held[idx]}}{col_pad}'

        coin_str = (
            f'{e.ver_thick}{col_pad}{coin.rank:>{len_rank.width-1}}){col_pad}{e.ver_thick}'
            f'{col_pad}{coin.name:<{len_name.width}}{col_pad}{coin_str_m_cap}'
            f'{coin_str_price_of_1}'
            f'{held_ver}{col_pad}{coin.total_held.formatted:>{len_held.width}}{col_pad}{held_ver}'
            f'{coin_str_value_of_held}{e.ver_thick}'
            f'{col_pad}{coin.perc_of_total.formatted:>{len_perc.width}}{col_pad}{e.ver_thick}'
        )

        if is_eth and Coin.is_staking_eth and coin_idx > 0:
            print(f' {mid_thin}')

        print(f' {coin_str}')

        sub_line_start = f' {e.ver_thick}{col_pad}{"":{len_rank.width}}{col_pad}{e.ver_thick}'

        if is_eth and coin.qty_held and Coin.is_staking_eth:
            print(f' {blank_line}')
            eth_type_strs = {}
            for s in [coin.qty_held, coin.qty_staked, coin.qty_earned]:
                if s.short_str == 'TOTAL ETH':
                    name_str = f'{s.short_str:<{len_name.width}}'
                    perc_str = f'{coin.perc_of_total.formatted:>{len_perc.width}}'

                else:
                    name_str = f' - {s.short_str:<{len_name.width - 3}}'
                    perc_str = f'{"":{len_perc.width}}'

                if details_in_name_col:
                    s_details_str = f'{col_pad}{name_str}{col_pad}{coin_str_m_cap_gap}{" " * section_width_price_of_1}'

                else:
                    s_details_str = (
                        f'{"":{len_name.w_pad}}{coin_str_m_cap_gap}{col_pad}'
                        f'{s.long_str:>{section_width_price_of_1-2}}{col_pad}'
                    )

                eth_sub_str = f'{col_pad}{s.in_fiat.formatted:>{len_value_of_held.width}}{col_pad}'

                for idx, eth_sub in enumerate(s.comp_list_values_of_held):
                    eth_sub_str += f'{col_pad}{eth_sub:>{Coin.max_width_values_of_held[idx]}}{col_pad}'

                coin_str_value_of_held = f'{col_pad}{s.in_fiat.formatted:>{len_price_of_1.width}}{col_pad}'
                for idx, value_of_held in enumerate(coin.comp_list_prices_of_1):
                    coin_str_value_of_held += f'{col_pad}{value_of_held:>{Coin.max_width_prices_of_1[idx]}}{col_pad}'

                subtype_str = (
                    f'{sub_line_start}{s_details_str}'
                    f'{held_ver}{col_pad}{s.quantity.formatted:>{len_held.width}}{col_pad}{held_ver}'
                    f'{eth_sub_str}{e.ver_thick}'
                    f'{col_pad}{perc_str}{col_pad}{e.ver_thick}'
                )

                eth_type_strs[s.short_str] = subtype_str

            print(f'{eth_type_strs["Held"]}\n{eth_type_strs["Staked"]}\n{eth_type_strs["Earned"]}')

            if split_validators and len(coin.validators) > 1:
                print(f' {blank_line}')

                for v in coin.validators:
                    if details_in_name_col:
                        v_details_str = (
                            f'{col_pad}  - {v.index:<{len_name.width - 4}}{col_pad}{coin_str_m_cap_gap}'
                            f'{" " * section_width_price_of_1}'
                        )

                    else:
                        v_details_str = (
                            f'{"":{len_name.w_pad}}{coin_str_m_cap_gap}{col_pad}{v.val_str:>{section_width_price_of_1-2}}{col_pad}'
                        )

                    val_str = f'{col_pad}{v.earned.in_fiat.formatted:>{len_value_of_held.width}}{col_pad}'

                    for idx, val_earned in enumerate(v.earned.comp_list_values_of_held):
                        val_str += f'{col_pad}{val_earned:>{Coin.max_width_values_of_held[idx]}}{col_pad}'

                    print(
                        f'{sub_line_start}{v_details_str}'
                        f'{held_ver}{col_pad}{v.earned.quantity.formatted:>{len_held.width}}{col_pad}{held_ver}'
                        f'{val_str}'
                        f'{e.ver_thick}'
                        f'{col_pad}{" " * len_perc.width}{col_pad}{e.ver_thick}'
                    )

            if coin_idx + 1 < len(coins) and Coin.is_staking_eth:
                print(f' {mid_thin}')

    print(f' {bottom}\n {abs_bottom}\n')


def display_validators(validators: List[Validator]):
    col_pad = " " * column_pad
    e = Elements()

    staked_in_eth_total = Quantity(
        raw=sum([v.staked.quantity.raw for v in validators]), dec_places=dp.fiat, currency='ETH'
    ).formatted

    staked_in_fiat_total = Quantity(
        raw=sum([v.staked.in_fiat.raw for v in validators]), dec_places=dp.fiat, currency=Coin.fiat_currency
    ).formatted

    earned_in_eth_total = Quantity(
        raw=sum([v.earned.quantity.raw for v in validators]), dec_places=dp.fiat, currency='ETH'
    ).formatted

    earned_in_fiat_total = Quantity(
        raw=sum([v.earned.in_fiat.raw for v in validators]), dec_places=dp.fiat, currency=Coin.fiat_currency
    ).formatted

    _total_eth = sum([v.total.quantity.raw for v in validators])

    total_in_eth_total = Quantity(
        raw=_total_eth, dec_places=dp.fiat, currency='ETH'
    ).formatted

    total_in_fiat_total = Quantity(
        raw=sum([v.total.in_fiat.raw for v in validators]), dec_places=dp.fiat, currency=Coin.fiat_currency
    ).formatted

    len_rank = TableCol(width=max(3, len(str(len(validators))))+1)
    len_index = TableCol(width=max(5, len(max([v.index for v in validators], key=len))))
    len_staked_eth = TableCol(width=len(staked_in_eth_total))
    len_staked_fiat = TableCol(width=len(staked_in_fiat_total))
    len_earned_eth = TableCol(width=len(earned_in_eth_total))
    len_earned_fiat = TableCol(width=len(earned_in_fiat_total))
    len_total_eth = TableCol(width=len(total_in_eth_total))
    len_total_fiat = TableCol(width=len(total_in_fiat_total))

    for validator in validators:
        perc = (validator.total.quantity.raw / _total_eth) * 100
        validator.percentage = Quantity(raw=perc, currency='%', dec_places=dp.percent)

    len_percentage = TableCol(width=len(max([v.percentage.formatted for v in validators], key=len)))

    section_width_staked = len_staked_eth.w_pad + len_staked_fiat.w_pad
    section_width_earned = len_earned_eth.w_pad + len_earned_fiat.w_pad
    section_width_total = len_total_eth.w_pad + len_total_fiat.w_pad

    staked_header_str = (
        f'{col_pad}{"STAKED":>{len_staked_eth.width}}{col_pad}'
        f'{col_pad}{f"in {Coin.fiat_currency}":>{len_staked_fiat.width}}{col_pad}'
    )

    earned_header_str = (
        f'{col_pad}{"EARNED":>{len_earned_eth.width}}{col_pad}'
        f'{col_pad}{f"in {Coin.fiat_currency}":>{len_earned_fiat.width}}{col_pad}'
    )

    total_header_str = (
        f'{col_pad}{"TOTAL":>{len_total_eth.width}}{col_pad}'
        f'{col_pad}{f"in {Coin.fiat_currency}":>{len_total_fiat.width}}{col_pad}'
    )

    staked_total_str = (
        f'{col_pad}{staked_in_eth_total:>{len_staked_eth.width}}{col_pad}'
        f'{col_pad}{staked_in_fiat_total:>{len_staked_fiat.width}}{col_pad}'
    )

    earned_total_str = (
        f'{col_pad}{earned_in_eth_total:>{len_earned_eth.width}}{col_pad}'
        f'{col_pad}{earned_in_fiat_total:>{len_earned_fiat.width}}{col_pad}'
    )

    total_total_str = (
        f'{col_pad}{total_in_eth_total:>{len_total_eth.width}}{col_pad}'
        f'{col_pad}{total_in_fiat_total:>{len_total_fiat.width}}{col_pad}'
    )

    for idx, comp_coin in enumerate(Coin.comparison_coins):
        header_str = f'in {comp_coin.symbol}'

        staked_width = Coin.max_width_vals_staked[idx]
        earned_width = Coin.max_width_vals_earned[idx]
        total_width = Coin.max_width_vals_total[idx]

        section_width_staked += staked_width + (2 * column_pad)
        section_width_earned += earned_width + (2 * column_pad)
        section_width_total += total_width + (2 * column_pad)

        staked_header_str += f'{col_pad}{header_str:>{staked_width}}{col_pad}'
        staked_total_str += f'{col_pad}{Coin.comp_list_vals_staked[idx]:>{staked_width}}{col_pad}'

        earned_header_str += f'{col_pad}{header_str:>{earned_width}}{col_pad}'
        earned_total_str += f'{col_pad}{Coin.comp_list_vals_earned[idx]:>{earned_width}}{col_pad}'

        total_header_str += f'{col_pad}{header_str:>{total_width}}{col_pad}'
        total_total_str += f'{col_pad}{Coin.comp_list_vals_total[idx]:>{total_width}}{col_pad}'

    top = (
        f'{e.top.left}'
        f'{e.hor_thick * len_rank.w_pad}{e.top.mid_thick}'
        f'{e.hor_thick * len_index.w_pad}{e.top.mid_thick}'
        f'{e.hor_thick * section_width_staked}{e.top.mid_thin}'
        f'{e.hor_thick * section_width_earned}{e.top.mid_thin}'
        f'{e.hor_thick * section_width_total}'
        f'{e.top.right}'
    )

    header = (
        f'{e.ver_thick}{col_pad}Rank{col_pad}{e.ver_thick}{col_pad}{"Index":<{len_index.width}}{col_pad}{e.ver_thick}'
        f'{staked_header_str}{e.ver_thin}{earned_header_str}{e.ver_thin}{total_header_str}'
        f'{e.ver_thick}'
    )

    body_top = (
        f'{e.mid_thick.left}'
        f'{e.hor_thick * len_rank.w_pad}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * len_index.w_pad}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * section_width_staked}{e.mid_thick.mid_thin}'
        f'{e.hor_thick * section_width_earned}{e.mid_thick.mid_thin}'
        f'{e.hor_thick * section_width_total}{e.mid_thick.mid_thick}'
        f'{e.hor_thick * len_percentage.w_pad}{e.top.right}'
    )

    body_bottom = (
        f'{e.bot.left}{e.hor_thick * len_rank.w_pad}'
        f'{e.bot.mid_thick}{e.hor_thick * len_index.w_pad}'
        f'{e.mid_thick.mid_thick}{e.hor_thick * section_width_staked}'
        f'{e.mid_thick.mid_thin}{e.hor_thick * section_width_earned}'
        f'{e.mid_thick.mid_thin}{e.hor_thick * section_width_total}'
        f'{e.mid_thick.mid_thick}{e.hor_thick * len_percentage.w_pad}{e.bot.right}'
    )

    total_pad = len_rank.w_pad + len_index.w_pad + 2

    total_total_line = (
        f'{"Total: ":>{total_pad}}{e.ver_thick}'
        f'{staked_total_str}{e.ver_thin}{earned_total_str}{e.ver_thin}{total_total_str}{e.ver_thick}'
    )

    bottom = (
        f'{" " * total_pad}{e.bot.left}'
        f'{e.hor_thick * section_width_staked}{e.bot.mid_thin}'
        f'{e.hor_thick * section_width_earned}{e.bot.mid_thin}'
        f'{e.hor_thick * section_width_total}{e.bot.right}'
    )

    print(f' {top}\n {header}\n {body_top}')

    for v_idx, val in enumerate(validators):
        staked_line = (
            f'{col_pad}{val.staked.quantity.formatted:>{len_staked_eth.width}}{col_pad}'
            f'{col_pad}{val.staked.in_fiat.formatted:>{len_staked_fiat.width}}{col_pad}'
        )

        earned_line = (
            f'{col_pad}{val.earned.quantity.formatted:>{len_earned_eth.width}}{col_pad}'
            f'{col_pad}{val.earned.in_fiat.formatted:>{len_earned_fiat.width}}{col_pad}'
        )

        total_line = (
            f'{col_pad}{val.total.quantity.formatted:>{len_total_eth.width}}{col_pad}'
            f'{col_pad}{val.total.in_fiat.formatted:>{len_total_fiat.width}}{col_pad}'
        )

        for c_idx, comp in enumerate(Coin.comparison_coins):
            staked_line += f'{col_pad}{val.comp_list_staked_eth[c_idx]:>{Coin.max_width_vals_staked[c_idx]}}{col_pad}'
            earned_line += f'{col_pad}{val.comp_list_earned_eth[c_idx]:>{Coin.max_width_vals_earned[c_idx]}}{col_pad}'
            total_line += f'{col_pad}{val.comp_list_total_eth[c_idx]:>{Coin.max_width_vals_total[c_idx]}}{col_pad}'

        validator_line = (
            f'{e.ver_thick}{col_pad}{v_idx+1:>{len_rank.width-1}}){col_pad}'
            f'{e.ver_thick}{col_pad}{val.index:>{len_index.width}}{col_pad}'
            f'{e.ver_thick}{staked_line}{e.ver_thin}{earned_line}{e.ver_thin}{total_line}{e.ver_thick}'
            f'{col_pad}{val.percentage.formatted:>{len_percentage.width}}{col_pad}'
            f'{e.ver_thick}'
        )

        print(f' {validator_line}')

    print(f' {body_bottom}\n {total_total_line}\n {bottom}\n')
