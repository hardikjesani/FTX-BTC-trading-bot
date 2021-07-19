# -*- coding: utf-8 -*-

import simplejson as json
import ccxt
import algo
import datetime
import time

def read_setting():
        with open('setting.json') as json_file:
            return json.load(json_file)
                     
config = read_setting()

exchange  = ccxt.ftx({
    'verbose': False,
    'apiKey': config["apiKey"],
    'secret': config["secret"],
    'enableRateLimit': True,
    'headers': {
        'FTX-SUBACCOUNT': config["sub_account"],
    },
})


counter = 0
main_job = algo.Grid_trader(exchange,config["LOGFILE"],config["symbol"]\
                        ,config["coin"],config["stablecoin"],config["tp"]\
                        ,config["sl"],config["time_period_BB"]\
                        ,config["time_period_TEMA"],config["BB"])

while True:
    '''Price info for signal is taken at every 60 seconds and for ordering info is taken at
    every 20 seconds'''
    print("Loop in :",datetime.datetime.utcnow())
    
    if counter == 0:
        main_job.get_load()
        counter = 1
    else:
        main_job.order_decide()
        counter += 1
        if counter == 3: counter = 0
    time.sleep(20)