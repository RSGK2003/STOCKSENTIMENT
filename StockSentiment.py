import streamlit as st
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
import yfinance as yf

# Initialize NLTK
nltk.download('vader_lexicon', quiet=True)
sia = SentimentIntensityAnalyzer()

# Constants
SEA_URL = "https://finviz.com/quote.ashx?t="

# Functions
def fetch_stock_data(ticker):
    try:
        url = SEA_URL + ticker
        req = Request(url=url, headers={'user-agent': 'my-app'})
        res = urlopen(req)
        html = BeautifulSoup(res, 'html.parser')
        nw = html.find(id='news-table')
        if nw is None:
            st.error("No news table found for the ticker.")
            return None
        return nw
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None

def process_data(news_table, ticker):
    data = []
    for row in news_table.findAll('tr'):
        if row.a is not None:
            title = row.a.text
            dates_data = row.td.get_text().strip().split(' ')
            
            if len(dates_data) == 1:
                time = dates_data[0]
            else:
                date = dates_data[0]
                time = dates_data[1]
            
            data.append([ticker, date, time, title])
    return pd.DataFrame(data, columns=['ticker', 'date', 'time', 'title'])

def fetch_and_process_price_data(ticker, min_date, max_date):
    try:
        price_data = yf.download(ticker, start=min_date, end=max_date)
        price_data.reset_index(inplace=True)
        # Rename columns
        price_data.rename(columns={'Date': 'date'}, inplace=True)
        
        # Convert date column to datetime and filter rows
        price_data['date'] = pd.to_datetime(price_data['date']).dt.date
        
        
        # Remove any potential duplicate rows
        price_data = price_data.drop_duplicates(subset=['date'])
        
        # Remove rows with any missing values
        price_data = price_data.dropna()
        
        return price_data
    except Exception as e:
        st.error(f"Failed to fetch stock price data: {str(e)}")
        return None

def plot_data(data_frame, price_data):
    try:
        # Calculate mean MarketReaction for each date
        grouped_data = data_frame.groupby(['date', 'ticker']).MarketReaction.mean()
        
        # Calculate price change percentage
        price_data['PriceChange'] = ((price_data['Close'] - price_data['Open']) / price_data['Open']) * 100
        
        # Merge sentiment data with price data
        merged_data = pd.merge(grouped_data.reset_index(), price_data, on='date', how='outer').dropna(axis=0)
        
        # Create the figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12), sharex=True)
        
        # Plot MarketReaction vs. Price Change (%)
        ax1.plot(merged_data['date'], merged_data['MarketReaction'], color='blue', label='Sentiment (Compound Score)')
        ax1.set_ylabel('Sentiment (Compound Score)', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1.set_title('Market Sentiment and Stock Metrics Over Time')
        
        ax1b = ax1.twinx()
        ax1b.plot(merged_data['date'], merged_data['PriceChange'], color='green', label='Price Change (%)')
        ax1b.set_ylabel('Price Change (%)', color='green')
        ax1b.tick_params(axis='y', labelcolor='green')
        
        # Plot MarketReaction vs. Volume
        ax2.plot(merged_data['date'], merged_data['MarketReaction'], color='blue', label='Sentiment (Compound Score)')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Sentiment (Compound Score)', color='blue')
        ax2.tick_params(axis='y', labelcolor='blue')
        
        ax2b = ax2.twinx()
        ax2b.plot(merged_data['date'], merged_data['Volume'], color='red', label='Volume')
        ax2b.set_ylabel('Volume', color='red')
        ax2b.tick_params(axis='y', labelcolor='red')
        
        # Adjust layout and show plot
        fig.tight_layout()
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Failed to plot data: {str(e)}")

# Streamlit application
st.title("Stock Market Sentiment and Price Analysis")

ticker = st.text_input("Enter the stock Ticker (e.g., AAPL):")

if st.button("Analyze"):
    if ticker:
        news_table = fetch_stock_data(ticker)
        if news_table:
            data_frame = process_data(news_table, ticker)
            if not data_frame.empty:
                data_frame['MarketReaction'] = data_frame.title.apply(lambda x: sia.polarity_scores(x)['compound'])
                data_frame['date'] = data_frame['date'].apply(lambda x: pd.Timestamp.today().date() if x == 'Today' else x)
                data_frame.date = pd.to_datetime(data_frame.date,format="%b-%d-%y").dt.date
                data_frame=data_frame.fillna(method='ffill')
                min_date = data_frame.date.min()
                max_date = data_frame.date.max()
                price_data = fetch_and_process_price_data(ticker, min_date, max_date)
                
                if price_data is not None and not price_data.empty:
                    # Display price data if it's not empty
                    st.write("**Stock Price Data:**")
                    st.dataframe(price_data, width=1000, height=200)
                    # Display news and stock prices data if it's not empty
                    st.write("**News and Stock Prices Data:**")
                    st.dataframe(data_frame[['date', 'time', 'title']])
                    
                    # Plot the data
                    plot_data(data_frame, price_data)
                else:
                    st.warning("No valid stock price data available.")
            else:
                st.warning("No news data found to analyze.")
    else:
        st.warning("Please enter a ticker symbol.")
