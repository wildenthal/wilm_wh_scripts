import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

'''
Scrapes logs to find how stock for fresh items evolved over the week.
Generates graphs to visualize.
'''

def main():
    if input('Scrape pages? y/n: ')=='y':
        scrape()
    
    #group log changes by SKU and order by time
    logs = pd.read_csv('logs.csv',delimiter=';')
    grouped = logs.groupby(logs['SKU'])
    
    stocklist = []
    for SKU in logs['SKU'].unique():
        df = grouped.get_group(SKU)
        df = df.sort_values('time')
        stocklist.append(df)
    
    #plots stock changes over time
    mpl.rc('figure', figsize=(20, 5))
    for index,stockitem in enumerate(stocklist):
        #formatting and prepping
        stockitem['time'] = pd.to_datetime(stockitem['time'])
        stockitem['time'] = (stockitem['time'].dt.day).astype(str) +'th '+ (stockitem['time'].dt.time).astype(str)#.dt.floor('T').dt.time).astype(str)
        stockitem['time'] = stockitem['time']#.apply(lambda x: x[:-3])
        name = stockitem['name'].values[0]
        SKU = stockitem['SKU'].values[0]
        changes = stockitem['change'].values
        initials = stockitem['initial'].values
        finals = stockitem['final'].values
        times = stockitem['time'].values
        shelf = stockitem['shelf'].values[0]
        letter = stockitem['letter'].values[0]
        x = np.arange(len(stockitem['initial']))
        x2 = [dot + 0.2 for dot in x]
        fig, ax = plt.subplots()
        ax.set_xticks(x)
        ax.set_xticklabels(times)
        
        for subindex,dot in enumerate(x):
            if finals[subindex]>initials[subindex]:
                #plot stock increases in green
                plt.plot([dot,dot+0.2],[initials[subindex],finals[subindex]],color='green')
            else:
                #plot stock decreases in red
                plt.plot([dot,dot+0.2],[initials[subindex],finals[subindex]],color='red')
            #write final amount at end of line
            ypoint = finals[subindex]*1.01
            plt.text(dot+0.21,ypoint,changes[subindex],fontsize=16)
            #join manual stock changes with dotted line (i.e. representing sales)
            if subindex > 0:
                plt.plot([dot-0.8,dot],[finals[subindex-1],initials[subindex]],linestyle='--',color='lightblue')
                sale=initials[subindex]-finals[subindex-1]
                plt.text(dot+0.01,initials[subindex],sale)
                try:
                    day = int(times[subindex][0:2])
                    yester = int(times[subindex-1][0:2])
                except:
                    day = int(times[subindex][0:1])
                    yester = int(times[subindex-1][0:1])
                if day > yester:
                    #separate days with black line
                    plt.axvline(dot-0.5,color='black')
        ax.set_ylim([ax.get_ylim()[0],ax.get_ylim()[1]*1.1])
        ax.set_title(f'{name} ({SKU})')
        plt.grid(axis='y')
        plt.savefig(f'figs/{shelf}_{letter} -{name}.jpg')
        plt.close()
        
def scrape():
    from bs4 import BeautifulSoup
    from pymongo import MongoClient
    import csv
    from decouple import config
    userID = config('userID',default='')
    password = config('password',default='')
    cluster = f"mongodb+srv://{userID}:{password}@warehouse.konbq.mongodb.net/Warehouses?retryWrites=true&w=majority"
    client = MongoClient(cluster)
    db = client.Warehouses
    stock = db.fullstock

    with open('logs.htm') as html_file:
        soup = BeautifulSoup(html_file,'lxml')
        
    csv_file = open('logs.csv', 'w',newline='')
    csv_writer = csv.writer(csv_file,delimiter=';')

    csv_writer.writerow(['SKU','name','initial','change','final','time','shelf','letter'])

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
        time = datetime.strptime(item[4].text,' %m/%d/%Y, %I:%M:%S %p ')
        if initial > final:
            change = -1*change
        try:
            stockitem = stock.find_one({'SKU':SKU})
            name = stockitem['name']
            harvest = stockitem['harvest']
            if harvest and change != 0:
                csv_writer.writerow([SKU,name,initial,change,final,time,stockitem['shelf'],stockitem['letter']])
            else:
                pass
        except:
            pass
            
    csv_file.close()
    
if __name__ == '__main__':
    main()
