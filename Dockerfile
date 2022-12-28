FROM python:3

ADD coins.py /
ADD user_variables.yml /
ADD requirements.txt /
ADD start.sh /

ENV TZ=America/Chicago

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV NOTION_SECRET_TOKEN unset
ENV DATABASE_ID unset
ENV CURRENT_PRICE_NAME Current Price
ENV PRICE_API api.binance.us
ENV TICKER_SYMBOL_NAME Symbol
ENV DEBUG false
ENV PERSIST_DATA false
ENV DATA_VOLUME /database
ENV CREATE_VOLUME: false

RUN pip3 install -r requirements.txt

ENTRYPOINT ["/start.sh"]