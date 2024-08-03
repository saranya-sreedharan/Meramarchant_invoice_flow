from flask import Flask, request, jsonify, render_template
import os
import decimal
from services import EmailClient, PDFDataExtractor, DatabaseClient, sanitize_filename
import yaml
from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging
import sys

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

app = Flask(__name__)

# Load configurations
config = {}
try:
    with open('configure.yaml', 'r') as file:
        config = yaml.safe_load(file)
except Exception as e:
    logging.error(f"Failed to load configurations: {e}")
    sys.exit(1)  # Exit if configuration loading fails

# Constants
DATE_FORMAT = "%d-%b-%Y"

@app.route('/')
def home():
    return render_template('home.html')

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
            process_data_entry(data, db_client)

        db_client.close()
        return jsonify({"message": "Processed emails successfully", "processed_files": len(combined_data)})
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"error": "An error occurred during processing"}), 500

def process_data_entry(data, db_client):
    clean_and_convert_data(data)
    truncate_data_fields(data)
    insert_data_into_db(data, db_client)

def clean_and_convert_data(data):
    data['InvoiceAmount'] = clean_invoice_amount(data.get('InvoiceAmount'))
    data['InvoiceDate'] = clean_invoice_date(data.get('InvoiceDate'))

def clean_invoice_amount(invoice_amount_str):
    if invoice_amount_str:
        try:
            return Decimal(invoice_amount_str.replace(',', ''))
        except InvalidOperation:
            logging.warning(f"Invalid invoice amount: {invoice_amount_str}")
    return Decimal(0)

def clean_invoice_date(invoice_date_str):
    if invoice_date_str and invoice_date_str.lower() != 'invoice date not found':
        try:
            return datetime.strptime(invoice_date_str, DATE_FORMAT).strftime("%Y-%m-%d")
        except ValueError as e:
            logging.warning(f"Invalid date format for InvoiceDate: {invoice_date_str}. Error: {e}")
    return None

def truncate_data_fields(data):
    data["DistributorCode"] = data["DistributorCode"][:20] if data.get("DistributorCode") else None
    data["DistributorName"] = data["DistributorName"][:50] if data.get("DistributorName") else None

def insert_data_into_db(data, db_client):
    try:
        db_client.insert_data(data)
    except Exception as e:
        logging.error(f"Failed to insert data: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)