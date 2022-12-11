# -*- coding: utf-8 -*-
import locale
import os
import sys
import time
from datetime import datetime

currentdir = os.path.dirname(os.path.realpath(__file__))
base_path = os.path.dirname(currentdir)
sys.path.append(base_path)
sys.path.append('/home/manage_report')
from Send_report.Utils import send_to_api
# from google_sheets_handler import insert
# from Mail import send_mail
# from TGHangler import send_message

from SynapsenetRu import SynapsenetRu


if __name__ == '__main__':
    print('Start:', print(datetime.now()))
    parsers = [
        SynapsenetRu(),
    ]

    msg = ''

    for parser in parsers:
        attempts = 0
        while True:
            if attempts > 2:
                msg += parser.name + ": ошибка" + "\n"

                break

            try:
                print('Запуск парсера {}'.format(parser.name))
                parser.run()
                msg += '{}: {}\n'.format(parser.name, parser.ads_count)
                print('{}: {}\n'.format(parser.name, parser.ads_count))

                try:
                    if len(parser.errors) > 0:
                        msg += '\n{}'.format('; '.join(parser.errors))
                except:
                    pass

                break

            except Exception as e:
                print(e)
                # msg += parser.name + ": ошибка" + "\n"
                attempts += 1
                time.sleep(10)

    print(msg)
    # send_mail(msg)
    # send_message(msg)
    # insert(msg,tenders=True)
    print('End:', print(datetime.now()))
    sys.exit()
