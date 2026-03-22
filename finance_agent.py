# quick sanity check — run this before writing the full agent
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
import random
import yfinance as yf

load_dotenv()

@tool
def get_stock_price(ticker: str) -> str:
    """
    Get the current stock price for a given ticker symbol.
    Use this when the user asks about the current price of any stock.
    Input: ticker symbol like 'AAPL', 'GOOGL', 'TSLA', 'RELIANCE.NS'
    Returns: current price and daily change percentage.
    """
    ticker = ticker.upper()
    try:
        stock = yf.Ticker(ticker)
        # Get the latest price using fast_info
        price = stock.fast_info.get("last_price")
        prev_close = stock.fast_info.get("previous_close")
        
        if price is None or prev_close is None:
            # Fallback to history if fast_info fails
            history = stock.history(period="5d")
            if len(history) >= 2:
                price = history['Close'].iloc[-1]
                prev_close = history['Close'].iloc[-2]
                
        if price is not None and prev_close is not None and prev_close > 0:
            change = round(((price - prev_close) / prev_close) * 100, 2)
            direction = "+" if change > 0 else ""
            return f"{ticker}: ₹/$ {round(price, 2)} ({direction}{change}% today)"
        else:
            return f"{ticker}: Price not available. Try AAPL, GOOGL, TSLA, MSFT"
    except Exception:
        return f"{ticker}: Price not available. Try AAPL, GOOGL, TSLA, MSFT"

# We can add a quick print to confirm tool is configured
if __name__ == "__main__":
    print(f"Tool name: {get_stock_price.name}")
    print(f"Tool description: {get_stock_price.description}")
    print(get_stock_price.invoke({"ticker": "AAPL"}))