import csv
import os

import tqdm
from scraper import WebScraper
from bs4 import BeautifulSoup
from langchain.schema import SystemMessage, HumanMessage
from langchain.tools import Tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain import hub
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

class IsScubscriptionRequired(BaseModel):
    is_subscription_required : bool = Field(description="true if subscription is required for the article to read")

is_subscrption_required_output = PydanticOutputParser(pydantic_object=IsScubscriptionRequired)

load_dotenv()

webscrapper = WebScraper()

# Configure Gemini API key
# genai.configure(api_key= os.environ["GEMINI_API_KEY"])
print(os.environ["GEMINI_API_KEY"])

# Load the Gemini AI model
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-exp-03-25", temperature=0, api_key=os.environ["GEMINI_API_KEY"])  # Adjust model if needed


# Function to fetch webpage content
def fetch_page_content(url: str) -> str:
    return webscrapper.fetch_markdown(url=url)

# Paywall detection function
def check_paywall(url: str) -> str:
    template = """You are analyzing web content to determine if it shows signs of requiring a subscription or having a paywall.
    Content from URL {url}:
    {truncated_markdown}

    VERY IMPORTANT: Check for ANY of these strong paywall indicators:
    1. Words like "Subscribe to unlock", "Subscribe to read", "Subscribe to view", "Subscribe to access", "Subscribe to continue", "Subscribe to read more", "Subscribe to view more", "Subscribe to access more"
    2. Analyze the content if it has some text that is not accessible without a subscription.
    3. Text asking users to pay or register to access content
    4. Content that appears truncated with "..." or "Continue reading"
    5. Messages about limited articles (e.g., "3 free articles remaining")
    6. Any buttons or links with terms like "Subscribe now", "Upgrade", "Join Premium"
    7. Content sections labeled as "Premium" or "Members Only"
    8. Sentences containing "to read this article" or "to access full content"
    9. Any mentions of payment plans, pricing, or premium features

    Be VERY sensitive to these indicators. Even if you can see SOME content, but there are ANY signs of premium/subscription requirements, respond with "true".

    \n{format_instructions}.
    """

    prompt_template = PromptTemplate(template=template, input_variables=["url", "truncated_markdown"],
                                     partial_variables={"format_instructions":is_subscrption_required_output.get_format_instructions()})

    truncated_markdown = fetch_page_content(url=url)

    chain = prompt_template | llm | is_subscrption_required_output

    result = chain.invoke(
        input=dict(url=url, truncated_markdown=truncated_markdown)
    )

    return result

with open("links.txt",'r') as text:
    urls = [link.strip() for link in text.read().split("\n")]

print(urls)

# url = "https://finance.yahoo.com/news/africa-oil-partner-create-subsidiary-115357477.html"

results = []

# Read URLs from a file and process them
for index,url in enumerate(urls):
    print("scraping for ",url, " index ",index)
    result = check_paywall(url)
    print("url",url, "result", result.is_subscription_required)
    break

# with open("output_file.csv", 'w', newline='') as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(['URL', 'result'])
        
#         try:
#             for url,result in results:
#                 writer.writerow([url,result.is_subscription_required])
#         except Exception as e:
#             pass
# # print("url ",url,"subscription required ", result.is_subscription_required)