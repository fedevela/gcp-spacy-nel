import re
from flask import Flask, request, jsonify
import spacy
import requests
import time
from bs4 import BeautifulSoup
from io import BytesIO
from PyPDF2 import PdfReader

# Initialize the Flask app

app = Flask(__name__)

# Load the spaCy model with NEL
nlp = spacy.load("en_core_web_lg")
    
# Regular expression for validating DOI
doi_pattern = re.compile(r'^10.\d{4,9}/[-._;()/:A-Z0-9]+$', re.IGNORECASE)

def extract_entities_from_paragraph(paragraph):
    # Process the paragraph using spaCy
    doc = nlp(paragraph)

    # Extract named entities and their labels
    entities = [
        {"text": ent.text, "label": ent.label_}
        for ent in doc.ents
    ]

    # Return the entities as JSON
    return jsonify({"entities": entities})

def extract_doi_metadata(item):
    """Extracts metadata from a CrossRef API item."""
    print("********************Debug: item contents:*****************************\n", item)
    doi = item.get('DOI')
    title = item.get('title', [''])[0]
    abstract = item.get('abstract', 'Abstract not available.')
    referenced_by_count = item.get('is-referenced-by-count', 0)
    
    return {
        "DOI": doi,
        "Title": title,
        "Abstract": abstract,
        "Referenced By Count": referenced_by_count
    }

def get_crossref_metadata(doi):
    """Queries CrossRef API for a specific DOI and retrieves metadata."""
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url)
        response.raise_for_status()        
        data = response.json()
        if 'message' in data:
            return extract_doi_metadata(data['message'])
        else:
            handleExceptionalMessage(f"No message present in CrossRef response for DOI: {doi}")
    except requests.exceptions.RequestException as e:
        handleExceptionalMessage(f"Error fetching data from CrossRef: {e}")

@app.route('/extract_doi_text_content', methods=['POST'])
def extract_doi_text_content():
    """Attempts to visit the DOI URL and extract the text content from the html or PDF."""
    doi = request.json.get("doi", "")
    
    if not doi:
        handleExceptionalMessage("Must provide a DOI.")
    
    if not doi_pattern.match(doi):
        handleExceptionalMessage(f"Invalid DOI format. ''{doi}''")
    
    return extract_url_text_content(f"https://doi.org/{doi}")

@app.route('/extract_url_text_content', methods=['POST'])
def extract_url_text_content():
    url = request.json.get("url", "")
    if not url:
        handleExceptionalMessage("Must provide a URL.")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'application/pdf' in content_type:
            return extract_text_from_pdf(response.content)
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text(separator="\n").strip()
            return text_content
    except requests.exceptions.RequestException as e:
        handleExceptionalMessage(f"Error fetching URL ({url}) page content: {e}")

def extract_text_from_pdf(pdf_content):
    """Extracts text from PDF content using PyPDF2."""
    try:
        pdf_reader = PdfReader(BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        handleExceptionalMessage(f"Error extracting text from PDF: {e}")

def handleExceptionalMessage(message):
    print(message)
    raise Exception(message)


@app.route('/get_dois_and_citation_counts_by_keyword', methods=['POST'])
def get_dois_and_citation_counts_by_keyword():
    max_retries=5
    initial_delay=0.5
    keyword = request.json.get("keyword", "")
    """Queries CrossRef API by keyword and retrieves all related DOIs and their citation counts with retries."""
    url = "https://api.crossref.org/works"
    results = []
    cursor = "*"
    rows_per_page = 20  # Number of rows to retrieve per request
    
    total_results = 0
    retry_count = 0
    delay = initial_delay  # Initial delay in seconds

    while retry_count < max_retries:
        try:
            # First request to determine total results or continue paginating
            params = {
                "query": keyword,
                "rows": rows_per_page,
                "cursor": cursor
            }

            response = requests.get(url, params=params)
            
            # Handle HTTP status 429 (Too Many Requests) or other recoverable errors
            if response.status_code == 429:
                raise requests.exceptions.HTTPError("Too Many Requests (429)")
            response.raise_for_status()  # Check for request errors
            
            data = response.json()
            
            if total_results == 0:
                # First call, set total_results
                total_results = data.get("message", {}).get("total-results", 0)
                print(f"Total number of results for '{keyword}': {total_results}")

            # Add the page of results
            if 'message' in data and 'items' in data['message']:
                
                results.extend([extract_doi_metadata(item) for item in data['message']['items']])

            # Update cursor for pagination
            cursor = data.get("message", {}).get("next-cursor")
            if not cursor or len(results) >= total_results:
                break  # Exit if no more pages or enough results fetched

            # Reset retry count after a successful request
            retry_count = 0
            delay = initial_delay

            # Respect rate limits (sleep between requests)
            time.sleep(delay)
        
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}, retrying in {delay} seconds...")
            
            # Increment retry count and apply exponential backoff
            retry_count += 1
            if retry_count >= max_retries:
                print(f"Max retries reached. Exiting after {retry_count} attempts.")
                break

            # Wait for the delay period (exponential backoff)
            time.sleep(delay)
            delay *= 2  # Exponentially increase delay after each retry
    
    return results




# Main entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
