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
        self.apiURL = self.user_variables_map["PRICE_API"]
        self.tickerName = self.user_variables_map["TICKER_SYMBOL_NAME"]
        self.currentPriceName = self.user_variables_map["CURRENT_PRICE_NAME"]
        self.user_variables_map["HISTORICAL_PRICE_MAP"] = {}
        self.debug = self.user_variables_map["DEBUG"]
        self.persistData = self.user_variables_map["PERSIST_DATA"]
        self.dataPath = self.user_variables_map["DATA_VOLUME"]
        self.initializepersistentData()
        self.usingPersistentData = False
        
        
    def queryNotionDatabase(self):
        if self.debug:
            print("------ Querying Notion Database----------")
        self.pages = self.database.db_query()
        
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
            file_path = self.dataPath + 'coin_prices.json'
        else:
            file_path = self.dataPath + '/' + 'coin_prices.json'
        return file_path    
        
    def readpersistentData(self):
        try:
            if self.debug:
                print("Reading persistent Data")
            with open(self.getDataPath()) as data:
                mapData = json.load(data)
                        
            self.user_variables_map["HISTORICAL_PRICE_MAP"] = mapData
            
            if self.debug:
                print("data is", str(self.user_variables_map["HISTORICAL_PRICE_MAP"]))   
                
        except json.JSONDecodeError as er:
            print("[Error]: while writing persistent data", er)
            
    def initializepersistentData(self):
        file_path = self.getDataPath()
        file_exists = exists(file_path)
        if self.persistData == True and file_exists:
            if self.debug:
                print("------ Persistent coin prices file exists .... attemptint to read it now----------")
            self.readpersistentData()    
            self.usingPersistentData = True 
            if self.debug:
                print("persistent data:", str(self.user_variables_map["HISTORICAL_PRICE_MAP"]))
        else:
            if self.debug:
                print("------ Persistent coin prices file not found at path " + file_path)        
            
        
    def getDatabaseValues(self):   
        self.queryNotionDatabase()    
        
        if self.debug:
            print("-------- Parsing Database Values ---------")
        for p in self.pages.obj:
            try:
                symbol = str(p.properties.get(self.tickerName))
                price_string = str(p.properties.get(self.currentPriceName))
                price = float(price_string)
                if self.debug:
                    print("Found " + symbol + " in database with price " + price_string)
            except ValueError:
                if self.debug:
                    print('Could not get property value from page. This could be a blank row or price is empty.')
                continue   
            self.user_variables_map["NOTION_ENTRIES"].update({symbol: {"page":p.id,"price":price, "update":False}})    
            if self.debug:
                print("Updated NOTION_ENTRIES MAP to ", self.user_variables_map["NOTION_ENTRIES"])                   
        
    def getCryptoPrices(self):
        if self.debug:
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
                if self.debug:
                    print(name + " price from api is " + price)
                    print(url)
                    print("pageID is " + data['page'])
            elif response.status_code == 400:
                if self.debug:
                 print("Coin not found on " + self.apiURL)
            else:
                print("Wrong response....sleeping.......")
                print(str(response))   
                time.sleep(1 * 60)
                
    def getStatusChange(self, historicalPrice, currentPrice):
        if self.debug:
            print("---- in getStatusChange ------")
        if float(currentPrice) == float(historicalPrice):  
            status = "No Change"       
        elif float(currentPrice) < float(historicalPrice):
            status = "Falling"
        elif float(currentPrice) > float(historicalPrice):
            status = "Rising"
        else:
            status = "Calculating"
        return status                
                
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
        
        change = self.getPercentChange(historicalPrices, currentPrice)
        
        if self.debug:
            print("12 hour percent change: " + str(change[0]) + " %")
            print("24 hour percent change: " + str(change[1]) + " %")
        
        status_12 = self.getStatusChange(historical_price[0], currentPrice)  
        status_24 = self.getStatusChange(historical_price[1], currentPrice)   
        
        if self.debug:
            print("---- returning status_12, status_24 ------")
        status = (status_12, status_24)
        
        return (change, status)
        
    def updateHistoryForSymbol(self, symbol, historicalPrices):
        symbolHistory = {symbol:historicalPrices}
        self.user_variables_map["HISTORICAL_PRICE_MAP"].update(symbolHistory)    
        
    def getHistoricalHour(self, number):
        historical_time = datetime.now() - timedelta(hours=number)
        if self.debug:
            print("---- This hour is: ", datetime.now().hour)    
            print("---- Historical hour was: ", historical_time.hour)
        return str(historical_time.hour)
        
    def getHistoricalPrice(self, historicalPrices):        
        historicalHour24 = self.getHistoricalHour(23)
        historicalHour12 = self.getHistoricalHour(12)
        
        if self.debug:
            print("Historical 12 Hour is: ", historicalHour12)
            print("Historical 24 Hour is: ", historicalHour24)
            
        try:
            historicalPrice_24 = historicalPrices[historicalHour24]
            historicalPrice_12 = historicalPrices[historicalHour12]
            if self.debug:
                print("Price 12 hours ago was:  ", str(historicalPrice_12))
                print("Price 24 hours ago was: ", str(historicalPrice_24))
            
        except Exception as e:
            print('-------- in exception ---------')
            print(f"Error getting hostorical prices: {e}")
                    
        return (historicalPrice_12,historicalPrice_24)
        
    def calculatePercent(self, historicalPrice, currentPrice):
        try:
            if float(historicalPrice) == float(currentPrice):
                percent = 0.00
            else:
                percent = round((float(currentPrice) - float(historicalPrice)) / abs(float(historicalPrice)) * 100, 2)
        except ZeroDivisionError:
            print("-- ZeroDivisionError --")
            percent = 0.00        
        
        return percent
            
    def getPercentChange(self, historicalPrices, currentPrice):
        if self.debug:
            print("..... In getPercentChange ..... ")
        
        historicalHour12 = self.getHistoricalHour(12)
        historicalHour24 = self.getHistoricalHour(23)
        
        historicalPrice_12 = historicalPrices[historicalHour12]
        historicalPrice_24 = historicalPrices[historicalHour24]
        
        historicalChange_12 = self.calculatePercent(historicalPrice_12, currentPrice)
        historicalChange_24 = self.calculatePercent(historicalPrice_24, currentPrice)
        
        return(historicalChange_12, historicalChange_24)
        
    def setHistoricalPrice(self, historicalPrices, currentPrice):
        thisHour = datetime.now().hour
        if self.debug:
            print("-- Setting Historical Price for hour " + str(thisHour) + " to price " + currentPrice)
        historicalPrices[thisHour] = currentPrice        
            
    def initializeHistoricalPrices(self, currentPrice):
        if self.debug:
            print("------ Creating Initial Historical Prices ----------")
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
            checkpoint = self.getCheckpointStatus(coinPrice, history) #Returns tuple of a tuple((0.0, 0.0), ('No Change', 'No Change'))
            if self.debug:
                print("checkpoint", str(checkpoint))
                
            checkpointChange = checkpoint[0]
            checkpointStatus = checkpoint[1]   
            if self.debug:
                print("checkpointChange", str(checkpointChange))
                print("checkpointStatus", str(checkpointStatus))
            
            change_12 = round(checkpointChange[0], 2)
            change_24 = round(checkpointChange[1], 2)
            if self.debug:
                print("change_12", str(change_12))
                print("change_24", str(change_24))
            
            status_12 = checkpointStatus[0]
            status_24 = checkpointStatus[1]
            if self.debug:
                print("status_12", str(status_12))
                print("status_24", str(status_24))
    
            #set a new historical price for this hour
            #get the historical price    
            if self.debug:
                print("        ")
                print("----- Historial Price BEFORE Update")
                print(str(history))
                print("        ")
            self.setHistoricalPrice(history, coinPrice)
            if self.debug:
                print("        ")
            self.updateHistoryForSymbol(symbol, history)   
            if self.debug:
                print("----- Historial AFTER Update")
                print(str(self.user_variables_map["HISTORICAL_PRICE_MAP"][symbol]))       
                      
            
            page.page_update(properties={"Change(12h)":PropertyValue.create("rich_text", str(change_12) + "%"),"12h Trend":PropertyValue.create("status", status_12),
            "Change(24h)":PropertyValue.create("rich_text", str(change_24) + "%"),"24h Trend":PropertyValue.create("status", status_24),
            self.currentPriceName: PropertyValue.create("number", float(coinPrice))})
            
            print("------ Updating " + symbol + " to " + str(coinPrice) + " with 12 hour status: " + status_12 + " and 24 hour status: " + status_24)
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
