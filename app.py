from flask import Flask, request, jsonify
import spacy

# Initialize the Flask app
app = Flask(__name__)

# Load the spaCy model with NEL
nlp = spacy.load("en_core_web_lg")

@app.route('/process', methods=['POST'])
def process_text():
    # Get the text from the request
    content = request.json
    paragraph = content.get("paragraph", "")

    # Process the paragraph using spaCy
    doc = nlp(paragraph)

    # Extract named entities and their labels
    entities = [
        {"text": ent.text, "label": ent.label_}
        for ent in doc.ents
    ]

    # Return the entities as JSON
    return jsonify({"entities": entities})

# Main entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
