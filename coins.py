import json
import time
import requests
import yaml
from os.path import exists
from datetime import datetime, timedelta

from pytion import Notion
from pytion.models import PropertyValue

class Coins:
    def __init__(self):
        """
        Gets required variable data from config yaml file.
        """
        with open("user_variables.yml", 'r') as stream:
            try:
                self.user_variables_map = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("[Error]: while reading yml file", exc)
        self.user_variables_map["NOTION_ENTRIES"] = {}
        self.no = Notion(token=self.user_variables_map["NOTION_SECRET_TOKEN"])
        self.database = self.no.databases.get(self.user_variables_map["DATABASE_ID"])  # retrieve database data (not content) and create object
        self.pages = self.database.db_query()
        self.apiURL = self.user_variables_map["PRICE_API"]
        self.tickerName = self.user_variables_map["TICKER_SYMBOL_NAME"]
        self.currentPriceName = self.user_variables_map["CURRENT_PRICE_NAME"]
        self.user_variables_map["HISTORICAL_PRICE_MAP"] = {}
        self.debug = self.user_variables_map["DEBUG"]
        self.persistData = self.user_variables_map["PERSIST_DATA"]
        self.dataPath = self.user_variables_map["DATA_VOLUME"]
        self.initializepersistentData()
        self.usingPersistentData = False
        
    def writepersistentData(self):
        try:
            json.dump(self.user_variables_map["HISTORICAL_PRICE_MAP"], open(self.getDataPath(),'w'))
            if self.debug:
                print("Writing persistent Data")
        except json.JSONDecodeError as er:
            print("[Error]: while writing persistent data", er)
    
    def getDataPath(self):
        last_char = self.dataPath[-1]
        if last_char == '/':
            if self.debug:
                print("------ ending slash detected----------")
            file_path = self.dataPath + 'coin_prices.json'
        else:
            if self.debug:
                print("------ ending slash NOT detected----------")
            file_path = self.dataPath + '/' + 'coin_prices.json'
        return file_path    
        
    def readpersistentData(self):
        try:
            if self.debug:
                print("Reading persistent Data")
            with open(self.getDataPath()) as data:
                mapData = json.load(data)
            
            print(type(mapData))
            
            self.user_variables_map["HISTORICAL_PRICE_MAP"] = mapData
            
            if self.debug:
                print("data is", str(self.user_variables_map["HISTORICAL_PRICE_MAP"]))   
                
        except json.JSONDecodeError as er:
            print("[Error]: while writing persistent data", er)
            
    def initializepersistentData(self):
        file_exists = exists(self.getDataPath())
        file_path = self.getDataPath()
        print("------ file_path ----------", file_path)
        print("------ self.persistData ----------", file_path)
        print("------ file_exists ----------", str(file_exists))
        if self.persistData == True and file_exists:
            if self.debug:
                print("------ historical coin prices file exists .... attemptint to read it now----------")
            self.readpersistentData()    
            self.usingPersistentData = True 
            if self.debug:
                print("persistent data:", str(self.user_variables_map["HISTORICAL_PRICE_MAP"]))
        
    def getDatabaseValues(self):   
        
        if self.debug:
            print("-------- Getting Database Values ---------")
        
        for p in self.pages.obj:
            symbol = str(p.properties.get(self.tickerName))
            price_string = str(p.properties.get(self.currentPriceName))
            price = float(price_string)                   
            
            self.user_variables_map["NOTION_ENTRIES"].update({symbol: {"page":p.id,"price":price, "update":False}})   
        
    def getCryptoPrices(self):
        """
        Using Binance.US API.
        Ref: https://github.com/binance/binance-api-postman
        """
        print(" --------Getting crypto prices ----------")
        
        for name, data in self.user_variables_map["NOTION_ENTRIES"].items():
            url = f"https://" + self.apiURL + "/api/v3/avgPrice?"\
                f"symbol={name}USDT"  
                
            response = requests.request("GET", url)
            if response.status_code == 200:
                content = response.json()
                
                price = content['price']
                
                if name not in self.user_variables_map["HISTORICAL_PRICE_MAP"]:
                    # Initialize Historical Prices if not present
                    if self.debug:
                        print("Creating map for", name)
                    historicalPrices = self.initializeHistoricalPrices(price)
                    self.updateHistoryForSymbol(name, historicalPrices)
                
                data['price'] = price
                data['update'] = True
                print(name + " price from api is " + price)
                if self.debug: 
                    print(url)
                    print("pageID is " + data['page'])
            elif response.status_code == 400:
                if self.debug:
                 print("Coin not found on " + self.apiURL)
            else:
                print("Wrong response....sleeping.......")
                print(str(response))   
                time.sleep(1 * 60)
                
    def getCheckpointStatus(self, currentPrice, historicalPrices):
        status = "Calculating"
        
        #if not historicalPrices:
        #    historicalPrices = self.initializeHistoricalPrices(currentPrice)
        
        if self.debug:
         print("---- getting checkpoint status ------")
            
        
        historical_price = self.getHistoricalPrice(historicalPrices)
        
        if self.debug:
            print("..... In getCheckpointStatus and got historical price ..... ")
        
        if self.debug:
            print("Historical price is: ", historical_price)
            print("Current price is: ", currentPrice)
        
        #finally get status
        change = self.getPercentChange(historicalPrices, currentPrice)
        
        if self.debug:
            print(str(change) + " %")
        
        if float(currentPrice) == float(historical_price):  
            status = "No Change"       
        elif float(currentPrice) < float(historical_price):
            status = "Falling"
        elif float(currentPrice) > float(historical_price):
            status = "Rising"
        else:
            status = "Calculating"
        
        return (change, status)
        
    def updateHistoryForSymbol(self, symbol, historicalPrices):
        symbolHistory = {symbol:historicalPrices}
        self.user_variables_map["HISTORICAL_PRICE_MAP"].update(symbolHistory)    
        
    def getHistoricalPrice(self, historicalPrices):        
        thisHour = datetime.now().hour
        historical_time = datetime.now() - timedelta(hours=24)
        historical_hour = historical_time.hour
        
        if self.debug:
            print("Historical Hour is: ", str(historical_hour))
            print("historicalPrices are: ", historicalPrices)
            print("historical hour type is: ", type(historical_hour))
            
        try:
            entry = historicalPrices[str(historical_hour)]
            print("entry is: ", str(entry))
            print("entry type is: ", type(entry))
        
            historicalPrice = entry
            if self.debug:
                print("Historical price is: ", historicalPrice)
        except Exception as e:
            print('-------- in exception ---------')
            print(f"[historicalPrices]: {e}")
                    
        return historicalPrice
        
    def getPercentChange(self, historicalPrices, currentPrice):
        if self.debug:
            print("..... In getPercentChange ..... ")
        
        thisHour = datetime.now().hour
        print("This hour is: ", str(thisHour))
        historical_time = datetime.now() - timedelta(hours=24)
        print("Historical time is: ", str(historical_time))
        historical_hour = historical_time.hour
        print("Historical hour is: ", str(historical_hour))
        historicalPrice = self.getHistoricalPrice(historicalPrices)
        print("Historical price is: ", historicalPrice)
        
        # try:
        #     entry = historicalPrices[str(historical_hour)]
        #     print("entry is: ", str(entry))
        #     print("entry type is: ", type(entry))
        #
        #     historicalPrice = entry
        #     if self.debug:
        #         print("Historical price is: ", historicalPrice)
        # except Exception as e:
        #     print(f"[historicalPrices]: {e}")
    
        
        try:
            if float(historicalPrice) == float(currentPrice):
                if self.debug:
                    print("-- No change --")
                percent = 0.00
            else:
                percent = round((float(currentPrice) - float(historicalPrice)) / abs(float(historicalPrice)) * 100, 2)
                if self.debug:
                    print("-- CHANGE --")
        except ZeroDivisionError:
            print("-- ZeroDivisionError --")
            percent = 0.00        
        
        return percent
            
        
    def setHistoricalPrice(self, historicalPrices, currentPrice):
        thisHour = datetime.now().hour
        print("-- Setting Historical Price for hour " + str(thisHour) + " to price " + currentPrice)
        historicalPrices[thisHour] = currentPrice        
            
    def initializeHistoricalPrices(self, currentPrice):
        if self.debug:
            print("------ Initializing Historical Prices ----------")
        historicalPrices = {}
        hours = 24
        while hours > -1:
            historicalPrices[str(hours)] = currentPrice
            hours = hours - 1
        return historicalPrices
                    
    def updateNotionDatabase(self, pageId, coinPrice, update):
        page = self.no.pages.get(pageId)
        print()
        if (update == True):
            
            price = float(coinPrice)
            
            symbol = str(page.obj.properties.get(self.tickerName))   
                                
            history = self.user_variables_map["HISTORICAL_PRICE_MAP"][symbol]
            checkpoint = self.getCheckpointStatus(coinPrice, history)
            status = checkpoint[1]
            change = round(checkpoint[0], 2)
    
            #set a new historical price for this hour
            #get the historical price    
            if self.debug:
                print("        ")
                print("        ")
                print("----- Historial Price BEFORE Update")
                print(str(history))
                print("        ")
                print("        ")
            self.setHistoricalPrice(history, coinPrice)
            if self.debug:
                print("        ")
                print("        ")
            self.updateHistoryForSymbol(symbol, history)   
            if self.debug:
                print("----- Historial AFTER Update")
                print(str(self.user_variables_map["HISTORICAL_PRICE_MAP"][symbol]))             
            
            page.page_update(properties={"Change(24h)":PropertyValue.create("rich_text", str(change) + "%"),"24h Trend":PropertyValue.create("status", status),self.currentPriceName: PropertyValue.create("number", float(coinPrice))})
            print("------ Updating " + symbol + " to " + str(coinPrice) + " with status " + status)
        else:
            page.page_update(properties={"24h Trend":PropertyValue.create("status", "Unlisted")})
            print("------ Not Updating " + str(page.obj.properties.get(self.tickerName)))
        
    def updateCoins(self):
        while True:
            try:
                self.getDatabaseValues()
                self.getCryptoPrices()
                for _, data in self.user_variables_map["NOTION_ENTRIES"].items():
                    
                    price = data['price']
                                        
                    self.updateNotionDatabase(pageId=data['page'],coinPrice=price,update=data['update'])
                    if data['update'] == True:
                        time.sleep(2 * 5)
                time.sleep(1 * 60)
                if self.persistData == True:
                    self.writepersistentData()
            except Exception as e:
                print(f"[Error encountered]: {e}")

if __name__ == "__main__":
    Coins().updateCoins()
