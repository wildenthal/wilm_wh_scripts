from bs4 import BeautifulSoup
import csv
import pandas as pd
from datetime import datetime

'''
Searches stocklist YYYY-MM-DD.htm file for annulled items and checks whether they were present the day before. 
Segregates into items that were annulled manually through logs.htm file.
'''

def main():
    morningstr = pd.to_datetime('today').strftime('%Y-%m-%d')
    nightstr = (pd.to_datetime('today')-pd.Timedelta('1 days')).strftime('%Y-%m-%d')

    print(f'Will compare {morningstr} to {nightstr}')
    
    if input('Scrape pages? y/n: ')=='y':
        scrape(morningstr,nightstr)
    
    #load csvs
    morning = pd.read_csv(f'{morningstr}.csv',delimiter=';')
    night = pd.read_csv(f'{nightstr}.csv',delimiter=';')
    logs = pd.read_csv('logs.csv',delimiter=';')

    #find sku for which morning values are zero
    nullstock = pd.DataFrame()
    nullstock['SKU'] = [morning.loc[index,'SKU'] for index in morning.query('amount==0').index] 

    #find night stock for these sku
    nightnull = night[night['SKU'].isin(nullstock['SKU'].values)]

    #check morning logs for these sku
    try:
        lognulls = logs[logs['SKU'].isin(nullstock['SKU'].values)]
        grouped = logs.groupby(lognulls['time'])
        group = grouped.get_group(pd.Timestamp.today().date().strftime('%Y-%m-%d'))
        ournulls = group[group['final']==0]
        print()
        prewarnvalues = nightnull[nightnull['amount']!= 0]
        print('We set these to zero: ')
        nonwarnvalues = prewarnvalues[prewarnvalues['SKU'].isin(ournulls['SKU'].values)]
        print(nonwarnvalues)
    except:
        print('No zeros on our part')
        ournulls = pd.DataFrame()
        ournulls['SKU']=[0]
    finally:
        prewarnvalues = nightnull[nightnull['amount']!= 0]
        nonwarnvalues = prewarnvalues[prewarnvalues['SKU'].isin(ournulls['SKU'].values)]
        print()
        print('We did not set these to zero: ')
        warnvalues = prewarnvalues[~prewarnvalues['SKU'].isin(ournulls['SKU'].values)]
        print(warnvalues)
        print()
       
def scrape(morningstr,nightstr):
    with open('logs.htm') as html_file:
        soup = BeautifulSoup(html_file,'lxml')
        
    csv_file = open('logs.csv', 'w',newline='')
    csv_writer = csv.writer(csv_file,delimiter=';')

    csv_writer.writerow(['SKU','initial','change','final','time'])

    sku_iter = soup.find_all('div',class_='log__sku')
    initial_iter = soup.find_all('div',class_='log__quantity-box log__quantity-box--yellow log__quantity-box--long')
    change_iter = soup.find_all(lambda tag: tag.name == 'div' and tag.get('class') == ['log__quantity-box'])
    final_iter = soup.find_all('div',class_='log__quantity-box log__quantity-box--green log__quantity-box--long')
    time_iter = soup.find_all('div',class_='log__timestamp') 
    zipped = zip(sku_iter,initial_iter,change_iter,final_iter,time_iter)

    for item in zipped:
        SKU = int(item[0].text)
        initial = int(item[1].text)
        change = int(item[2].text)
        final = int(item[3].text)
        time = datetime.strptime(item[4].text,' %m/%d/%Y, %I:%M:%S %p ').date()
        if initial > final:
            change = -1*change
        if change != 0:
            csv_writer.writerow([SKU,initial,change,final,time])
            
    csv_file.close()

    for filename in [morningstr,nightstr]:
        with open(f'{filename}.htm') as html_file:
            soup = BeautifulSoup(html_file, 'lxml')
        csv_file = open(f'{filename}.csv', 'w',newline='')
        csv_writer = csv.writer(csv_file,delimiter=';')
        csv_writer.writerow(['SKU','name','amount','shelf','letter'])

        for shelfgrp in soup.find_all("table", class_="stock-list__table"):
            for lettergrp in shelfgrp.find_all("td", class_="stock-list__shelf-sub-group"):
                letterstr = lettergrp.text
                #print(letterstr)
                try:
                    shelf = int(letterstr[0:4])
                    letter = letterstr[4]
                    for item in lettergrp.parent.find_all("table", class_="stock-line stock-list__stock-item"):
                        properties = item.find_all("td")
                        SKU = properties[0].text
                        name = properties[2].text
                        amount = properties[3].text
                        csv_writer.writerow([SKU,name,amount,shelf,letter])
                except:
                    pass
        csv_file.close()

if __name__ == '__main__':
    main()
