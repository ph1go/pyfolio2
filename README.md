
Pyfolio2
===================
This is a Python (3.7+) tool to show you the value (in a currency of your choice, the default is USD) 
of your holdings in whatever coins you hold, updated to include earnings from ETH staking.

It won't show you if your holdings are up or down or whatever, it just gives you an at-a-glance total
according to the current prices on CoinMarketCap. If you're staking and you provide indexes of your 
validator(s), you will also see your earnings.

Installation
============
Extract the files into their own folder and run pyfolio2.py from a CLI environment (Command Prompt or 
PowerShell in Windows or any Linux terminal).

The config.ini file
===================
This is generated when you first run the script. You need a CoinMarketCap API key. To obtain one, go to 
https://pro.coinmarketcap.com/ and then paste it in when asked. 

The "number of coins" is how many coins are returned by the CoinMarketCap API call. The default is 200, 
if you hold coins that are ranked lower than that, increase it accordingly.

If "show bitcoin if not held" is True, Bitcoin's price will be shown even if you don't include it in the
holdings file.

The "decimal places" fields are pretty self-explanatory, increase the values if you need higher accuracy.

The holdings.ini file
=====================
Included is a sample holdings.ini file. Ethereum is split into 3 subcategories - held, staked and earned. 
If you are not staking, put whatever ETH you hold into "held" and leave "validators" blank or remove it. 
If you are staking, put whatever ETH you *didn't* deposit into "held" and then list the indexes of your 
validators in "validators", separated by commas. That's all you need to do, the script will make an API 
call to beaconcha.in to calculate your earnings and, from the number of validators, how much you staked.

Enter any other coins you hold in the "other coins" section. Use either the name (eg: Ethereum) or the 
symbol (eg: ETH). Case doesn't matter. If your coin isn't accepted and you're sure you entered either its
name or symbol correctly, check that the "number of coins" setting in config.ini is high enough to reach
that coin's rank.
