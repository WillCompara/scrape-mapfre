import csv
import json
import sys
import time
from datetime import datetime

import gspread
import pandas as pd
from playwright.sync_api import sync_playwright
from transitions import Machine

from reframework.process import run


class ReFramework(object):
    
    states = ['initialization', 'get_transaction_data', 'process', 'end_process']

    def __init__(self):
        self.machine = Machine(model=self, states=ReFramework.states, initial='initialization')
        self.machine.add_transition(trigger='successful', source='initialization', dest='get_transaction_data')
        self.machine.add_transition(trigger='failed_init', source='initialization', dest='end_process')
        self.machine.add_transition(trigger='new_transaction', source='get_transaction_data', dest='process')
        self.machine.add_transition(trigger='no_data', source='get_transaction_data', dest='end_process')
        self.machine.add_transition(trigger='se_exception', source='process', dest='initialization')
        self.machine.add_transition(trigger='success', source='process', dest='get_transaction_data')

        self.config = None
        self.queue = list()
        self.queue_report = list()
        self.transaction_item = dict()
        self.transaction_number = 1
        # self.retry_number = 0
        self.consecutive_system_exceptions = 0
        self.system_exception = None
        
        self.pw = sync_playwright().start()
        # self.pw = None
        self.page = None
        self.browser = None
        self.context = None


    def init_all_settings(self):
        print('Initializing settings...')
        with open('data/config.json', mode='r') as config:
            self.config = json.load(config)
        
        
    def kill_all_processes(self):
        print('Killing processes...')
        pass


    def init_all_apps(self):
        print('Opening applications...')
        self.browser = self.pw.firefox.launch(headless=self.config['headless'], 
                                              proxy={
                                                "username": "geonode_KnfQQsuBuJ-country-CL",
                                                "password": "e5efbcb4-2c3b-4239-96d2-7723d8ceacbb",
                                                "server": "premium-residential.geonode.com:9000",
                                            },
              )
        
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.set_default_timeout(700000)

        # Bloqueo de recursos innecesarios
        RESOURCE_EXCLUSIONS = ['image', 'media', 'font', 'other', 'stylesheet']
        self.page.route("**/*", lambda route: route.abort()
            if route.request.resource_type in RESOURCE_EXCLUSIONS
            else route.continue_()
        )
        # self.page.goto("https://nordvpn.com/what-is-my-ip/")

        # location = self.page.locator("span.js-ipdata-location").text_content()
        # ip = self.page.locator("h1.Title.h3.mb-6.js-ipdata-ip-address").text_content()
        # print(ip, "------->" ,location)
        #self.context.close()

    def add_to_queue(self):
        gc = gspread.service_account(filename='data/gspread_credentials.json')
        ws = gc.open(self.config['google_sheet']).worksheet(self.config['sheet_read'])
        df_queue = pd.DataFrame(ws.get_all_records())
        df_queue.to_csv('data/input/queue.csv', encoding='utf-8-sig', index=False)

        print('Adding items to queue...')
        with open('data/input/queue.csv', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=self.config['separator'])
            queue = list(csv_reader)
            for transaction in queue:
                transaction['retry_number'] = 0
            self.queue = queue

    
    def clean_worksheet(self):
        gc = gspread.service_account(filename='data/gspread_credentials.json')
        ws = gc.open(self.config['google_sheet']).worksheet(self.config['sheet_write'])
        ws.clear()
        columns = [
            'car',
            'brand',
            'model',
            'year',
            'plate',
            'rut',
            'birthdate',
            'comune',
            'email',
            'celular',
            'company',
            'product company',
            'compara product name',
            'company product name',
            'deductible',
            'price',
            'execute date',
            'quote ID',
            'obs',
            'execution time'
        ]

        df = pd.DataFrame(columns=columns)
        ws.update([df.columns.values.tolist()])


    def initialization(self):
        self.system_exception = None
        # If first run
        if self.config == None:
            self.init_all_settings()
            self.kill_all_processes()
            self.add_to_queue()
            self.clean_worksheet()

        if self.consecutive_system_exceptions == self.config['max_consecutive_system_exceptions']:
            raise Exception('End of process because of max number of consecutive system exceptions.')

        self.init_all_apps()


    def get_transaction_data(self):
        if len(self.queue) > 0:
            print('--------------------------------------------------------------------')
            print(f'Processing Transaction Number: {self.transaction_number}')
            transaction_item = self.queue.pop(0)
            self.transaction_item = transaction_item
        else:
            print('Process finished due to no more transaction data.')
            self.transaction_item = dict()


    def write_execution_report(self):
        now = datetime.now().strftime('%d-%m-%Y_%H%M%S')
        filename = f'execution_report_{now}.csv'
        with open(f'data/logs/{filename}', mode='w', newline='', encoding='utf-8-sig') as report_file:
            writer = csv.DictWriter(report_file, fieldnames=self.queue_report[0].keys(), delimiter=self.config['separator'])
            writer.writeheader()
            writer.writerows(self.queue_report)


    def end_process(self):
        self.close_all_apps()
        # if len(self.queue_report) > 0:
        #     self.write_execution_report()
        print('Process Finished.')
        if self.pw._loop.is_running():
            self.pw.stop()
        sys.exit(0)


    def retry_transaction(self):
        if self.transaction_item['retry_number'] == self.config['max_retry_number']:
            # self.retry_number = 0
            self.transaction_number += 1
        else:
            # self.retry_number += 1
            retry_transaction = self.transaction_item
            # print(retry_transaction)
            retry_transaction['retry_number'] += 1
            time.sleep(30)
            self.queue.append(self.transaction_item)


    def set_transaction_status(self):
        transaction_report = self.transaction_item.copy()
        if self.system_exception == None:
            print('Transaction Successful.')
            transaction_report['status'] = 'successful'
            self.queue_report.append(transaction_report)
            self.transaction_number += 1
            self.consecutive_system_exceptions = 0
        else:
            self.consecutive_system_exceptions += 1
            print(f'Transaction Failed. Consecutive system exception counter is {self.consecutive_system_exceptions}.')
            transaction_report['status'] = 'failed'
            self.queue_report.append(transaction_report)
            self.retry_transaction()
            self.close_all_apps()


    def close_all_apps(self):
        print('Closing applications...')
        try:
            self.context.close()
            self.browser.close()
            self.page.close()
        except:
            raise Exception('Error Closing Apps.')


    def process(self):
        print('Started Process')
        config = self.config
        transaction_item = self.transaction_item
        run(self.page, transaction_item, config)


    # -------------------------------------------------------------------------------------------------


def main():
    ref = ReFramework()
    while True:
        # Start of Initialization State <---------------------
        if ref.state == ReFramework.states[0]:
            try:
                ref.initialization()
                print(f"Initializating process: {ref.config['process_name']}")
            except Exception as se_init:
                print(se_init)
                ref.system_exception = se_init
            # Initialization Transitions <--------------------
            if ref.system_exception != None:
                ref.failed_init()
                ref.end_process()
            else:
                ref.successful()
        
        # Start of Get Transaction Data State <---------------
        ref.get_transaction_data()
        # Get Transaction Data Transitions <------------------
        if ref.transaction_item == {}:
            ref.no_data()
            ref.end_process()
        else:
            ref.new_transaction()

        # Start of Process State <----------------------------
        try:
            ref.process()
        # Process Transitions <-------------------------------
            ref.success()
        except Exception as se_process:
            print(se_process)
            ref.system_exception = se_process
        if ref.system_exception != None:
            ref.se_exception()
        ref.set_transaction_status()
        

if __name__ == '__main__':
    main()
