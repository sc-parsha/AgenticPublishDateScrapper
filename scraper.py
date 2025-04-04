import boto3
import json
import requests
from typing import Dict, List, Tuple
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.graph import Graph, StateGraph
from langchain_core.runnables import RunnablePassthrough
from typing import Optional, List
from newspaper import Article
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import logging
import time
from datetime import datetime
from selenium.webdriver.common.by import By
import html2text
import csv
from dateutil import parser
import tqdm


class WebScraper:
    def __init__(self):
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2'
        )

    def _get_html_newspaper(self, url: str) -> Optional[str]:
        """Attempt to get HTML content using newspaper3k."""
        try:
            article = Article(url)
            article.download()
            return article.html
        except Exception as e:
            return None

    def _get_html_selenium(self, url: str) -> Optional[str]:
        """Get HTML content using Selenium as fallback."""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            text_content = driver.find_element(By.TAG_NAME, "body").text
            driver.quit()
            return text_content
        except Exception as e:
            return None

    def get_page_html(self, url: str) -> Optional[str]:
        """Get HTML content using newspaper3k first, then selenium as fallback."""
        html = self._get_html_newspaper(url)
        if not html:
            html = self._get_html_selenium(url)
        return html

    def convert_html_to_markdown(self, html: str) -> Optional[str]:
        """Convert HTML content to markdown format."""
        try:
            # Using html2text for conversion
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            h.ignore_tables = True
            h.body_width = 0  # Don't wrap text
            markdown = h.handle(html)
            return markdown.strip()
        except Exception as e:
            return None

    def fetch_markdown(self, url: str) -> str:
        """Fetch markdown content using Jina."""
        html = self.get_page_html(url)
        return self.convert_html_to_markdown(html)

    def invoke_bedrock(self, prompt: str) -> str:
        """Invoke Bedrock model with the given prompt."""

        body = json.dumps({
            "prompt": prompt,
            "temperature": 0.2,
            "top_p": 1,
            "max_gen_len": 8192,
            "stop": []
        })

        response = self.bedrock.invoke_model(
            modelId="us.meta.llama3-3-70b-instruct-v1:0",
            body=body
        )
        
        # Debug: read streaming body content
        raw_response = response['body'].read().decode('utf-8')
        
        try:
            response_body = json.loads(raw_response)
            # Debug: print parsed JSON structure
            print("Response structure:", json.dumps(response_body, indent=2))
            return response_body.get('generation', '').strip()
        except json.JSONDecodeError as e:
            print(f"Error parsing response: {e}")
            return raw_response.strip()

    def extract_content(self, markdown: str, url: str) -> Dict:
        """Extract only the publication date from markdown."""
        prompt = f"""You are an assistant that finds publication dates in text.

Look at the text below and find the publication date of the article:

{markdown}

The URL of the article is: {url}   

Return ONLY the publication date in YYYY-MM-DD format. If the date is incomplete, use X for unknown parts (like XXXX-XX-XX).

Respond ONLY with the date in YYYY-MM-DD format. No other text or explanation.

If you cannot find the publication date in the article's metadata, content, or timestamps, try to extract it from the URL pattern. Many news sites include dates in their URL structures (like example.com/2023/05/12/article-title or example.com/news/article-title-20230512). Look for patterns that might represent a date (YYYY/MM/DD, YYYYMMDD, etc.) and extract this information as a potential publication date, but indicate that it was derived from the URL rather than an explicit publication date.

If the page shows a '404 Not Found' error, indicates 'No Content Found', 'Page Content Not Found', or similar error messages, or if the page redirects to a press release page or homepage, do not attempt to extract a publication date. In these cases, return 'XXXX-XX-XX'.

If you cannot find a publication or update date in the available text with reasonable confidence, or if the page has no publish date, return 'XXXX-XX-XX' rather than making a guess.

If multiple dates are found in the content, return the most recent/latest date only.

If a page seems to have a url not related to the content  like homepage , /press-release etc., return 'XXXX-XX-XX'
"""

        result = self.invoke_bedrock(prompt)
        
        # Clean up the result to ensure we just get the date
        # Extract YYYY-MM-DD pattern from the response
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', result)
        if date_match:
            date_result = date_match.group(1)
        else:
            # Check for XXX pattern if no standard date is found
            x_date_match = re.search(r'(X{4}-X{2}-X{2})', result)
            if x_date_match:
                date_result = x_date_match.group(1)
            else:
                date_result = "XXXX-XX-XX"
            
        return {
            "publish_date": date_result
        }

def create_scraping_graph():
    scraper = WebScraper()

    # Define the nodes
    def fetch_node(state):
        url = state["url"]
        markdown = scraper.fetch_markdown(url)
        state["markdown"] = markdown
        state["url"] = url
        return state

    def extract_node(state):
        markdown = state["markdown"]
        url = state["url"]
        content = scraper.extract_content(markdown, url)
        state["result"] = content
        return state

    # Create the graph
    workflow = StateGraph(Graph())

    # Add nodes
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("extract", extract_node)

    # Define edges
    workflow.add_edge("fetch", "extract")
    workflow.set_entry_point("fetch")

    # Compile the graph
    chain = workflow.compile()
    return chain

def scrape_website(url: str) -> Dict:
    """Main function to scrape and analyze a website."""
    chain = create_scraping_graph()
    
    # Initialize state
    initial_state = {
        "url": url
    }
    
    # Execute the graph
    result = chain.invoke(initial_state)
    return result["result"]

# Example usage
if __name__ == "__main__":
    # Read URLs and expected dates from input_links.txt
    input_data = []
    with open("input_links.txt", "r") as f:
        for line in f:
            if line.strip():
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    url = parts[0].strip()
                    expected_date = parts[1].strip()
                    input_data.append((url, expected_date))
    
    # Create or open CSV file for writing results
    with open("scraping_results.csv", "w", newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write header
        csv_writer.writerow(["URL", "Expected Date", "Scraped Date"])
        
        # Process each URL
        for url, expected_date in tqdm.tqdm(input_data, desc="Extracting publication dates", unit="url"):
            print(f"Processing URL: {url}")
            try:
                result = scrape_website(url)
                scraped_date = result.get("publish_date", "XXXX-XX-XX")
                # Write results to CSV
                csv_writer.writerow([url, expected_date, scraped_date])
                
                # Also output to console
                print(f"URL: {url}")
                print(f"Expected Date: {expected_date}")
                print(f"Scraped Date: {scraped_date}")
                print("-" * 50)
                
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                # Write error to CSV
                csv_writer.writerow([url, expected_date, "ERROR"])
            
    print(f"Results have been saved to scraping_results.csv")