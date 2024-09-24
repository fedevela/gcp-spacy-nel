from flair.models import SequenceTagger
from flair.data import Sentence
import requests
import sys
import time


def perform_ner_on_abstract(abstract):
    """
    Performs Named Entity Recognition (NER) on the given abstract using Flair.

    Args:
        abstract (str): The abstract text to perform NER on.
    
    Returns:
        dict: A dictionary containing NER tags and entities.
    """
    # Load the NER tagger
    print("Load the NER tagger")
    tagger = SequenceTagger.load("ner")

    # Create a sentence
    print("Create a sentence")
    sentence = Sentence(abstract)

    # Predict NER tags
    print("Predict NER tags")
    tagger.predict(sentence)

    # Print the entities
    print("******** Print the entities")
    return sentence.to_dict()


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
        response.raise_for_status()  # Check for request errors
        
        data = response.json()
        if 'message' in data:
            return extract_doi_metadata(data['message'])
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CrossRef: {e}")
        return None

def get_dois_and_citation_counts_by_keyword(keyword, max_retries=5, initial_delay=0.5):
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

def main():
    if len(sys.argv) < 3:
        print("Usage: doi_explore <command> <parameter>")
        sys.exit(1)

    command = sys.argv[1]
    parameter = sys.argv[2]

    if command == "doi2word":
        metadata = get_crossref_metadata(parameter)
        if metadata:
            print(perform_ner_on_abstract(metadata.get("Abstract","")).get("entities",[]))
        else:
            print("No metadata found for the provided DOI.")
    elif command == "word2doi":
        results = get_dois_and_citation_counts_by_keyword(parameter)
        if results:
            for result in results:
                print(result)
        else:
            print("No related DOIs found for the provided keyword.")
    else:
        print("Invalid command. Use 'doi2word' or 'word2doi'.")

if __name__ == "__main__":
    main()
