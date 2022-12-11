# -*- coding: utf-8 -*-
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta

import cfscrape
import requests
from lxml import html

currentdir = os.path.dirname(os.path.realpath(__file__))
base_path = os.path.dirname(currentdir)
sys.path.append(base_path)
order_path = os.path.join('home/rinal/Рабочий стол/home/python_parsers/synapsenet', "last_order.txt")

from Send_report.Utils import send_to_api, prepare_data_for_send


class SynapsenetRu:
    def __init__(self):
        self.name = 'synapsenet.ru'
        self.session = cfscrape.create_scraper(sess=requests.Session())
        self.ads_count = 0

    def auth(self):
        time.sleep(random.uniform(7, 25))
        response = self.session.post('https://synapsenet.ru/account/login', data={
            'email': 'snegurka.zmurik18@gmail.com',
            'password': 'Qwertyuiop1234567890',
        }, timeout=30)

        if response.status_code == 200:
            return True

        return False

    def get_purchase_type(self, tree):
        title = ''
        try:
            title = tree.xpath("//ul[@class='tf-cd-requisites'][1]/li[1]/span[1]/text()")[0]
        except Exception as e:
            print('title error')
            print(e)

        return title

    def get_customer(self, tree):
        time.sleep(random.uniform(3, 5))

        url = 'https://synapsenet.ru{}'.format(''.join(tree.xpath("//a[@class='tf-customer']/@href")))
        if url == 'https://synapsenet.ru':
            return

        print('customer url {}'.format(url))

        customer = {}

        try:
            response = self.session.get(url, timeout=30)
            tree = html.document_fromstring(response.content.decode(response.encoding))

            inn = re.sub(r'[^\d]', '',
                         ''.join(tree.xpath("//div[@class='of-common-data'][2]/ul[@class='ofcd-requisites']/li[2]/text()")))
            kpp = re.sub(r'[^\d]', '',
                         ''.join(tree.xpath("//div[@class='of-common-data'][2]/ul[@class='ofcd-requisites']/li[3]/text()")))

            customer = {
                'factAddress': ''.join(tree.xpath("//div[@class='ofc-block'][1]/div/text()")),
                'fullName': ''.join(tree.xpath("//h1/text()")),
                'inn': inn,
                'kpp': kpp,
            }
        except Exception as e:
            print(e)

        return customer

    def get_end_date(self, tree):
        end_date = ''

        try:
            end_date = ''.join(tree.xpath("//meta[@itemprop='endDate']/@content")).replace('T', ' ')
        except Exception as e:
            print(e)

        return end_date

    def get_obesp_z(self, tree):
        for item in tree.xpath("//ul[@class='tf-cd-requisites']/li"):
            html_string = html.tostring(
                item, encoding='unicode', method='html', with_tail=False
            )
            item_tree = html.document_fromstring(html_string)

            if 'обеспечение заявки' in ''.join(item_tree.xpath("//text()")):
                return ''.join(item_tree.xpath("//span/text()"))

        return ''

    def get_obesp_i(self, tree):
        for item in tree.xpath("//ul[@class='tf-cd-requisites']/li"):
            html_string = html.tostring(
                item, encoding='unicode', method='html', with_tail=False
            )
            item_tree = html.document_fromstring(html_string)

            if 'обеспечение контракта' in ''.join(item_tree.xpath("//text()")):
                return ''.join(item_tree.xpath("//span/text()"))

        return ''

    def get_kladr_places(self, tree):
        kladr_places = []

        try:
            delivery_place = '{}, {}'.format(
                ''.join(tree.xpath("//span[@itemprop='addressRegion']/text()")),
                ''.join(tree.xpath("//span[@itemprop='addressLocality']/text()"))
            ).replace(' | ', '')
            kladr_places.append({
                'deliveryPlace': delivery_place
            })
        except Exception as e:
            print(e)

        return kladr_places

    def get_contact_person(self, tree):
        contact_person = {}

        for block in tree.xpath("//div[@class='tf-common-data']"):
            block_html_string = html.tostring(
                block, encoding='unicode', method='html', with_tail=False
            )
            block_tree = html.document_fromstring(block_html_string)

            if 'Контактное лицо' in ''.join(block_tree.xpath("//div/span/text()")):
                for item in block_tree.xpath("//li/text()"):
                    if 'email' in item:
                        contact_person['contactEMail'] = item.replace('email — ', '')
                    elif 'телефон' in item:
                        contact_person['contactPhone'] = re.sub(r'[^0-9]', '', item.replace('телефон — ', ''))
                    else:
                        try:
                            contact_person['lastName'] = item.split(' ')[0]
                        except Exception as e:
                            print(e)

                        try:
                            contact_person['firstName'] = item.split(' ')[1]
                        except Exception as e:
                            print(e)

                        try:
                            contact_person['middleName'] = item.split(' ')[2]
                        except Exception as e:
                            print(e)

        return contact_person

    def get_attachments(self, tree):
        attachments = []

        for item in tree.xpath("//div[@class='tf-docs-line']/a[@class='tender-link']"):
            html_string = html.tostring(
                item, encoding='unicode', method='html', with_tail=False
            )
            item_tree = html.document_fromstring(html_string)

            attachments.append({
                'docDescription': ''.join(item_tree.xpath("//text()")),
                'url': ''.join(item_tree.xpath("//@href")),
            })

        return attachments

    def get_data(self, item_url):
        time.sleep(random.uniform(3, 5))

        try:
            print('get data {}'.format(item_url))
            response = self.session.get(item_url, timeout=30)
            tree = html.document_fromstring(response.content.decode(response.encoding))

            purchase_type = self.get_purchase_type(tree)
            # if 'единств' in purchase_type.lower() or 'закрыт' in purchase_type.lower():
            #     return

            item_data = {
                'fz': 'Коммерческие',
                'purchaseNumber': ''.join(
                    tree.xpath("//div[@id='tender-full-header']/div[1]/div[1]/text()")
                ).replace('Тендер №', ''),
                'url': ''.join(tree.xpath("//a[@class='tfn-point'][1]/@href")),
                'title': ''.join(tree.xpath("//h1[@itemprop='name']/text()")),
                'purchaseType': purchase_type,

                'customer': self.get_customer(tree),

                'procedureInfo': {
                    'endDate': self.get_end_date(tree),
                },

                'lots': [
                    {
                        'price': ''.join(tree.xpath("//meta[@itemprop='price']/@content")),
                        'customerRequirements': [
                            {
                                'obesp_z': self.get_obesp_z(tree),
                                'obesp_i': self.get_obesp_i(tree),
                                # 'sumInPercents': sum_in_percents,
                                'kladrPlaces': self.get_kladr_places(tree),
                            }
                        ],
                        # 'lotItems': self.get_lot_items(lot, response.json()['short_trade_procedure']),
                    }
                ],

                'ETP': {
                    'name': ''.join(tree.xpath("//span[@class='tf-sourse-title']/text()")),
                },

                'contactPerson': self.get_contact_person(tree),
                'attachments': self.get_attachments(tree),
            }

            return item_data

        except Exception as e:
            print(e)

    def run(self):
        self.session.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36',
        }

        if self.auth() is False:
            print('ошибка авторизации')

            return

        date_from = str(datetime.strftime((datetime.now() - timedelta(days=1)), '%d.%m.%Y 00:00:00'))
        date_to = datetime.strftime((datetime.now()), '%d.%m.%Y 00:00:00')
        # date_from = str(datetime.strftime((datetime.now()), '%d.%m.%Y 00:00:00'))
        # date_to = str(datetime.strftime((datetime.now() + timedelta(days=1)), '%d.%m.%Y 00:00:00'))

        # ts_from = int(round(time.mktime(datetime.strptime(date_from, '%d.%m.%Y 00:00:00').timetuple())))
        # ts_to = int(round(time.mktime(datetime.strptime(date_to, '%d.%m.%Y 00:00:00').timetuple())))
        #
        # print('from: {}, to: {}'.format(ts_from, ts_to))
        print('from: {}, to: {}'.format(date_from, date_to))

        params = {
            'page': 1,
        }

        collected_urls = []

        completed = False
        required_date_found = False

        # номера заказов для остановки парсера
        yesterday_first_order = None
        today_first_order = None

        try:
            # считывает последний заказ с файла --> '№ 321103681501'
            with open(order_path, 'r', encoding='UTF-8') as f:
                yesterday_first_order = str(f.read()).strip()
                print(f'Прошлый заказ - {yesterday_first_order}')
        except Exception as e:
            print(f'Ошибка записи номера заказа в файл - {e}')

        for i in range(80):
            if completed is True or yesterday_first_order is None:
                break

            time.sleep(random.uniform(3, 5))

            print(params)

            response = self.session.get(
                # 'https://synapsenet.ru/pro/templates?templateId=149715&sortMode=10', сортировка по началу приема заявок
                'https://synapsenet.ru/pro/templates?templateId=149715&sortMode=4',  # сортировка по обновлению
                params=params,
                timeout=30
            )

            print(response.status_code)

            try:
                tree = html.document_fromstring(response.content.decode(response.encoding))
            except Exception as e:
                print(e)

                completed = True

                continue

            items = tree.xpath("//div[@id='sp-results-block']/div")

            if len(items) == 0:
                break

            required_date = (datetime.now() - timedelta(days=1)).date()
            # required_date = (datetime.now()).date()

            for item in items:
                html_string = html.tostring(
                    item, encoding='unicode', method='html', with_tail=False
                )
                item_tree = html.document_fromstring(html_string)
                class_name = ''.join(item_tree.xpath("//@class"))

                if 'sp-tb-right-block' in class_name:
                    number_order = ''.join(item_tree.xpath("//div[@class='sp-tb-right-block']/a/text()")).replace('посмотреть закупку', '')
                    number_order = number_order.strip()

                    if number_order == yesterday_first_order:
                        print('Найден последний заказ!')
                        completed = True
                        break

                    if not today_first_order:
                        today_first_order = number_order

                # if 'sp-time-line' in class_name:
                #     item_date = datetime.strptime(''.join(item_tree.xpath("//text()")).strip(), '%d.%m.%Y').date()
                #
                #     print(required_date, item_date)
                #
                #     if required_date < item_date:
                #         required_date_found = False
                #
                #         continue
                #
                #     if required_date > item_date and item_date.year > 2019:
                #         completed = True
                #
                #         continue
                #
                #     if required_date == item_date:
                #         required_date_found = True
                #
                #     continue

                # собирает ссылки
                # if required_date_found is True:
                #     item_url = 'https://synapsenet.ru{}'.format(''.join(item_tree.xpath("//a[@class='sp-tb-title']/@href")))
                #
                #     if item_url in collected_urls:
                #         continue
                #
                #     collected_urls.append(item_url)

                item_url = 'https://synapsenet.ru{}'.format(''.join(item_tree.xpath("//a[@class='sp-tb-title']/@href")))

                if item_url in collected_urls:
                    continue

                collected_urls.append(item_url)

            params['page'] += 1

        print('links count {}'.format(len(collected_urls)))

        ads = []
        for collected_url in collected_urls:
            item_data = self.get_data(collected_url)
            if item_data is None:
                continue

            ads.append(item_data)
            self.ads_count += 1

            if len(ads) > 49:
                send_to_api(ads)
                ads = []

            print('collected', self.ads_count)

        if len(ads) > 0:
            send_to_api(ads)

        try:
            if today_first_order:
                with open(order_path, 'w', encoding='UTF-8') as f:
                    print(today_first_order, file=f)
                    print(f'Запись стоп-заказа - {today_first_order}')
        except Exception as e:
            print(f'Ошибка записи номера заказа в файл - {e}')


if __name__ == '__main__':
    parser = SynapsenetRu()
    parser.run()
    print(parser.ads_count)
