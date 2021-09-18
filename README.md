
Pyfolio2
===================
This is a Python (3.7+) tool to show you the value (in a currency of your choice, the default is USD) 
of your holdings in whatever coins you hold, updated to include earnings from ETH staking.

It won't show you if your holdings are up or down or whatever, it just gives you an at-a-glance total
according to the current prices on CoinGecko. If you're staking and you provide indexes of your 
validator(s), you will also see your earnings.

Installation
============
Extract the files into their own folder and run pyfolio2.py from a CLI environment (Command Prompt or 
PowerShell in Windows or any Linux terminal).

The config.ini file
===================
This is generated when you first run the script.

`show individual validators` - either show earnings per validator (as well as in total) or just the total.

`show bitcoin if not held` either include Bitcoin's price even if you don't include it in the
holdings file. To show other coins you don't hold, add them to the `holdings.ini` file with 0 held.

`show market caps` show the market caps section

`show market cap percentages` display each coin's market cap as a percentage of the coins you're comparing with 
(default BTC and ETH)

`compare to bitcoin` compare "Market cap" (if `show market caps` is set to True), "Price of 1" and "Value held" 
figures to Bitcoin

`compare to ethereum` compare "Market cap" (if `show market caps` is set to True), "Price of 1" and "Value held" 
figures to Ethereum

`compare to` specify other coins to use for the above comparisons

The `decimal places` fields are pretty self-explanatory, increase the values if you need higher accuracy.

The holdings.ini file
=====================
Included is a sample holdings.ini file. Ethereum is split into 3 subcategories - held, staked and earned. 
If you are not staking, put whatever ETH you hold into "held" and leave "validators" blank or remove it. 
If you are staking, put whatever ETH you *didn't* deposit into "held" and then list the indexes of your 
validators in "validators", separated by commas. That's all you need to do, the script will make an API 
call to beaconcha.in to calculate your earnings and, from the number of validators, how much you staked.

Enter any other coins you hold in the "other coins" section. Use either the name (eg: Ethereum) or the 
symbol (eg: ETH). If the app finds multiple coins that match whatever you entered, you'll be given a choice 
and the result will be saved. If you'd like to include coins that you don't hold for comparison, add them 
with 0 held


