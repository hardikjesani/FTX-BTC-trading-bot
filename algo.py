# coding=utf-8

import ccxt
import pandas as pd
import numpy as np
import talib as ta
import time
import datetime


LOGFILE=""

'''loading live price'''
temp_data= pd.Series(data=np.random.rand(36),index=[i for i in range(36)], dtype=('float'))

buy_price = 0
id_for_close = 0

class Oreder_Info:
    def __init__(self):
        #self.done=False
        self.side=None
        self.id=0

class Grid_trader:

    def __init__(self,exchange,logfile,symbol,coin,fiat,tp=0.0,sl=0.0,time_period_BB=0.0,time_period_TEMA=0.0, BB=0.0):
        '''get basic data from exhchange and json file to start'''
        self.symbol = symbol
        self.logfile = logfile
        self.exchange=exchange
        self.BB = BB
        self.tp = 1 + tp/100
        self.sl = 1 - sl/100
        self.time_period_BB=time_period_BB
        self.time_period_TEMA=time_period_TEMA
        self.coin = coin
        self.fiat = fiat
        ##to check if coin is already bought and save buying price
        global buy_price
        buy_price = self.send_request("get_trades")
        
    
    def get_load(self):
        '''combine data for last 36 minutes and generate Bollinger Bands and Triple EMA'''
        
        self.bid, self.ask = self.send_request("get_bid_ask_price")
        
        global temp_data
        live_data = temp_data
        live_data = live_data[1:].append(pd.Series(self.ask))
        live_data.reset_index(drop =True,inplace=True)
        

        global bb_data
        bb_data=pd.DataFrame(live_data, columns=[ 'price'])
        bb_data['ub'], bb_data['mb'], bb_data['lb'] = ta.BBANDS(bb_data['price'], timeperiod =self.time_period_BB, nbdevup = self.BB, nbdevdn = self.BB)    
        bb_data['tema']=ta.TEMA(bb_data['price'], timeperiod=self.time_period_TEMA)
        temp_data = live_data
        self.order_decide()
        
    def send_request(self,task,input1=None,input2=None,amount=None,order_close_id=None):
        '''various exchange calls'''
        
        tries = 5
        for i in range(tries):
            try:
                if task == "get_bid_ask_price":
                    ticker =self.exchange.fetch_ticker(self.symbol)
                    return ticker["bid"],  ticker["ask"]
                elif task == "get_balance":
                    return self.exchange.fetchBalance()

                elif task == "get_order":
                    return self.exchange.fetchOrder(input1)["info"]
                
                elif task == "get_trades":
                    trade = self.exchange.fetchMyTrades(symbol = self.symbol, limit = 1)
                    if trade[0]["side"] == "buy":
                        return trade[0]["price"]
                    else:
                        return None
                
                elif task == "cancel_order":
                    self.exchange.cancelOrder(order_close_id)

                elif task == "place_order":
                    #send_request(self,task,input1=side,input2=price,amount)
                    side = input1
                    price = input2
                    orderid=0
                    
                    if side =="buy":
                        orderid = self.exchange.create_limit_buy_order(self.symbol,amount,price )["info"]["id"]
                    else:
                        orderid = self.exchange.create_limit_sell_order(self.symbol,amount,price )["info"]["id"]
                    return orderid

                else:
                    return None
            except ccxt.NetworkError as e:
                if i < tries - 1: # i is zero indexed
                    msg = ("NetworkError , try last "+str(i) +"chances" + str(e))
                    self.log(msg)
                    time.sleep(5)
                    continue
                else:
                    self.log(str(e))
                    raise
            except ccxt.ExchangeError as e:
                if i < tries - 1: # i is zero indexed
                    self.log(str(e))
                    time.sleep(0.5)
                    continue
                else:
                    self.log(str(e))
                    raise
            break
    
    
    
            
    def order_decide(self):
        '''trading decision'''
        
        order =Oreder_Info()
        balance = self.send_request('get_balance')
        self.bid, self.ask = self.send_request("get_bid_ask_price")
        
        ##buy
        try:
            if balance[self.fiat]['free']>3:##decrceased from 10 to 3
                
                if self.ask < bb_data.lb.iloc[-1] and bb_data.lb.iloc[-1] < bb_data.tema.iloc[-1]:
                    print('buy_tirggered')
                    quantity = round(balance[self.fiat]['free']/self.ask,5)
                    print(quantity)
                    order.id = self.send_request("place_order","buy",self.ask,quantity)
                    msg = ("place buy order id = " + str(order.id) + " in "+ str(self.ask))
                    self.log(msg)
                    
                    #order closing confirmation in 30 seconds else cancel
                    signal_close = False
                    count = 0
                    while signal_close == False:
                        order_info = self.send_request("get_order",order.id)
                        if order_info["status"] == "closed":
                            signal_close = True
                            global buy_price
                            buy_price = float(order_info["price"])
                            
                        else:
                            time.sleep(5)
                            count =count+5
                            
                        if count == 30:
                            signal_close = True
                            self.send_request('cancel_order', order_close_id=str(order.id))
                            msg = ("cancel buy id = " + str(order.id) + " in "+ str(self.bid))
                            self.log(msg) 
        except:
            pass
        
        ##sell
        try:
            if balance[self.coin]['free']>0.0001:
                
                if buy_price*self.tp<= self.bid or buy_price*self.sl>= self.bid :
                    quntity = balance[self.coin]['free']
                    order.id = self.send_request("place_order","sell",self.bid,quntity)##removed 1.002
                    msg = ("place sell order id = " + str(order.id) + " in "+ str(self.bid))
                    self.log(msg)
                    
                    #order closing confirmation in 30 seconds else cancel
                    signal_close = False
                    count = 0
                    while signal_close == False:
                        order_info = self.send_request("get_order",order.id)
                        if order_info["status"] == "closed":
                            signal_close = True
                                                        
                        else:
                            time.sleep(5)
                            count =count+5
                            
                        if count == 30:
                            signal_close = True
                            self.send_request('cancel_order', order_close_id=str(order.id))
                            msg = ("cancel sell id = " + str(order.id) + " in "+ str(self.bid))
                            self.log(msg)
        except:
            pass
    

    def log(self, msg):
        timestamp = datetime.datetime.now().strftime("%b %d %Y %H:%M:%S ")
        s = "[%s]: %s" % (timestamp, msg)
        print(s)
        try:
            f = open(self.logfile, "a")
            f.write(s + "\n")
            f.close()
        except:
            pass
    
