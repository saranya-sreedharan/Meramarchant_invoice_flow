import decimal
import fitz
import imaplib
import email
import os
import re
import glob
import logging
import yaml
import string
import random
import time
import mysql.connector
import pdfplumber
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Setup logging
logging.basicConfig(filename='process_emails.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# Load YAML configuration file
try:
    with open('configure.yaml', 'r') as file:
        config = yaml.safe_load(file)
except Exception as e:
    logging.error(f"Failed to load configuration file: {e}")
    raise SystemExit(e)

# Access the variables from the YAML file
EMAIL_USER = config['email_user']
EMAIL_PASS = config['email_pass']
IMAP_URL = config['imap_url']
INPUT_DIRECTORY = config['input_directory']
OUTPUT_DIRECTORY = config['output_directory']
DB_HOST = config['db_host']
DB_DATABASE = config['db_database']
DB_USER = config['db_user']
DB_PASSWORD = config['db_password']
DB_PORT = config['db_port']

# Function and class definitions (EmailClient, PDFDataExtractor, DatabaseClient) go here
# Ensure each class and function is integrated properly according to the functionalities of both scripts

class EmailClient:
    def __init__(self, user, password, imap_url):
        self.user = user
        self.password = password
        self.imap_url = imap_url
        self.mail = self.connect_to_email()

    def connect_to_email(self):
        mail = imaplib.IMAP4_SSL(self.imap_url)
        mail.login(self.user, self.password)
        return mail

    def search_emails(self, folder='inbox'):
        self.mail.select(folder)
        result, data = self.mail.search(None, 'ALL') #add "ALL" to see all the files
        return data[0].split()

    def download_attachments(self, email_ids, download_folder=INPUT_DIRECTORY):
        if not os.path.exists(download_folder):
            os.makedirs(download_folder, exist_ok=True)  # Create the directory if it doesn't exist
            print(f"Directory {download_folder} created")
        for num in email_ids:
            result, data = self.mail.fetch(num, '(RFC822)')
            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)

            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if 'pdf' in part.get_content_type():
                    filename = part.get_filename()
                    if filename:
                        filename = sanitize_filename(filename)
                        filepath = os.path.join(download_folder, filename)

                        # Check if the file already exists
                        if os.path.exists(filepath):
                            print(f"File {filename} already exists. Skipping download.")
                            continue

                        # File does not exist, download it
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                            print(f"Downloaded {filename}")

def sanitize_filename(filename):
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.replace('\r', '').replace('\n', '')
    return filename

class PDFDataExtractor:
    def __init__(self, input_directory=INPUT_DIRECTORY, output_directory=OUTPUT_DIRECTORY):
        self.input_directory = input_directory
        self.output_directory = output_directory
        
        if not os.path.exists(input_directory):
            os.makedirs(input_directory, exist_ok=True)
            print(f"Input directory {input_directory} created")

        # Check and create output directory if necessary
        if not os.path.exists(output_directory):
            os.makedirs(output_directory, exist_ok=True)
            print(f"Output directory {output_directory} created")

    def get_all_pdfs(self):
        return sorted(glob.glob(os.path.join(self.input_directory, '*.pdf')))

    def extract_invoice_data(self, pdf_path):
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

        data = {
            "AnchorName": self.extract_field(text, r"^(.+?)\s+TAX INVOICE", "Company name not found"),
            "DistributorName": self.extract_field(text, r"Name\s*:\s*(.+?)\s+(?=\w+\sNo\.|\w+\s:)", "Name not found"),
            "DistributorCode": self.extract_field(text, r"Bill To Party\s*:\s*(\d+)", "Bill to party not found"),
            "DeliveryCode": self.extract_field(text, r"Delivery at\s*:\s*(\d+)", "Delivery at not found"),
            "InvoiceNo": self.extract_field(text, r"INVOICE No\. :\s*(\d+)", "Invoice no not found"),
            "InvoiceAmount": self.extract_field(text, r"TOTAL INVOICE AMOUNT \(ROUND OFF\) :\s*([0-9,\.]+)", "Invoice amount not found"),
            "InvoiceDate": self.extract_field(text, r"INVOICE No\. :\s*\d+\s+Date\s*:\s*(\d{2}-\w{3}-\d{4})", "Invoice date not found"),
            "PhoneNo": self.extract_field(text, r"PHONE No\. :\s*(\d+)", "Phone no not found"),
            "DistributorEmailAddress": self.extract_field(text, r"E-Mail\s*:\s*([^\n]+)", "Distributor email address not found"),
            "CFA_Email": self.extract_field(text, r"Fax No\.\s*:.*?([\w\.-]+@[\w\.-]+\.\w+)", "CFA Email not found"),
            "CFAName": self.extract_field(text, r"Invoiced by\s*:\s*([^\n]+)", "CFA Name not found")
        }
        return data

    def extract_field(self, pdf_text, pattern, default_value="Not found"):
        match = re.search(pattern, pdf_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        else:
            return default_value

    def extract_payment_info(self, extracted_text):
        patterns = {
            'PaymentType': r"''You May Also\s+(IMPS/RTGS/NEFT)\s+to",
            'RemittanceBank': r"/RTGS/NEFT to\s+([A-Z\s]+),",
            'RemittanceBankCode': r"IFSC Code: (\w+)",
            'RemittanceBankAccountNo': r"Your Account is\s+(\d+)"
        }
        payment_info = {key: re.search(pattern, extracted_text, re.IGNORECASE).group(1) if re.search(pattern, extracted_text, re.IGNORECASE) else 'Not found' for key, pattern in patterns.items()}
        return payment_info

    def extract_address_info(self, pdf_path):
        with fitz.open(pdf_path) as doc:
            extracted_text = ''.join([page.get_text() for page in doc])

        address_pattern = r"Address\s*:\s*(.+?)\s*\n\s*Delivery at :"
        address_match = re.search(address_pattern, extracted_text, re.IGNORECASE | re.DOTALL)
        address = address_match.group(1).strip() if address_match else 'Address not found'
        
        address_del = re.findall(r"^.+?\)", address)
        if address_del:
            address = address.replace(address_del[0], '')

        address_dict = {'DeliveryAddress': address.replace('\n', '').replace('\r', '').replace('\t', '').strip()}
        return {'DeliveryAddress': address}

    def combine_data(self):
        pdf_paths = self.get_all_pdfs()
        all_combined_data = []
        for path in pdf_paths:
            print(f"Processing file: {path}")  # Print the file name
            try:
                invoice_data = self.extract_invoice_data(path)

                with fitz.open(path) as doc:  # Using PyMuPDF to extract text for payment and address info
                    extracted_text = ''.join([page.get_text() for page in doc])

                payment_info = self.extract_payment_info(extracted_text)  # Extract payment info from the text
                address_info = self.extract_address_info(path)  # Extract address info from the text

                # Combine all the extracted info and include the pdf_path
                combined_entry = {
                    **invoice_data, 
                    **payment_info, 
                    **address_info, 
                    'pdf_path': path  # Include pdf_path here
                }
                all_combined_data.append(combined_entry)
            except Exception as e:
                print(f"Error processing file {path}: {e}")  # Print any error
        return all_combined_data

    def save_to_json(self, combined_data):
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)
        for data in combined_data:
            base_filename = os.path.basename(data['pdf_path'])  # Now this should work
            json_filename = os.path.splitext(base_filename)[0] + '.json'
            file_path = os.path.join(self.output_directory, json_filename)
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)

def generate_unique_code(length=10):
    """Generates a unique code of specified length."""
    characters = string.ascii_letters + string.digits
    unique_code = ''.join(random.choice(characters) for _ in range(length))
    return unique_code

class DatabaseClient:
    def __init__(self, host, database, user, password,port):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.conn = self.connect()
        self.cursor = self.conn.cursor()

    def connect(self):
        return mysql.connector.connect(host=self.host, database=self.database, user=self.user, password=self.password,port=self.port)
    
    def record_exists(self, invoice_no):
        query = "SELECT EXISTS(SELECT 1 FROM raw_imports WHERE InvoiceNo = %s)"
        self.cursor.execute(query, (invoice_no,))
        return self.cursor.fetchone()[0]

    def insert_data(self, data):
        print(f"Inserting data with PDF path: {data['pdf_path']}")
        if not self.record_exists(data["InvoiceNo"]):
            unique_code = generate_unique_code(10)
            query = """
            INSERT INTO raw_imports (code, AnchorName, DistributorName, DistributorCode, DeliveryCode, InvoiceNo, InvoiceAmount, InvoiceDate, PhoneNo, DistributorEmailAddress, CFA_Email, CFAName, pdf_path, PaymentType, RemittanceBank, RemittanceBankCode, RemittanceBankAccountNo, DeliveryAddress)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            data_tuple = (
                unique_code, data["AnchorName"], data["DistributorName"], data["DistributorCode"], data["DeliveryCode"], 
                data["InvoiceNo"], data["InvoiceAmount"], data["InvoiceDate"], data["PhoneNo"], 
                data["DistributorEmailAddress"], data["CFA_Email"], data["CFAName"], data['pdf_path'], data["PaymentType"], 
                data["RemittanceBank"], data["RemittanceBankCode"], data["RemittanceBankAccountNo"], 
                data["DeliveryAddress"]
            )
            self.cursor.execute(query, data_tuple)
            self.conn.commit()
        else:
            print(f"Record with InvoiceNo {data['InvoiceNo']} already exists.")
    def close(self):
        self.cursor.close()
        self.conn.close()

def main():
    while True:
        try:
            logging.info("Starting email check and processing cycle.")
            email_client = EmailClient(EMAIL_USER, EMAIL_PASS, IMAP_URL)
            email_ids = email_client.search_emails()
            email_client.download_attachments(email_ids)

            pdf_extractor = PDFDataExtractor(INPUT_DIRECTORY, OUTPUT_DIRECTORY)
            combined_data = pdf_extractor.combine_data()  # Ensure this method exists and processes all PDFs correctly
            pdf_extractor.save_to_json(combined_data)

            db_client = DatabaseClient(DB_HOST, DB_DATABASE, DB_USER, DB_PASSWORD, DB_PORT)
            for data in combined_data:
                db_client.insert_data(data)
            db_client.close()

            logging.info("Completed email check and processing cycle.")
        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")

        logging.info("Sleeping for 1 hour before next cycle.")
        time.sleep(3600)  # Sleep for 1 hour (3600 seconds), adjust as needed

if __name__ == '__main__':
    main()