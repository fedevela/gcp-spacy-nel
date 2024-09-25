import logging
import re
import requests
import requests
import time
import traceback
import uuid

from bs4 import BeautifulSoup
from flair.models import SequenceTagger
from flair.data import Sentence
from flask import Flask, request
from io import BytesIO
from PyPDF2 import PdfReader
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS
# CORS(app)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000", "methods": ["GET", "POST", "OPTIONS"], "supports_credentials": True}})

# Load the NER tagger
flair_ner_tagger = SequenceTagger.load("ner")

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

newlines_pattern = re.compile(r' *[\n|\r|\r\n]+ *')
whitespace_pattern = re.compile(r'[\t\f\v ]+')
paragraph_split_pattern = re.compile(r'\n')
doi_compiled_regex = re.compile(r'^10.\d{4,9}/[-._;()/:A-Z0-9]+$', re.IGNORECASE)

ner_type_to_wikidata_qid = {
    'PER': 'Q5',        # human
    'LOC': 'Q618123',   # geographical object
    'ORG': 'Q43229',    # organization
}

def clean_text(text):
    """
    Cleans the given text by keeping only paragraphs and removing all other whitespace or orphaned words.

    Args:
        text (str): The text to clean.
    
    Returns:
        str: The cleaned text with only paragraphs.
    """
    no_space_text = whitespace_pattern.sub(' ', text)
    no_multiple_lines_text = newlines_pattern.sub('\n', no_space_text)
    no_multiple_lines_text_2 = newlines_pattern.sub('\n', no_multiple_lines_text)
    paragraphs = paragraph_split_pattern.split(no_multiple_lines_text_2)
    cleaned_paragraphs = [para for para in paragraphs if len(para.split()) > 5]
    return ' '.join(cleaned_paragraphs)

def perform_ner_with_text(sentence_text):
    """
    Performs Named Entity Recognition (NER) on the given abstract using Flair.

    Args:
        sentence_text (str): The text to perform NER on.
    
    Returns:
        list: A list of entities extracted from the abstract.
    """
    clean_abstract = clean_text(sentence_text)
    sentence = Sentence(clean_abstract)
    logging.debug("Predicting NER tags...")
    flair_ner_tagger.predict(sentence)
    logging.debug("... done!!!")
    # Extract entities
    entities = []
    unique_entities = set()

    for entity in sentence.get_spans('ner'):
        text_type_combo = (entity.text, entity.tag)
        if text_type_combo not in unique_entities:
            entities.append({
                'text': entity.text,
                'type': entity.tag,
                'score': entity.score
            })
            unique_entities.add(text_type_combo)
    return entities

def query_wikidata(entity_text):
    """
    Query Wikidata API to find the entity matching the given text.

    Args:
        entity_text (str): The text of the entity to search for.

    Returns:
        dict: The JSON response from Wikidata API.
    """
    # Base URL for Wikidata API
    url = "https://www.wikidata.org/w/api.php"

    # Parameters for the API request
    params = {
        'action': 'wbsearchentities',
        'search': entity_text,
        'language': 'en',
        'format': 'json',
        'limit': 1  # Get the top match
    }

    # Implement incrementing rate throttling
    wait_time = 1  # Start with 1 second
    max_wait_time = 60  # Maximum wait time of 60 seconds
    while True:
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logging.warning(f"Received HTTP 429 Too Many Requests. Waiting for {wait_time} seconds.")
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, max_wait_time)  # Exponential backoff
            else:
                handleExceptionalMessage(f"Received unexpected HTTP status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            handleExceptionalMessage(f"An error occurred: {e}")
            

def perform_nel(abstract):
    """
    Performs Named Entity Linking (NEL) on the given abstract using Flair and Wikidata.

    Args:
        abstract (str): The abstract text to perform NEL on.

    Returns:
        list: A list of entities with their linked Wikidata IDs.
    """
    entities = perform_ner_with_text(abstract)
    for entity in entities:
        if 'start_pos' in entity:
            del entity['start_pos']
        if 'end_pos' in entity:
            del entity['end_pos']
    
    # Filter out entities with score less than 0.87 and sort by score in descending order
    filtered_sorted_entities = sorted(
        [entity for entity in entities if entity['score'] >= 0.87],
        key=lambda x: x['score'],
        reverse=True
    )[:100]# Limit to top 100 entities
    linked_entities = []
    total_entities = len(filtered_sorted_entities)
    for index, entity in enumerate(filtered_sorted_entities):
        # Calculate and print progress
        progress = (index + 1) / total_entities * 100
        logging.debug(f"Progress: {progress:.2f}%")
        entity_text = entity['text']
        wikidata_response = query_wikidata(entity_text)
        if wikidata_response and 'search' in wikidata_response and len(wikidata_response['search']) > 0:
            top_match = wikidata_response['search'][0]
            entity['wikidata_id'] = top_match['id']
            entity['wikidata_label'] = top_match.get('label', '')
            entity['wikidata_description'] = top_match.get('description', '')
            linked_entities.append(entity)
        else:
            entity['wikidata_id'] = None
            linked_entities.append(entity)
    return linked_entities

def extract_graph_nodes_and_links_from_paragraph(paragraph, source_url, is_doi=False):
    logging.debug("Performing NER on the abstract...")
    linked_entities = perform_nel(paragraph)
    
    links = []
        
    base_node = ({
        'id': str(uuid.uuid4()),
        'text': source_url,
        'type': 'DOI' if is_doi else 'URL',
        'score': 1.0,
        #TODO: fix the statement below to include full paper wikidata info
        'wikidata_id': None
    })
        
    for entity in linked_entities:
        entity['id'] = str(uuid.uuid4())
        links.append({
            'source': base_node['id'],
            'target': entity['id'],
            'type': 'MENTION',
            'score': entity['score']
        })
        
    # Add a new entity with the source_url
    linked_entities.append(base_node)
    
    return ({"nodes": linked_entities, "links": links})

def extract_doi_metadata(item):
    logging.debug("**** Extracts metadata from a CrossRef API item.", item)
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

def query_crossref_metadata(doi):
    logging.debug("**** Queries CrossRef API for a specific DOI and retrieves metadata.")
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

@app.route('/doi2graph', methods=['POST'])
def post_extract_doi_text_content():
    logging.debug("**** Attempts to visit the DOI URL and extract the text content from the html or PDF")
    doi = request.json.get("doi", "")
    
    if not doi:
        handleExceptionalMessage("Must provide a DOI.")
    
    if not doi_compiled_regex.match(doi):
        handleExceptionalMessage(f"Invalid DOI format. ''{doi}''")
    
    return query_url_text_content(f"https://doi.org/{doi}",True)

@app.route('/url2graph', methods=['POST'])
def post_extract_url_text_content():
    url = request.json.get("url", "")
    return query_url_text_content(url,False)

def query_url_text_content(url, is_doi=False):
    logging.debug("**** Extract URL text content.")
    if not url:
        handleExceptionalMessage("Must provide a URL.")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        text_content = ""
        
        if 'application/pdf' in content_type:
            text_content = extract_text_from_pdf(response.content)
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text(separator="\n").strip()
        return extract_graph_nodes_and_links_from_paragraph(text_content,url,is_doi)
    except requests.exceptions.RequestException as e:
        handleExceptionalMessage(f"Error fetching URL ({url}) page content: {e}")

def extract_text_from_pdf(pdf_content):
    try:
        pdf_reader = PdfReader(BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        handleExceptionalMessage(f"Error extracting text from PDF: {e}")

def handleExceptionalMessage(message):
    logging.exception(message)
    traceback.print_stack()
    raise Exception(message)


# @app.route('/get_dois_and_citation_counts_by_keyword', methods=['POST'])
# def query_crossref_dois_and_citation_counts_by_keyword():
#     logging.debug("**** Queries CrossRef API by keyword and retrieves all related DOIs and their citation counts with retries.")
#     max_retries=5
#     initial_delay=0.5
#     keyword = request.json.get("keyword", "")
#     url = "https://api.crossref.org/works"
#     results = []
#     cursor = "*"
#     rows_per_page = 20  # Number of rows to retrieve per request
    
#     total_results = 0
#     retry_count = 0
#     delay = initial_delay  # Initial delay in seconds

#     while retry_count < max_retries:
#         try:
#             # First request to determine total results or continue paginating
#             params = {
#                 "query": keyword,
#                 "rows": rows_per_page,
#                 "cursor": cursor
#             }

#             response = requests.get(url, params=params)
            
#             # Handle HTTP status 429 (Too Many Requests) or other recoverable errors
#             if response.status_code == 429:
#                 raise requests.exceptions.HTTPError("Too Many Requests (429)")
#             response.raise_for_status()  # Check for request errors
            
#             data = response.json()
            
#             if total_results == 0:
#                 # First call, set total_results
#                 total_results = data.get("message", {}).get("total-results", 0)
#                 print(f"Total number of results for '{keyword}': {total_results}")

#             # Add the page of results
#             if 'message' in data and 'items' in data['message']:
                
#                 results.extend([extract_doi_metadata(item) for item in data['message']['items']])

#             # Update cursor for pagination
#             cursor = data.get("message", {}).get("next-cursor")
#             if not cursor or len(results) >= total_results:
#                 break  # Exit if no more pages or enough results fetched

#             # Reset retry count after a successful request
#             retry_count = 0
#             delay = initial_delay

#             # Respect rate limits (sleep between requests)
#             time.sleep(delay)
        
#         except requests.exceptions.RequestException as e:
#             print(f"Error occurred: {e}, retrying in {delay} seconds...")
            
#             # Increment retry count and apply exponential backoff
#             retry_count += 1
#             if retry_count >= max_retries:
#                 print(f"Max retries reached. Exiting after {retry_count} attempts.")
#                 break

#             # Wait for the delay period (exponential backoff)
#             time.sleep(delay)
#             delay *= 2  # Exponentially increase delay after each retry
    
#     return results

# Main entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
