from flask import Flask, render_template, request
import pyodbc
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# Load environment variables
load_dotenv()

app = Flask(__name__)

# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')

    connection_string = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
    )

    return pyodbc.connect(connection_string)

# ---------------- BLOB STORAGE CONNECTION ----------------
def upload_to_blob(file):
    if not file or file.filename == '':
        return None

    connection_string = os.getenv('BLOB_CONNECTION_STRING')
    container_name = 'reports'

    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string
    )

    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(file.filename)

    # overwrite=True allows re-uploading a file with the same name
    blob_client.upload_blob(file, overwrite=True)

    return file.filename

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    patient_name = request.form['patient_name']
    symptoms = request.form['symptoms'].lower()
    report = request.files.get('report')

    # Prediction logic
    if 'chest pain' in symptoms:
        priority = 'High'
        waiting_time = 5
    elif 'fever' in symptoms:
        priority = 'Medium'
        waiting_time = 20
    else:
        priority = 'Low'
        waiting_time = 45

    # Upload file to Azure Blob Storage
    report_filename = upload_to_blob(report)

    # Save data to Azure SQL Database
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        INSERT INTO patients
        (patient_name, symptoms, priority_level, waiting_time, report_filename)
        VALUES (?, ?, ?, ?, ?)
        ''',
        patient_name,
        symptoms,
        priority,
        waiting_time,
        report_filename
    )

    conn.commit()
    cursor.close()
    conn.close()

    return f'''
    <h1>Prediction Result</h1>
    <p>Patient: {patient_name}</p>
    <p>Symptoms: {symptoms}</p>
    <p>Priority: {priority}</p>
    <p>Estimated Waiting Time: {waiting_time} minutes</p>
    <p>Uploaded File: {report_filename or "No file uploaded"}</p>
    <p>✅ Data saved to Azure SQL Database!</p>
    <p>✅ File uploaded to Azure Blob Storage!</p>
    <br>
    <a href="/">Go Back</a>
    '''

if __name__ == '__main__':
    app.run(debug=True)