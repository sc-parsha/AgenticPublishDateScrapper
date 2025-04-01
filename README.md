# Publication Date Scraper

A robust web scraping tool designed to extract publication dates from web articles. This tool uses a combination of techniques including newspaper3k, Selenium, and AWS Bedrock LLM to accurately identify and extract publication dates from various web pages.

## Features

- **Multi-method HTML extraction**: Uses newspaper3k with Selenium fallback
- **HTML to Markdown conversion**: Simplifies content for analysis
- **AWS Bedrock LLM integration**: Uses Llama 3 70B for intelligent date extraction
- **Flexible date format handling**: Returns dates in standardized YYYY-MM-DD format
- **URL pattern recognition**: Can extract dates from URL patterns when not present in content
- **Batch processing**: Process multiple URLs from an input file
- **Error handling**: Gracefully handles failures and missing dates
- **Progress tracking**: Uses tqdm for progress visualization

## Prerequisites

- Python 3.8+
- AWS account with Bedrock access (us-west-2 region)
- Chrome browser (for Selenium)
- Proper AWS credentials configured

## Dependencies

```
boto3
requests
langchain-core
langgraph
newspaper3k
selenium
beautifulsoup4
html2text
python-dateutil
tqdm
```

## Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install boto3 requests langchain-core langgraph newspaper3k selenium beautifulsoup4 html2text python-dateutil tqdm
   ```
3. Ensure you have Chrome installed and chromedriver configured for Selenium
4. Configure AWS credentials with Bedrock access

## Usage

### Input File Format

Create a file named `input_links.txt` with the following format:
```
https://example.com/article1    2023-05-15
https://example.com/article2    2022-11-23
```

Each line should contain a URL and an expected date (for verification) separated by a tab.

### Running the Scraper

```bash
python scraper.py
```

### Output

The script will:
1. Process each URL in the input file
2. Extract the publication date
3. Write results to `scraping_results.csv`
4. Display progress in the console

## How It Works

1. **HTML Extraction**: 
   - Primary method: newspaper3k library
   - Fallback: Selenium headless browser

2. **Content Processing**:
   - Converts HTML to clean markdown format

3. **Date Extraction**:
   - Uses AWS Bedrock's Llama 3 70B model to intelligently identify publication dates
   - Processes various date formats and patterns
   - Handles edge cases like dates in URL patterns
   - Returns XXXX-XX-XX for pages without dates

4. **Processing Flow**:
   - Implemented using LangGraph for flexible workflow orchestration

