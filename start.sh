#!/bin/bash

# Check user defined variables
# 
if [ "${NOTION_SECRET_TOKEN}" == "unset" ] ; then echo "Please set NOTION_SECRET_TOKEN. example:  -e NOTION_SECRET_TOKEN=<YOUR_NOTION_SECRET_TOKEN> (max 15 characters)"; exit 1 ; fi
if [ "${DATABASE_ID}" == "unset" ] ; then echo "Please set DATABASE_ID. example:  -e DATABASE_ID=<DATABASE_ID> (max 15 characters)"; exit 1 ; fi
  
#add token  
sed -i -e "s/NOTION_SECRET_TOKEN:.*/NOTION_SECRET_TOKEN: ${NOTION_SECRET_TOKEN}/g" user_variables.yml
sed -i -e "s/DATABASE_ID:.*/DATABASE_ID: ${DATABASE_ID}/g" user_variables.yml
sed -i -e "s/CURRENT_PRICE_NAME:.*/CURRENT_PRICE_NAME: ${CURRENT_PRICE_NAME}/g" user_variables.yml
sed -i -e "s/PRICE_API:.*/PRICE_API: ${PRICE_API}/g" user_variables.yml
sed -i -e "s/TICKER_SYMBOL_NAME:.*/TICKER_SYMBOL_NAME: ${TICKER_SYMBOL_NAME}/g" user_variables.yml
sed -i -e "s/DEBUG:.*/DEBUG: ${DEBUG}/g" user_variables.yml
sed -i -e "s/PERSIST_DATA:.*/PERSIST_DATA: ${PERSIST_DATA}/g" user_variables.yml
sed -i -e "s/DATA_VOLUME:.*/DATA_VOLUME: ${DATA_VOLUME}/g" user_variables.yml
sed -i -e "s/CREATE_VOLUME:.*/CREATE_VOLUME: ${CREATE_VOLUME}/g" user_variables.yml


if [ "${CREATE_VOLUME}" = true ] || [ "${CREATE_VOLUME}" == "true" ] || [ "${CREATE_VOLUME}" == "True" ] ; then 
  echo "creating data volume"
  mkdir -p "${DATA_VOLUME}"
fi

#start script
python3 coins.py

exec "$@"