from flask import Flask, jsonify, request, render_template
import logging
import yaml
from services import EmailClient, PDFDataExtractor, DatabaseClient
import requests

# Load YAML configuration file
try:
    with open('configure.yaml', 'r') as file:
        config = yaml.safe_load(file)
except Exception as e:
    logging.error(f"Failed to load configuration file: {e}")
    raise SystemExit(e)

app = Flask(__name__)

# Constants
LOCAL_DEPLOYMENT_SERVER_URL = "http://127.0.0.1:5000"

@app.route('/')
def home():
    return "Welcome to the Email Processing API.", 200
    #return render_template('home.html'), 404  # Render home.html with a 404 status code

@app.route('/process-emails', methods=['POST'])
def process_emails():
    try:
        email_client = EmailClient(config['email_user'], config['email_pass'], config['imap_url'])
        email_ids = email_client.search_emails()
        email_client.download_attachments(email_ids)

        pdf_extractor = PDFDataExtractor(config['input_directory'], config['output_directory'])
        combined_data = pdf_extractor.combine_data()
        pdf_extractor.save_to_json(combined_data)
        
        db_client = DatabaseClient(config['db_host'], config['db_database'], config['db_user'], config['db_password'], config['db_port'])
        for data in combined_data:
            db_client.insert_data(data)

        db_client.close()
        return jsonify({"message": "Processed emails successfully", "processed_files": len(combined_data)})
    except Exception as e:
        logging.error(f"An error occurred during processing: {e}")
        return jsonify({"error": f"An error occurred during processing: {e}"}), 500

@app.route('/check-db-connection')
def check_db_connection():
    try:
        db_client = DatabaseClient(config['db_host'], config['db_database'], config['db_user'], config['db_password'], config['db_port'])
        db_client.connect()
        db_client.close()
        return jsonify({"message": "Database connection successful"})
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return jsonify({"error": "Database connection failed"}), 500

@app.route('/check-url-connection')
def check_url_connection():
    try:
        response = requests.get(LOCAL_DEPLOYMENT_SERVER_URL)
        if response.status_code == 200:
            return jsonify({"message": "URL connection successful"})
        else:
            return jsonify({"error": "URL connection failed"}), response.status_code
    except Exception as e:
        logging.error(f"URL connection failed: {e}")
        return jsonify({"error": "URL connection failed"}), 500

@app.route('/check-both-connections')
def check_both_connections():
    try:
        # Check DB Connection
        db_client = DatabaseClient(config['db_host'], config['db_database'], config['db_user'], config['db_password'], config['db_port'])
        db_client.connect()
        db_client.close()
        
        # Check URL Connection
        response = requests.get(LOCAL_DEPLOYMENT_SERVER_URL)
        assert response.status_code == 200, "URL connection failed"
        
        return jsonify({"message": "Both Database and URL connections are successful"})
    except Exception as e:
        logging.error(f"Connection check failed: {e}")
        return jsonify({"error": "Connection check failed"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)