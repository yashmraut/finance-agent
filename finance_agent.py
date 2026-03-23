# quick sanity check — run this before writing the full agent
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
import random
import yfinance as yf
import requests

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

@tool
def calculate_compound_interest(
    principal: float,
    annual_rate: float,
    years: int
) -> str:
    """
    Calculate compound interest on an investment.
    Use this when the user wants to know how much money will grow over time.
    Input:
        principal: initial investment amount in rupees or dollars
        annual_rate: annual interest rate as a percentage (e.g. 12 for 12%)
        years: number of years to invest
    """
    rate = annual_rate / 100
    final_amount = principal * (1 + rate) ** years
    profit = final_amount - principal
    return (
        f"Principal: ₹{principal:,.0f}\n"
        f"After {years} years at {annual_rate}%: ₹{final_amount:,.0f}\n"
        f"Total profit: ₹{profit:,.0f}\n"
        f"Money multiplied: {final_amount/principal:.1f}x"
    )


@tool
def get_mutual_fund_info(fund_name: str) -> str:
    """
    Get information about a mutual fund including its category,
    fund house, and latest NAV.
    Use this when the user asks about mutual funds or wants fund details.
    Input: fund name like 'HDFC Small Cap', 'SBI Bluechip', 'Parag Parikh Flexi Cap'
    Returns: fund details and latest NAV.
    """
    try:
        # Search for the scheme by keyword
        search_url = f"https://api.mfapi.in/mf/search?q={fund_name}"
        search_response = requests.get(search_url)
        search_response.raise_for_status()
        search_results = search_response.json()
        
        if not search_results:
            return f"No specific data found for '{fund_name}'. Please try with a more specific mutual fund name."
        
        # Take the most relevant (first) result
        scheme_code = search_results[0]['schemeCode']
        
        # Get details for the specific scheme code
        details_url = f"https://api.mfapi.in/mf/{scheme_code}"
        details_response = requests.get(details_url)
        details_response.raise_for_status()
        details_data = details_response.json()
        
        meta = details_data.get("meta", {})
        data = details_data.get("data", [])
        
        scheme_name = meta.get("scheme_name", "Unknown Scheme")
        fund_house = meta.get("fund_house", "Unknown Fund House")
        scheme_category = meta.get("scheme_category", "Unknown Category")
        
        if data:
            latest_nav = data[0].get("nav", "N/A")
            latest_date = data[0].get("date", "N/A")
            return (
                f"Fund Name: {scheme_name}\n"
                f"Fund House: {fund_house}\n"
                f"Category: {scheme_category}\n"
                f"Latest NAV: ₹{latest_nav} (as of {latest_date})"
            )
        else:
            return (
                f"Fund Name: {scheme_name}\n"
                f"Fund House: {fund_house}\n"
                f"Category: {scheme_category}\n"
                f"Latest NAV: Not available"
            )
    except Exception as e:
        return f"Error fetching mutual fund details for '{fund_name}': {str(e)}"

tools = [get_stock_price, calculate_compound_interest, get_mutual_fund_info]

llm = ChatGroq(model="qwen/qwen3-32b", temperature=0.0)

system_prompt = """You are a knowledgeable personal finance advisor for Indian investors.

Your behavior:
- Always use tools to get real data before giving advice
- Be specific with numbers — never give vague answers
- If the user asks about stocks, check the price first using the tool
- If the user asks about investing, calculate actual returns using the tool
- Always explain your reasoning after using a tool
- Be concise but complete — no unnecessary padding
- If you don't have data for something, say so honestly
- CRITICAL: Never call more than one tool at the exact same time. Think step-by-step and use one tool sequentially."""

agent = create_react_agent(model=llm, tools=tools, prompt=system_prompt)

def ask_finance_agent(question: str) -> str:
    print(f"\n{'='*55}")
    print(f"Question: {question}")
    print('='*55)

    result = agent.invoke({
        "messages": [("human", question)]
    })

    # result["messages"] is a list of all messages in the conversation:
    # HumanMessage → AIMessage(tool_call) → ToolMessage → AIMessage(final)
    # We want the last AIMessage which is the final answer.
    final = result["messages"][-1]
    return final.content



# We can add a quick print to confirm tool is configured
# if __name__ == "__main__":
#     #print(f"Tool name: {get_stock_price.name}")
#     #print(f"Tool description: {get_stock_price.description}")
#     #print(calculate_compound_interest.invoke({"principal": 10000, "annual_rate": 12, "years": 10}))
#     print(get_mutual_fund_info.invoke({"fund_name": "Motilal oswal midcap fund"}))

if __name__ == "__main__":

    # Test 1 — single tool call
    answer = ask_finance_agent("What is the current price of Apple stock?")
    print("\nAnswer:", answer)

    # Test 2 — tool call + reasoning
    answer = ask_finance_agent(
        "If I invest ₹50,000 in an index fund today, "
        "how much will I have in 15 years?"
    )
    print("\nAnswer:", answer)

    # Test 3 — multi tool call (agent decides to call 2 tools)
    answer = ask_finance_agent(
        "I have ₹1,00,000 to invest. Should I put it in TSLA stock "
        "or an ELSS mutual fund? Show me the numbers."
    )
    print("\nAnswer:", answer)
