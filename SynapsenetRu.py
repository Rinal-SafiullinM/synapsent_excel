# -*- coding: utf-8 -*-
import os
import random
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import openpyxl.worksheet.ole
import openpyxl
import cfscrape
import requests
from lxml import html
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

currentdir = os.path.dirname(os.path.realpath(__file__))
base_path = os.path.dirname(currentdir)
sys.path.append(base_path)
sys.path.append('/home/manage_report')

from Send_report.mywrapper import magicDB


class SynapsenetRu:
    def __init__(self):
        logging.basicConfig(filename='synapsenet.log', format='%(filename)s: %(message)s',
                            level=logging.DEBUG)
        self.name = 'synapsenet.ru'
        self.session = cfscrape.create_scraper(sess=requests.Session())
        self.ads_count = 0
        self.session.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36',
        }
        self.domain = 'https://synapsenet.ru'
        if os.name == 'nt':
            self.chrome_path = 'chromedriver/chromedriver.exe'
        if os.name == 'posix':
            self.chrome_path = '/home/service/chromedriver'
        self.chrome_options = Options()
        self.chrome_options.add_argument('start-maximized')
        self.chrome_options.add_argument('enable-automation')

        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        self.chrome_options.add_experimental_option("prefs", {
            "download.default_directory": r"/home/python_parsers/tendery/synapsenet/synapsenetru_parser",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })

        s = Service(executable_path=self.chrome_path)
        self.webdriver = webdriver.Chrome(service=s, options=self.chrome_options)

    def auth(self):
        time.sleep(random.uniform(7, 25))
        self.webdriver.get('https://synapsenet.ru/home/login')
        self.webdriver.find_element(By.XPATH, '//input[@name="email"]').send_keys('snegurka.zmurik18@gmail.com')
        self.webdriver.find_element(By.XPATH, '//input[@name="password"]').send_keys('Qwertyuiop1234567890')
        self.webdriver.find_element(By.XPATH, '//input[@class="demand-submit"]').click()
        time.sleep(random.uniform(7, 25))

        return True

    def download(self):
        try:
            path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'download.xlsx')
            os.remove(path)
            print('File deleted')
        except Exception as e:
            print(e)
            logging.info('Error in deleting file')
        self.webdriver.get('https://synapsenet.ru/pro/templatesloadfile?templateId=149715&sortMode=4')
        time.sleep(random.uniform(7, 25))
        print('File downloaded')
        p = Path(r'/home/python_parsers/tendery/synapsenet/synapsenetru_parser/download')
        p.rename(p.with_suffix('.xlsx'))
        logging.info('Dowloading xlsx file')
        time.sleep(random.uniform(7, 25))

    @magicDB
    def parse_excel(self):
        ads = []
        book = openpyxl.load_workbook(r'/home/python_parsers/tendery/synapsenet/synapsenetru_parser/download.xlsx')
        sheet = book.active
        try:
            for i in range(3,1003):
                item_data = {
                    'fz': 'Коммерческие',
                    'purchaseNumber': sheet[i][10].value,
                    'url': sheet[i][0].hyperlink.target,
                    'title': sheet[i][0].value[0:499],
                    'purchaseType': '',
                    'customer':
                        {
                         'fullName': sheet[i][2].value,
                         'inn': '',
                         'kpp': '',
                         },
                    'procedureInfo': {
                        'endDate': sheet[i][6].value
                    },

                    'lots': [
                        {
                            'price': sheet[i][3].value,
                            'customerRequirements': [
                                {
                                    'obesp_z': '',
                                    'obesp_i':'',
                                    'kladrPlaces': sheet[i][4].value,
                                }
                            ],
                        }
                    ],
                    'ETP': {
                        'name': '',
                    },

                    'contactPerson':
                        {
                            'contactName': sheet[i][7].value,
                            'contactPhone': sheet[i][8].value,
                            'contactEMail': sheet[i][9].value
                        },
                    'attachments': '',
                }
                if sheet[i][7].value is None: 
                    item_data['contactPerson']['contactName'] = ''
                if sheet[i][8].value is None: 
                    item_data['contactPerson']['contactPhone'] = ''
                if sheet[i][9].value is None: 
                    item_data['contactPerson']['contactEMail'] = ''
                if sheet[i][8].value is None:
                    item_data['contactPerson']['contactPhone'] = ''
                url = sheet[i][2].hyperlink
                if url is not None:
                    url = sheet[i][2].hyperlink.target
                else:
                    pass
                if url is not None:
                    try:
                        response = self.session.get(url, timeout=30, headers=self.session.headers)
                        tree = html.document_fromstring(response.content.decode(response.encoding))
                        inn = re.sub(r'[^\d]', '',
                                     ''.join(tree.xpath(
                                         "/html/body/div[2]/div[3]/div[4]/div/div[1]/div[1]/div[2]/div[2]/text()")))
                        kpp = re.sub(r'[^\d]', '',
                                     ''.join(tree.xpath(
                                         "/html/body/div[2]/div[3]/div[4]/div/div[1]/div[1]/div[3]/div[2]/text()")))
                        item_data['customer']['inn'] = inn
                        item_data['customer']['kpp'] = kpp
                    except Exception as e:
                        print(e)
                else:
                    pass
                ads.append(item_data)
                print('Data added')
                self.ads_count += 1
            data = {'name': 'synapsenetru',
                    'data': ads}
            print('collected', self.ads_count)
            return data
           
        except Exception as e:
            logging.info('Error in collecting data from xlsx file')
            print(e)
   
    def run(self):
        start_time = datetime.now()
        if self.auth() is False:
            print('Authorization error')

            return
        date_from = str(datetime.strftime((datetime.now() - timedelta(days=1)), '%d.%m.%Y 00:00:00'))
        date_to = datetime.strftime((datetime.now()), '%d.%m.%Y 00:00:00')
        print('from: {}, to: {}'.format(date_from, date_to))
        #Download file
        self.download()
        #Parse xlsx file
        self.parse_excel()
        self.webdriver.close()
        print(datetime.now() - start_time)
        logging.info(f'Working time:{datetime.now() - start_time}')



if __name__ == '__main__':
    parser = SynapsenetRu()
    parser.run()
    sys.exit(1)
