import sys

from bs4 import BeautifulSoup
from requests_html import HTMLSession
from tqdm import tqdm
import pandas as pd
import os
import time
from fake_useragent import UserAgent
from datetime import datetime
import logging
from pythonjsonlogger import jsonlogger

results = {}
id = 0
month_mapper = {'januari': 'january', 'februari':'february', 'mars': 'march', 'april': 'april', 'maj': 'may', 'juni':'june',
                'juli': 'july', 'augusti': 'august', 'september': 'september', 'oktober': 'october', 'november': 'november', 'december': 'december'}

df_housing = pd.read_csv('hemnet_housing.csv')

newly_added_accomodations = 0
gothenburg_municipality_id = 17920

PAGES_TO_SEARCH = 50
HOUSE_CARDS_PER_PAGE = 50
pbar = tqdm(total=PAGES_TO_SEARCH*HOUSE_CARDS_PER_PAGE)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
   def add_fields(self, log_record, record, message_dict):
       super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
       if not log_record.get('timestamp'):
           dtime_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
           log_record['timestamp'] = dtime_now
       if log_record.get('level'):
           log_record['level'] = log_record['level'].upper()
       else:
           log_record['level'] = record.levelname

def setup_logging(logging_file):
    '''
    Set up the root logger
    '''
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # formatter = CustomJsonFormatter('(timestamp) (level) (message)')
    '''
    File handler that writes to a log file
    '''

    if logging_file:
        file_handler = logging.FileHandler(logging_file)
        file_handler.setLevel(logging.INFO)
        # file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    consoleHandler = logging.StreamHandler()
    # consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

session = HTMLSession()
ua = UserAgent()
header = {
    "User-Agent": ua.random
}

for page in range(1,PAGES_TO_SEARCH+1):
    # URL = f"https://www.hemnet.se/salda/bostader?page={page}" # Gives all locations
    URL = f'https://www.hemnet.se/salda/bostader?location_ids%5B%5D={gothenburg_municipality_id}&page={page}'

    r = session.get(URL, headers=header)
    r.html.render(timeout=30)
    content = r.html.html

    content_utf8 = content.encode("utf-8").decode('utf-8')

    soup = BeautifulSoup(content_utf8, 'html.parser')
    sale_cards = soup.find_all('li', class_= 'sold-results__normal-hit')

    for sale_info in sale_cards:
        card_link = sale_info.find("a", class_="sold-property-link").get('href')
        card = sale_info.find("a", class_="sold-property-link").find('div', 'sold-property-listing qa-sale-card')
        listing_info = card.find("div", class_="sold-property-listing__info")
        location_info = listing_info.find("div", class_="sold-property-listing__location")
        address_info = location_info.find("h2", class_="sold-property-listing__heading qa-selling-price-title")
        county_info = location_info.find("div", class_=None)
        housing_type= county_info.find("span", class_= 'property-icon property-icon--result').find("title").text

        if housing_type == 'Övriga':
            continue

        county = county_info.text.split('\n')[-2].strip()
        region = county_info.text.split('\n')[-3].strip().strip(',')
        address = address_info.text.split('\n')[1].strip()

        other_area = None
        house_area_m2 = None

        if address not in df_housing['address'].values:
            newly_added_accomodations+=1
            house_info = listing_info\
                .find("div", class_='sold-property-listing__size')\
                .find("div", class_='sold-property-listing__subheading sold-property-listing__area')

            if housing_type == 'Lägenhet':
                if 'm²' in house_info.text:
                    house_info_idx = house_info.text.split().index("m²") - 1
                    house_area_m2 = float(house_info.text.split()[house_info_idx].replace(',', '.'))
                else:
                    house_area_m2 = None

                if 'rum' in house_info.text:
                    room_idx = house_info.text.split().index("rum") - 1
                    rooms = float(house_info.text.split()[room_idx].replace(',', '.'))
                else:
                    rooms = None

            elif housing_type in ['Villa', 'Fritidsboenden']:
                temp = house_info.text.split()
                if temp != []:
                    if '+' in house_info.text:
                        house_area_m2 = float(house_info.text.split()[0].replace(',', '.'))
                        other_area = float(house_info.text.split()[2].replace(',', '.'))
                    else:

                        house_area_m2 = float(temp[0].replace(',', '.'))
                        other_area = 0
                else:
                    house_area_m2 = None
                    other_area = 0


                if 'rum' in house_info.text:
                    room_idx = house_info.text.split().index("rum") - 1
                    rooms =  float(house_info.text.split()[room_idx].replace(',', '.'))

                else:
                    rooms = None
            elif housing_type == "Gårdar/Skogar":
                temp = house_info.text.split()
                if temp != []:
                    if '+' in house_info.text:
                        house_area_m2 = float(house_info.text.split()[0].replace(',', '.'))
                        other_area = float(house_info.text.split()[2].replace(',', '.'))
                    else:

                        house_area_m2 = float(temp[0].replace(',', '.'))
                        other_area = 0

                if 'rum' in house_info.text:
                    room_idx = house_info.text.split().index("rum") - 1
                    rooms = float(house_info.text.split()[room_idx].replace(',', '.'))
                else:
                    rooms = None
            elif housing_type == 'Radhus':

                temp = house_info.text.split()
                if temp != []:
                    if '+' in house_info.text:
                        house_area_m2 = float(house_info.text.split()[0].replace(',', '.'))
                        other_area = float(house_info.text.split()[2].replace(',', '.'))
                    else:

                        house_area_m2 = float(temp[0].replace(',', '.'))
                        other_area = 0

                if 'rum' in house_info.text:
                    room_idx = house_info.text.split().index("rum") - 1
                    rooms = float(house_info.text.split()[room_idx].replace(',', '.'))
                else:
                    rooms = None
            elif housing_type == 'Tomter':
                rooms = None
                house_area_m2 = None
                other_area = 0

            else:
                rooms = None
                house_area_m2 = None
                other_area = 0

            fee_info = listing_info\
                .find("div", class_='sold-property-listing__size')\
                .find("div", class_='sold-property-listing__fee')


            if housing_type == 'Lägenhet':
                if fee_info is not None:
                    maintenance_fee = float(fee_info.text.replace('\xa0','').replace('kr/mån','').strip())
                else:
                    maintenance_fee = None
                site_area = None
            elif housing_type == 'Villa':
                if fee_info is not None:
                    if 'tomt' in fee_info:
                        site_area = float(fee_info.text.replace('\xa0', '').replace('m²', '').strip().replace('tomt', ''))
                        maintenance_fee = None
                    else:
                        maintenance_fee = float(fee_info.text.replace('\xa0', '').replace('kr/mån', '').strip())
                else:
                    maintenance_fee = None
                    site_area = None
            elif housing_type ==  'Fritidsboenden':
                if ('tomt' in fee_info):
                    site_area = float(fee_info.text.replace('\xa0', '').replace('m²', '').strip().replace('tomt', ''))
                    maintenance_fee = None
                else:
                    maintenance_fee = float(fee_info.text.replace('\xa0', '').replace('kr/mån', '').strip())
                    site_area = None
            elif housing_type == 'Radhus':
                if fee_info is not None:
                    if  ('tomt' in fee_info or 'plot' in fee_info):
                        site_area = float(fee_info.text.replace('\xa0', '').replace('m²', '').strip().replace('tomt', '') )
                        maintenance_fee = None
                    else:
                        maintenance_fee = float(fee_info.text.replace('\xa0','').replace('kr/mån','').strip())
                        site_area = None
                else:
                    maintenance_fee = None
                    site_area = None

            elif housing_type == 'Tomter':
                site_area = float(house_info.text.replace('\xa0', '').replace('m²', '').strip())
                maintenance_fee = None
            elif housing_type == "Gårdar/Skogar":
                site_area = float(fee_info.text.replace('\xa0', '').replace('tomt', '').replace('m²', '').strip())
                maintenance_fee = None
            else:
                maintenance_fee = None
                site_area = None

            price_info = card.find("div", class_="sold-property-listing__price-info")\
                .find("div", class_='sold-property-listing__price')\
                .find("div", class_='sold-property-listing__subheading')

            sold_date_info = card.find("div", class_="sold-property-listing__price-info")\
                .find("div", class_='sold-property-listing__price')\
                .find("div", class_='sold-property-listing__sold-date')

            sold_price = float(price_info.text.replace('\xa0', '').replace('Slutpris', '').strip().replace('kr', ''))
            sold_date_elements = sold_date_info.text.replace('Såld','').strip().split()
            sold_date_month_english =  month_mapper[sold_date_elements[1]]
            sold_date_day = sold_date_elements[0]
            sold_date_year = sold_date_elements[2]

            sold_date = f'{sold_date_day} {sold_date_month_english} {sold_date_year}'

            price_change_info = card.find("div", class_='sold-property-listing__price-change-and-price-per-m2').find("div", class_='sold-property-listing__price-change')

            if price_change_info is not None:
                price_change_perc = float(price_change_info.text.strip().replace('\xa0', '').replace('%','').replace('±', ''))
            else:
                price_change_perc = None

            price_per_m2_info = card.find("div", class_='sold-property-listing__price-change-and-price-per-m2').find("div", class_='sold-property-listing__price-per-m2')

            if price_per_m2_info is not None:
                price_per_m2 = float(price_per_m2_info.text.replace('kr/m²', '').replace('\xa0', '').strip())
            else:
                price_per_m2 = None

            # Go to the card link to fetch more info about the card

            results[id] = {'address': address, 'county': county, 'region': region,
                           'house_area_m2': house_area_m2, 'rooms': rooms, 'maintenance_fee': maintenance_fee,
                           'sold_price': sold_price, 'sold_date': sold_date, 'price_change_perc': price_change_perc,
                       'price_per_m2': price_per_m2, 'housing_type': housing_type, 'other_usable_area': other_area}
            id = id + 1
        else:
            pass
        pbar.set_postfix({'new housing': newly_added_accomodations})
        pbar.update(1)

# print(f'Added {newly_added_accomodations} new properties to the database')
df = pd.DataFrame.from_dict(results)
# df.T.to_csv('hemnet_housing.csv', encoding='utf-8-sig', index=False)
output_path = 'hemnet_housing.csv'
df.T.to_csv(output_path, mode='a', header=not os.path.exists(output_path), encoding='utf-8-sig', index=False)
session.close()


Logfile_path = './log/'
Logfile_name = 'housing_log'
# currenttime = str(datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(Logfile_path, exist_ok=True)
logging_file_name = Logfile_path + Logfile_name  + '.txt'
setup_logging(logging_file_name)
log = logging.getLogger(__name__)
os.chmod(logging_file_name, 0o775)
process_start_time = datetime.now()
log.info("Process Start Time: " + str(process_start_time.strftime("%Y-%m-%d %H:%M:%S")))
log.info(f'Added {newly_added_accomodations} housings at {str(process_start_time.strftime("%Y-%m-%d %H:%M:%S"))} ')

df_housing = pd.read_csv('hemnet_housing.csv')
print(f'total number of housings in database: {len(df_housing)}')