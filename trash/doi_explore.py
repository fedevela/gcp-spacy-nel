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
