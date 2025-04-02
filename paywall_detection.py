from scraper import WebScraper
from langgraph.graph import Graph, StateGraph
from typing import TypedDict, Optional, Annotated
from tqdm import tqdm

# Define a schema for our state
class PaywallState(TypedDict):
    url: str
    markdown: Optional[str]
    is_paywalled: Optional[bool]

class PaywallDetector(WebScraper):
    def __init__(self):
        super().__init__()

    def detect_paywall(self, markdown: str, url: str) -> bool:
        """Use the LLM to determine if content is behind a paywall."""
        # Truncate the markdown to a reasonable length
        truncated_markdown = markdown[:7000] + "..." if len(markdown) > 7000 else markdown
        
        prompt = f"""You are analyzing web content to determine if it shows signs of requiring a subscription or having a paywall.
And in the main content, there is a lot of text that is not accessible without a subscription.
Content from URL {url}:
{truncated_markdown}

VERY IMPORTANT: Check for ANY of these strong paywall indicators:
1. Words like "Subscribe to unlock", "Subscribe to read", "Subscribe to view", "Subscribe to access", "Subscribe to continue", "Subscribe to read more", "Subscribe to view more", "Subscribe to access more"
2. Analyze the content if it is has some content that is not accessible without a subscription.
3. Text asking users to pay or register to access content
4. Content that appears truncated with "..." or "Continue reading"
5. Messages about limited articles (e.g., "3 free articles remaining")
6. Any buttons or links with terms like "Subscribe now", "Upgrade", "Join Premium"
7. Content sections labeled as "Premium" or "Members Only"
8. Sentences containing "to read this article" or "to access full content"
9. Any mentions of payment plans, pricing, or premium features

Be VERY sensitive to these indicators. Even if you can see SOME content, but there are ANY signs of premium/subscription requirements, respond with "true".

NOTE : Respond with ONLY "true" if there's ANY indication of paywall/subscription requirements, or "false" ONLY if content appears fully accessible with NO subscription indicators. Provide NO explanation.
"""

        result = self.invoke_bedrock(prompt)
        # Clean up result and convert to boolean
        result = result.strip().lower()
        return "true" in result

def create_paywall_detection_graph():
    detector = PaywallDetector()

    # Define the nodes
    def fetch_node(state: PaywallState) -> PaywallState:
        url = state["url"]

        markdown = detector.fetch_markdown(url)
        if not markdown:
            # If we couldn't get any content, likely paywalled
            state["is_paywalled"] = True
            state["markdown"] = ""
            return state
        
        state["markdown"] = markdown
        return state

    def detect_node(state: PaywallState) -> PaywallState:
        # Skip detection if we already determined it's paywalled in fetch_node
        if state.get("is_paywalled", False):
            return state
            
        markdown = state["markdown"]
        url = state["url"]
        is_paywalled = detector.detect_paywall(markdown, url)
        state["is_paywalled"] = is_paywalled
        return state

    # Create the graph with the schema
    workflow = StateGraph(PaywallState)

    # Add nodes
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("detect", detect_node)

    # Define edges
    workflow.add_edge("fetch", "detect")
    workflow.set_entry_point("fetch")

    # Compile the graph
    chain = workflow.compile()
    return chain

def check_for_paywall(url: str) -> bool:
    """Main function to check if a website has a paywall."""
    print("Checking for paywall on ", url)
    chain = create_paywall_detection_graph()
    
    # Initialize state
    initial_state = {
        "url": url
    }
    
    # Execute the graph
    result = chain.invoke(initial_state)
    return result["is_paywalled"]

# Example usage
if __name__ == "__main__":
    import csv
    import os
    
    # Path to the paywall_links.txt file - assuming it's in the same directory
    input_file = "paywall_links.txt"
    output_file = "paywall_results.csv"
    
    # Read the URLs and their actual paywall status from the file
    urls_and_statuses = []
    try:
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    parts = line.split('\t')
                    if len(parts) == 2:
                        url = parts[0]
                        actual_is_paywall = parts[1].upper() == 'TRUE'
                        urls_and_statuses.append((url, actual_is_paywall))
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        exit(1)
    
    print(f"Found {len(urls_and_statuses)} URLs to process")
    
    # Create a CSV file to store results
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['URL', 'Actual_Is_Paywall', 'Is_Paywall_Detected'])
        
        # Process each URL with tqdm progress bar
        for url, actual_is_paywall in tqdm(urls_and_statuses, desc="Processing URLs", unit="url"):
            try:
                is_paywall_detected = check_for_paywall(url)
                writer.writerow([url, actual_is_paywall, is_paywall_detected])
                tqdm.write(f"URL: {url}")
                tqdm.write(f"Actual paywall status: {actual_is_paywall}")
                tqdm.write(f"Detected paywall status: {is_paywall_detected}")
                tqdm.write("-" * 50)
            except Exception as e:
                tqdm.write(f"Error processing {url}: {e}")
                writer.writerow([url, actual_is_paywall, "ERROR"])
    
    print(f"Results saved to {output_file}")
