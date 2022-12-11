# -*- coding: utf-8 -*-
import json
import re
import os
import sys
import urllib
from datetime import datetime, timedelta

import chardet
import pytesseract
import requests

from Locations.Handler import get_region_by_string, get_region_id


def download(url, filepath):
    try:
        with open(filepath, "wb") as file:
            response = requests.get(url)
            file.write(response.content)
    except:
        return False

    return True


def delete_file(filepath):
    try:
        os.remove(filepath)
    except:
        return False

    return True


def text_recognize(filepath):
    # image = os.path.abspath('temp/phone.png')
    image = os.path.abspath(filepath)
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    # custom_config = r'--oem 3 --psm 13'
    # text = pytesseract.image_to_string(image, config=custom_config)
    text = pytesseract.image_to_string(image)

    return text


def prepare_phone(phone):
    return re.sub(r'[^0-9]', '', phone)


def prepare_fz_item(item):
    item['type'] = 2

    #if 'ETP' in item:
    #    del item['ETP'] 

    if 'procedureInfo' in item and 'startDate' in item['procedureInfo']:
        del item['procedureInfo']['startDate']

    if 'contactPerson' in item and 'contactPhone' in item['contactPerson']:
        item['contactPerson']['contactPhone'] = prepare_phone(item['contactPerson']['contactPhone'])

    # if 'customer' in item:
    #     item['customer']['inn']

    try:
        if 'purchaseType' in item:
            if 'procedureInfo' not in item:
                item['procedureInfo'] = {}

            if 'единствен' in item['purchaseType'].lower():
                item['procedureInfo']['endDate'] = str(datetime.strftime(datetime.date(datetime.now()), '%d.%m.%Y'))

            elif 'endDate' not in item['procedureInfo'] or item['procedureInfo']['endDate'] == '':
                item['procedureInfo']['endDate'] = str(
                    datetime.strftime((datetime.date(datetime.now()) + timedelta(days=7)), '%d.%m.%Y')
                )
    except Exception as e:
        print('Ошибка изменения даты в тендерах', e)

    lot_num = 0
    for lot in item['lots']:
        region_name = None
        if 'region' in lot:
            region_name = get_region_by_string(lot['region'])

        if region_name is None and 'address' in lot:
            region_name = get_region_by_string(lot['address'])

        if region_name is not None:
            item['lots'][lot_num]['region_id'] = get_region_id(region_name)

        okpd_list = []
        if 'lotItems' in lot:
            for lot_item in lot['lotItems']:
                if 'code' in lot_item and lot_item['code'] in okpd_list:
                    item['lots'][lot_num]['lotItems'].remove(lot_item)

                    continue

                if 'name' in lot_item and lot_item['name'] in okpd_list:
                    item['lots'][lot_num]['lotItems'].remove(lot_item)

                    continue

                for item_name in ['name', 'code']:
                    if item_name in lot_item:
                        okpd_list.append(lot_item[item_name])

        if 'customerRequirements' in lot:
            customer_requirement_num = 0
            for customer_requirement in lot['customerRequirements']:
                combined = '(?:{})'.format('|'.join(['не требуется', 'нет', '0.00']))

                try:
                    if re.search(combined, customer_requirement['obesp_z'], flags=re.I) is not None:
                        del item['lots'][lot_num]['customerRequirements'][customer_requirement_num]['obesp_z']

                except:
                    pass

                try:
                    if re.search(combined, customer_requirement['obesp_i'], flags=re.I) is not None:
                        del item['lots'][lot_num]['customerRequirements'][customer_requirement_num]['obesp_i']
                except:
                    pass

                customer_requirement_num += 1

        lot_num += 1

    return item


# Deprecated
def prepare_data_for_send(list):
    return list
    # data = []
    #
    # try:
    #     for item in list:
    #         # Deprecated
    #         if 'description' in item:
    #             phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
    #             item['description'] = re.sub(phone_pattern, '', item['description'])
    #
    #         # Deprecated
    #         item['phone'] = re.sub(r'[^0-9]', '', item['phone'])
    #
    #         # Deprecated
    #         if len(item['phone']) < 9:
    #             item['phone'] = ''
    #
    #         json_data = json.dumps(item, ensure_ascii=False)
    #         data.append(json_data)
    #
    # except Exception as e:
    #     pass
    #
    # return data


def prepare_item(item):
    if 'type' not in item:
        print(item)
        item['type'] = 1

    if 'date' in item:
        del item['date']

    if 'description' in item:
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        item['description'] = re.sub(phone_pattern, '', item['description'])

    if 'phone' in item:
        item['phone'] = prepare_phone(item['phone'])
        # item['phone'] = re.sub(r'[^0-9]', '', item['phone'])

        if len(item['phone']) < 9:
            item['phone'] = ''

    region_name = None
    if 'region' in item:
        region_name = get_region_by_string(item['region'])

    if region_name is None:
        if 'city' in item:
            region_name = get_region_by_string(item['city'])

    if region_name is None:
        if 'address' in item:
            region_name = get_region_by_string(item['address'])

    if region_name is not None:
        item['region_id'] = get_region_id(region_name)

    return json.dumps(item, ensure_ascii=False)


def send_to_api(list):
    api_urls = [
       # 'https://uspehdelo.ru/api/api.php',
       #  'https://bazazakazov.ru/api/api.php'
        'https://dev.bazazakazov.ru/api/api.php'
        # 'https://cpp-group.ru/api/api.php',
    ]

    i = 0

    payload = []
    for item in list:
        if 'fz' in item:
            item = prepare_fz_item(item)

        prepared_item = prepare_item(item)
        payload.append(prepared_item)
        i += 1

        if i >= 10:
            print(payload)
            for api_url in api_urls:
                response = requests.post(api_url, headers={'Content-type': 'application/json; charset=utf-8'},
                                         json=payload, timeout=90)
                print(response.status_code, api_url)

            i = 0
            payload = []

    if len(payload) >= 0:
        print(payload)
        for api_url in api_urls:
            response = requests.post(api_url, headers={'Content-type': 'application/json; charset=utf-8'},
                                     json=payload, timeout=90)
            print(response.status_code, api_url)
