#!/usr/bin/env python
"""
Created on Tue May 30 09:40:29 2017

@author: johnfroiland
"""
#
# OANDA Imports
#
import argparse
import common.config
import common.args
from view import mid_string, heartbeat_to_string, currency_string
from order_response import print_order_create_response_transactions
#from decimal import *
#getcontext().prec = 4

#
# Project Imports
#
import pandas as pd
pd.set_option('display.large_repr', 'truncate')
pd.set_option('display.max_columns', 0)
from datetime import datetime
#import threading
#import sys
#sys.stdout.write('\a')
#sys.stdout.flush()
import os
os.system('say "Cool."')


def main():
    
    #
    # Stream the prices for a list of Instruments for the active Account.
    #
    #print "------ System online -------", datetime.now()

    parser = argparse.ArgumentParser()

    common.config.add_argument(parser)
    
    parser.add_argument(
        '--instrument', "-i",
        type=common.args.instrument,
        required=True,
        action="append",
        help="Instrument to get prices for"
    )

    parser.add_argument(
        '--snapshot',
        action="store_true",
        default=True,
        help="Request an initial snapshot"
    )

    parser.add_argument(
        '--no-snapshot',
        dest="snapshot",
        action="store_false",
        help="Do not request an initial snapshot"
    )

    parser.add_argument(
        '--show-heartbeats', "-s",
        action='store_true',
        default=False,
        help="display heartbeats"
    )

    args = parser.parse_args()
    account_id = args.config.active_account
    
    api = args.config.create_streaming_context()    
    account_api = args.config.create_context()
    #
    # Fetch the details of the Account found in the config file
    #
    account_response = account_api.account.summary(account_id)
    keys = account_response.get("account").__dict__.keys()
    values = account_response.get("account").__dict__.values()
    account_details = zip(keys,values)
    account_details = account_details[17][1]
    #
    # Subscribe to the pricing stream
    #
    response = api.pricing.stream(
        account_id,
        snapshot=args.snapshot,
        instruments=",".join(args.instrument),
    )
    
    """
        # Need to create two separate threads: One for the trading loop
        # and another for the market price streaming class
        
        trade_thread = threading.Thread(target=trade_response)
        price_thread = threading.Thread(target=response)
    
        # Start both threads
        print("Starting trading thread")
        trade_thread.start()
        print("Starting price streaming thread")
        price_thread.start()
    """
    """
        df: Used to track streams of pricing data as they are received.
        minuteData: Tracks df data and resamples it to OHLC every minute.
        positions: Temporarily stores prices in DataFrame when establishing or 
            closing a position. Saves to csv the trades initiated and results.
    """
    df = pd.DataFrame([])
    minuteData = pd.DataFrame([])
    open_instrument = pd.DataFrame({'Instrument':[None]})
    open_units = pd.DataFrame({'Units':[None]})
    open_long = pd.DataFrame({'Long':[None]})
    open_short = pd.DataFrame({'Short':[None]})
    trade_id = pd.DataFrame({'TradeID':[None]})
    profit = pd.DataFrame({'Profit':[None]})
    loss = pd.DataFrame({'Loss':[None]})
    positions = pd.DataFrame([])
    positions = pd.concat([open_instrument,open_units,open_long,open_short,
                           trade_id,profit,loss],axis=1, join='outer')
    #
    # Print out each price as it is receive
    #       
    for msg_type, msg in response.parts():
        if msg_type == "pricing.Heartbeat" and args.show_heartbeats:
            print heartbeat_to_string(msg)
            
        if msg_type == "pricing.Price":
            #print(price_to_string(msg))
            
            #now = datetime.strptime(printer.time_value(candle), "%Y-%m-%d %H:%M:%S")
            #print now
            now = datetime.now()
            df5 = pd.DataFrame({'Time':[now]})
            df6 = pd.DataFrame({'Mid':[float(mid_string(msg))]})
            df7 = pd.concat([df5,df6], axis=1, join='inner')
            df7 = df7.set_index(['Time'])
            df7.index = pd.to_datetime(df7.index, unit='s')
            df = df.append(df7)
            
            #
            # Resample the data to OHLC candles and indexed by Timestamp
            #
            xx = df.to_period(freq="s")
            openCol2 = xx.resample("5min").first()
            highCol2 = xx.resample("5min").max()
            lowCol2 = xx.resample("5min").min()
            closeCol2 = xx.resample("5min").last()
            minuteData = pd.concat([openCol2,highCol2,lowCol2,closeCol2],
                                   axis=1, join='inner')
            
            minuteData['Open'] = openCol2.round(5)
            minuteData['High'] = highCol2.round(5)
            minuteData['Low'] = lowCol2.round(5)
            minuteData['Close'] = closeCol2.round(5)
            minuteData['20 High Close'] = minuteData['Close'].rolling(20).max()
            minuteData['20 Low Close'] = minuteData['Close'].rolling(20).min()
            minuteData['10 High Close'] = minuteData['Close'].rolling(10).max()
            minuteData['10 Low Close'] = minuteData['Close'].rolling(10).min()
            minuteData['HL'] = minuteData['High']-minuteData['Low']
            minuteData['HC'] = minuteData['High']-minuteData['Close']
            minuteData['CL'] = minuteData['Close']-minuteData['Low']
            minuteData['True Range'] = minuteData[['HL','HC','CL']].max(axis=1).round(5)
            minuteData['N'] = minuteData['True Range'].rolling(20).mean().round(5)
            minuteData['$Volatility'] = minuteData['N']*minuteData['Close']*50
            minuteData['Account'] = .01 * account_details
            minuteData['Lot Size'] = minuteData['Account']/minuteData['$Volatility']
            try:
                minuteData['Lot Size'] = minuteData['Lot Size'].fillna(0.0).astype(int)
            except: pass
            minuteData = minuteData[['Open','High','Low','Close','20 High Close',
                        '10 High Close','20 Low Close','10 Low Close','True Range',
                        'N','$Volatility','Lot Size']]
           
            """
            if: LONG position
                    
                    Checks to see if new HIGH is greater than the HIGH of the 
                    20 Period HIGH Close. It then checks to see that the LONG 
                    position value in the positions DataFrame is NONE. 
                    If so, it initiates a MARKET order.
            
            elif: SHORT position
                    
                    Checks to see if new LOW is greater than the LOW of the 
                    20 Period LOW Close. It then checks to see that the SHORT 
                    position value in the positions DataFrame is NONE. 
                    If so, it initiates a MARKET order.  
                    
            elif: LONG Take Profit
            
            elif: SHORT Take Profit
            
            elif: STOP LOSS for Open SHORT position
                
                    Checks to see if new High is greater than the high of the 
                    10 Period High Close. It then checks to see if there is an open 
                    short position value in the positions DataFrame. If so, it 
                    initiates a Stop for the position.

            elif: STOP LOSS for Open LONG position
                    
                    Checks to see if new LOW is greater than the LOW of the 
                    10 Period LOW Close. It then checks to see if there is an 
                    open LONG position value in the positions DataFrame. 
                    If so, it initiates a STOP for the position.    
            """
            
            if (
                    minuteData.shape[0] > 19 and \
                    minuteData.iloc[-1]['High'] > minuteData.iloc[-2]['20 High Close'] and \
                    positions.iloc[0]['TradeID'] is None
                ):
                api = args.config.create_context()
                units = minuteData['Lot Size'][-1].astype('str')
                currency = currency_string(msg)
                #
                # Long
                #
                trade_response = api.order.market(
                    account_id,
                    instrument=currency,
                    units=units
                )
                if currency_string(msg) == 'AUD_USD':
                    os.system('say "Long, Aussie."')
                elif currency_string(msg) == 'EUR_USD':
                    os.system('say "Long, Euro."')
                elif currency_string(msg) == 'USD_CAD':
                    os.system('say "Long, Loonie."')
                elif currency_string(msg) == 'GBP_USD':
                    os.system('say "Long, Cable."')
                elif currency_string(msg) == 'USD_CHF':
                    os.system('say "Long, Swiss."')
            
                tradeID = trade_response.get('lastTransactionID')
                keys = trade_response.get('orderFillTransaction').__dict__.keys()
                values = trade_response.get('orderFillTransaction').__dict__.values()
                orderFill = zip(keys,values)
                profit = Decimal(orderFill[6][1] * 1.001)
                loss = Decimal(orderFill[6][1]/1.001)
                #
                # Process the response
                #
                print("Response: {} ({})".format(
                        trade_response.status,trade_response.reason))
                print("")
                print_order_create_response_transactions(trade_response)
                #
                # Enter Trade Into DataFrame
                #
                positions['Profit'] = profit
                positions['Loss'] = loss
                positions['TradeID'] = tradeID
                positions['Instrument'] = currency_string(msg)
                positions['Units'] = minuteData['Lot Size'][-1].astype('str')
                positions['Long'] = minuteData.iloc[-1]['High']
                positions = positions[['Instrument','Units','Long',
                                       'Short','TradeID','Profit','Loss']]
             
            elif (
                    minuteData.shape[0] > 19 and \
                    minuteData.iloc[-1]['Low'] < minuteData.iloc[-2]['20 Low Close'] and \
                    positions.iloc[0]['TradeID'] is None
                ):
                api = args.config.create_context()
                units = int(minuteData['Lot Size'][-1].astype('str'))*-1
                currency = currency_string(msg)
                #
                # Short
                #
                trade_response = api.order.market(
                    account_id,
                    instrument=currency,
                    units=units
                )
                if currency_string(msg) == 'AUD_USD':
                    os.system('say "Short, Aussie."')
                elif currency_string(msg) == 'EUR_USD':
                    os.system('say "Short, Euro."')
                elif currency_string(msg) == 'USD_CAD':
                    os.system('say "Short, Loonie."')
                elif currency_string(msg) == 'GBP_USD':
                    os.system('say "Short, Cable."')
                elif currency_string(msg) == 'USD_CHF':
                    os.system('say "Short, Swiss."')
                
                tradeID = trade_response.get('lastTransactionID')
                keys = trade_response.get('orderFillTransaction').__dict__.keys()
                values = trade_response.get('orderFillTransaction').__dict__.values()
                orderFill = zip(keys,values)
                profit = Decimal(orderFill[6][1]/1.001)
                loss = Decimal(orderFill[6][1] * 1.001)
                #
                # Process the response
                #
                print("Response: {} ({})".format(
                        trade_response.status,trade_response.reason))
                print("")
                print_order_create_response_transactions(trade_response)
                #
                # Enter Trade Into DataFrame
                #
                positions['Profit'] = profit
                positions['Loss'] = loss
                positions['TradeID'] = tradeID
                positions['Instrument'] = currency_string(msg)
                positions['Units'] = int(minuteData['Lot Size'][-1].astype('str'))*-1
                positions['Short'] = minuteData.iloc[-1]['Low']
                positions = positions[['Instrument','Units','Long',
                                       'Short','TradeID','Profit','Loss']]
                
            elif (
                    Decimal(mid_string(msg)) >= positions.iloc[0]['Profit'] and \
                    positions.iloc[0]['Long'] is not None
                ):
                price = positions.iloc[0]['Profit']
                tradeID = positions.iloc[0]['TradeID']
                currency = currency_string(msg)
                #
                # Long Profit
                #
                profit_response = api.order.take_profit(
                    account_id,
                    instrument=currency,
                    tradeID=tradeID,
                    price=price
                )
                #
                # Process the response
                #
                print("Response: {} ({})".format(
                        profit_response.status,profit_response.reason))
                print("")
                #keys = profit_response.get('orderFillTransaction').__dict__.keys()
                #values = profit_response.get('orderFillTransaction').__dict__.values()
                #orderFill = zip(keys,values)
                #print 'Take Profit Trade Executed', orderFill
                print_order_create_response_transactions(profit_response)
                #
                # Remove Trade From DataFrame
                #
                positions['TradeID'] = None
                positions['Profit'] = None
                positions['Loss'] = None
                positions['Instrument'] = None
                positions['Units'] = None
                positions['Long'] = None
                positions = positions[['Instrument','Units','Long',
                                       'Short','TradeID','Profit','Loss']]
            
            elif (
                    Decimal(mid_string(msg)) <= positions.iloc[0]['Profit'] and \
                    positions.iloc[0]['Short'] is not None
                ):
                price = positions.iloc[0]['Profit']
                tradeID = positions.iloc[0]['TradeID']
                currency = currency_string(msg)
                #
                # Short Profit
                #
                profit_response = api.order.take_profit(
                    account_id,
                    instrument=currency,
                    tradeID=tradeID,
                    price=price
                )
                #
                # Process the response
                #
                print("Response: {} ({})".format(
                        profit_response.status,profit_response.reason))
                print("")
                #keys = profit_response.get('orderFillTransaction').__dict__.keys()
                #values = profit_response.get('orderFillTransaction').__dict__.values()
                #orderFill = zip(keys,values)
                #print 'Take Profit Trade Executed', orderFill
                print_order_create_response_transactions(profit_response)
                #
                # Remove Trade From DataFrame
                #
                positions['TradeID'] = None
                positions['Profit'] = None
                positions['Loss'] = None
                positions['Instrument'] = None
                positions['Units'] = None
                positions['Short'] = None
                positions = positions[['Instrument','Units','Long',
                                       'Short','TradeID','Profit','Loss']]
                   
            elif (
                    Decimal(mid_string(msg)) <= positions.iloc[0]['Loss'] and
                    positions.iloc[0]['Long'] is not None
                ):
                api = args.config.create_context()
                price = positions.iloc[0]['Loss']
                tradeID = positions.iloc[0]['TradeID']
                currency = currency_string(msg)
                #
                # Stop Loss for Long
                #
                loss_response = api.order.stop_loss(
                    account_id,
                    instrument=currency,
                    tradeID=tradeID,
                    price=price
                )
                if currency_string(msg) == 'AUD_USD':
                    os.system('say "Long stop loss, Aussie."')
                elif currency_string(msg) == 'EUR_USD':
                    os.system('say "Long stop loss, Euro."')
                elif currency_string(msg) == 'USD_CAD':
                    os.system('say "Long stop loss, Loonie."')
                elif currency_string(msg) == 'GBP_USD':
                    os.system('say "Long stop loss, Cable."')
                elif currency_string(msg) == 'USD_CHF':
                    os.system('say "Long stop loss, Swiss."')
            
                #
                # Process the response
                #
                #print minuteData
                print("Response: {} ({})".format(
                        loss_response.status,loss_response.reason))
                print("")
                print_order_create_response_transactions(loss_response)
                #
                # Remove Trade From DataFrame
                #
                positions['TradeID'] = None
                positions['Profit'] = None
                positions['Loss'] = None
                positions['Instrument'] = None
                positions['Units'] = None
                positions['Long'] = None
                positions = positions[['Instrument','Units','Long',
                                       'Short','TradeID','Profit','Loss']]
                  
            elif (
                    Decimal(mid_string(msg)) >= positions.iloc[0]['Loss'] and
                    positions.iloc[0]['Short'] is not None
                ):
                api = args.config.create_context()
                price = positions.iloc[0]['Loss']
                tradeID = positions.iloc[0]['TradeID']
                currency = currency_string(msg)
                #
                # Stop Loss for Short
                #
                loss_response = api.order.stop_loss(
                    account_id,
                    instrument=currency,
                    tradeID=tradeID,
                    price=price
                )
                if currency_string(msg) == 'AUD_USD':
                    os.system('say "Short stop loss, Aussie."')
                elif currency_string(msg) == 'EUR_USD':
                    os.system('say "Short stop loss, Euro."')
                elif currency_string(msg) == 'USD_CAD':
                    os.system('say "Short stop loss, Loonie."')
                elif currency_string(msg) == 'GBP_USD':
                    os.system('say "Short stop loss, Cable."')
                elif currency_string(msg) == 'USD_CHF':
                    os.system('say "Short stop loss, Swiss."')
                #
                # Process the response
                #
                #print minuteData
                print("Response: {} ({})".format(
                        loss_response.status,loss_response.reason))
                print("")
                print_order_create_response_transactions(loss_response)
                #
                # Remove Trade From DataFrame
                #
                positions['Profit'] = None
                positions['Loss'] = None
                positions['TradeID'] = None
                positions['Instrument'] = None
                positions['Units'] = None
                positions['Short'] = None
                positions = positions[['Instrument','Units','Long',
                                       'Short','TradeID','Profit','Loss']]
            
            print "df:",df.shape[0]," minuteData:",minuteData.shape[0]
            
          
if __name__ == "__main__":
    main()
