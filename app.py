from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
from collections import defaultdict
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/'

# Global variables to store data
fpy_data = defaultdict(lambda: [0, 0])
parts_tested_data = defaultdict(int)
selected_description = None
selected_project = None
selected_date = None
file_path = None
file_name = None
projects = defaultdict(list)
description_dates = defaultdict(set)

@app.route('/')
def index():
    global selected_description, selected_date, projects, fpy_data, description_dates, file_name
    sorted_fpy_data = dict(sorted(fpy_data.items()))  # Sort the fpy_data by hour
    description_dates_list = {k: list(v) for k, v in description_dates.items()}  # Convert sets to lists
    return render_template('index.html', selected_description=selected_description, selected_date=selected_date, projects=projects, fpy_data=sorted_fpy_data, description_dates=description_dates_list, file_name=file_name)

@app.route('/upload', methods=['POST'])
def upload_file():
    global file_path, file_name, selected_description, projects, description_dates
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    # Save the uploaded file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    file_name = file.filename
    
    # Extract descriptions, projects, and dates
    extract_description(file_path)
    extract_projects(file_path)
    extract_dates(file_path)
    
    return redirect(url_for('index'))

def extract_description(file_path):
    global selected_description, projects
    descriptions = []
    try:
        df = pd.read_csv(file_path)
        print("CSV file read successfully")
        for _, row in df.iterrows():
            if len(row) > 4:
                description = row.iloc[3]
                project = row.iloc[4].strip()
                print(f"Description: {description}, Project: {project}")
            else:
                print("Row does not have enough columns:", row)

            if description not in descriptions:
                descriptions.append(description)
            if project not in projects[description]:
                projects[description].append(project)
        if descriptions:
            selected_description = descriptions[0]
            print(f"Selected description: {selected_description}")
    except Exception as e:
        print("Error processing CSV file:", e)

def extract_projects(file_path):
    global projects
    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            description = row.iloc[3]
            project = row.iloc[4].strip()
            if project not in projects[description]:
                projects[description].append(project)
        print(f"Projects: {projects}")
    except Exception as e:
        print("Error extracting projects from CSV file:", e)

def extract_dates(file_path):
    global description_dates
    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            date_str, _ = row.iloc[1].split()
            description = row.iloc[3]
            description_dates[description].add(date_str)
        print(f"Description Dates: {description_dates}")
    except Exception as e:
        print("Error extracting dates from CSV file:", e)

@app.route('/process', methods=['POST'])
def process_data():
    global selected_description, selected_project, selected_date, fpy_data, parts_tested_data
    selected_description = request.form.get('description')
    selected_project = request.form.get('project')
    selected_date = request.form.get('date')
    
    # Process the CSV file
    process_csv(file_path)
    
    return redirect(url_for('index'))

def process_csv(file_path):
    global fpy_data, parts_tested_data
    fpy_data.clear()
    parts_tested_data.clear()
    
    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            description = row.iloc[3]
            project = row.iloc[4]
            date_str, time_str = row.iloc[1].split()
            hour = int(time_str.split(':')[0])
            state = row.iloc[2].lower()
            
            if description == selected_description and date_str == selected_date:
                fpy_data[hour][0] += 1
                if state == "pass":
                    fpy_data[hour][1] += 1
                
                parts_tested_data[hour] += 1
        print(f"FPY Data: {fpy_data}")
        print(f"Parts Tested Data: {parts_tested_data}")
    except Exception as e:
        print("Error processing CSV file:", e)

if __name__ == '__main__':
    app.run(debug=True)