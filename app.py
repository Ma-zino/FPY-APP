from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
from collections import defaultdict
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/'

# Global variables to store data
fpy_data = defaultdict(lambda: [0, 0])
parts_tested_data = defaultdict(int)
selected_description = None
selected_machine = None
selected_date = None  # Expected format: MM/DD/YYYY
file_path = None
file_name = None
machines = defaultdict(list)
description_dates = defaultdict(set)

@app.route('/')
def index():
    global selected_description, selected_date, machines, fpy_data, description_dates, file_name
    sorted_fpy_data = dict(sorted(fpy_data.items()))  # Sort the fpy_data by hour
    description_dates_list = {k: list(v) for k, v in description_dates.items()}  # Convert sets to lists
    
    # Calculate totals
    total_tested_parts = sum(data[0] for data in fpy_data.values())
    total_pass_parts = sum(data[1] for data in fpy_data.values())
    total_fail_parts = total_tested_parts - total_pass_parts
    total_fpy = (total_pass_parts / total_tested_parts * 100) if total_tested_parts != 0 else 0
    
    return render_template('index.html',
                           selected_description=selected_description,
                           selected_date=selected_date,
                           machines=machines,
                           fpy_data=sorted_fpy_data,
                           description_dates=description_dates_list,
                           file_name=file_name,
                           total_tested_parts=total_tested_parts,
                           total_pass_parts=total_pass_parts,
                           total_fail_parts=total_fail_parts,
                           total_fpy=total_fpy)

@app.route('/upload', methods=['POST'])
def upload_file():
    global file_path, file_name, selected_description, machines, description_dates
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    # Save the uploaded file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    file_name = file.filename
    
    # Extract descriptions, machines, and dates
    extract_description(file_path)
    extract_machines(file_path)
    extract_dates(file_path)
    
    return redirect(url_for('index'))

def extract_description(file_path):
    global selected_description, machines
    descriptions = []
    try:
        df = pd.read_csv(file_path)
        print("CSV file read successfully")
        for _, row in df.iterrows():
            if len(row) > 4:
                description = row.iloc[3]
                machine = row.iloc[4].strip()
                print(f"Description: {description}, Machine: {machine}")
            else:
                print("Row does not have enough columns:", row)

            if description not in descriptions:
                descriptions.append(description)
            if machine not in machines[description]:
                machines[description].append(machine)
        if descriptions:
            selected_description = descriptions[0]
            print(f"Selected description: {selected_description}")
    except Exception as e:
        print("Error processing CSV file:", e)

@app.route('/charts')
def charts():
    global fpy_data
    # Sort FPY data by hour
    sorted_fpy_data = dict(sorted(fpy_data.items()))
    total_tested_parts = sum(data[0] for data in fpy_data.values())
    total_pass_parts = sum(data[1] for data in fpy_data.values())
    total_fail_parts = total_tested_parts - total_pass_parts
    total_fpy = (total_pass_parts / total_tested_parts * 100) if total_tested_parts != 0 else 0

    return render_template('charts.html',
                           fpy_data=sorted_fpy_data,
                           total_tested_parts=total_tested_parts,
                           total_pass_parts=total_pass_parts,
                           total_fail_parts=total_fail_parts,
                           total_fpy=total_fpy)


def extract_machines(file_path):
    global machines
    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            description = row.iloc[3]
            machine = row.iloc[4].strip()
            if machine not in machines[description]:
                machines[description].append(machine)
        print(f"Machines: {machines}")
    except Exception as e:
        print("Error extracting machines from CSV file:", e)

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
    global selected_description, selected_machine, selected_date, fpy_data, parts_tested_data
    selected_description = request.form.get('description')
    selected_machine = request.form.get('machine')
    selected_date = request.form.get('date')
    
    # Process the CSV file and group data by hour (for the main page charts)
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
            machine = row.iloc[4]
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

# --------- New Shift Data Processing Functions ---------
def process_shifts(file_path):
    # Group overall shift data into: Morning, Afternoon, Night
    shift_data = {"Morning": [0, 0], "Afternoon": [0, 0], "Night": [0, 0]}
    try:
        current_date = datetime.strptime(selected_date, "%m/%d/%Y")
        next_date = current_date + timedelta(days=1)
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            description = row.iloc[3]
            date_time_parts = row.iloc[1].split()
            if len(date_time_parts) < 2:
                continue
            date_str, time_str = date_time_parts
            try:
                row_date = datetime.strptime(date_str, "%m/%d/%Y")
            except Exception:
                continue
            try:
                hour = int(time_str.split(':')[0])
            except Exception:
                continue
            state = row.iloc[2].lower()
            if description != selected_description:
                continue
            
            # Determine shift key based on hour and date
            if row_date.date() == current_date.date():
                if 6 <= hour < 14:
                    key = "Morning"
                elif 14 <= hour < 22:
                    key = "Afternoon"
                elif hour >= 22:
                    key = "Night"
                else:
                    continue
            elif row_date.date() == next_date.date() and hour < 6:
                key = "Night"
            else:
                continue

            shift_data[key][0] += 1  # parts tested
            if state == "pass":
                shift_data[key][1] += 1  # pass count
        print(f"Shift data: {shift_data}")
    except Exception as e:
        print("Error processing shift data:", e)
    return shift_data

def process_hours_by_shift(file_path):
    # Groups data by hour for each shift.
    hours_by_shift = {"Morning": {}, "Afternoon": {}, "Night": {}}
    try:
        df = pd.read_csv(file_path)
        current_date = datetime.strptime(selected_date, "%m/%d/%Y")
        next_date_obj = current_date + timedelta(days=1)
        next_date = f"{next_date_obj.month}/{next_date_obj.day}/{next_date_obj.year}"
        for _, row in df.iterrows():
            description = row.iloc[3]
            date_time = row.iloc[1].split()
            if len(date_time) < 2:
                continue
            date_str, time_str = date_time
            try:
                hour = int(time_str.split(':')[0])
            except Exception:
                continue
            state = row.iloc[2].lower()
            if description != selected_description:
                continue

            shift_key = None
            if date_str == selected_date and 6 <= hour < 14:
                shift_key = "Morning"
            elif date_str == selected_date and 14 <= hour < 22:
                shift_key = "Afternoon"
            elif (date_str == selected_date and hour >= 22) or (date_str == next_date and hour < 6):
                shift_key = "Night"
            if shift_key is None:
                continue

            if hour not in hours_by_shift[shift_key]:
                hours_by_shift[shift_key][hour] = [0, 0, 0]  # [parts_tested, pass_count, fail_count]
            hours_by_shift[shift_key][hour][0] += 1
            if state == "pass":
                hours_by_shift[shift_key][hour][1] += 1
            else:
                hours_by_shift[shift_key][hour][2] += 1
        print(f"Hours by shift: {hours_by_shift}")
    except Exception as e:
        print("Error processing hours by shift:", e)
    return hours_by_shift

# ------ Updated Shift Route ------
@app.route('/shift')
def shift():
    global file_path, selected_description, selected_date
    # Ensure that file_path, selected_date, and selected_description exist
    if not file_path or not selected_date or not selected_description:
        return render_template('shift.html',
                               selected_date=selected_date,
                               shift_data={},
                               hours_by_shift={},
                               total_shift_fpy={})
    
    shift_data = process_shifts(file_path)
    hours_by_shift = process_hours_by_shift(file_path)

    total_shift_fpy = {}
    for shift_key, data in shift_data.items():
        total = data[0]
        passes = data[1]
        total_shift_fpy[shift_key] = (passes / total * 100) if total != 0 else 0

    return render_template('shift.html',
                           selected_date=selected_date,
                           shift_data=shift_data,
                           hours_by_shift=hours_by_shift,
                           total_shift_fpy=total_shift_fpy)

@app.route('/bcp')
def bcp():
    # Process data for all machines at once.
    all_machines_data = {}  # Key: machine name, Value: dict with hour => [parts_tested, pass_count, fail_count]

    if file_path:
        try:
            df = pd.read_csv(file_path)
            # Initialize data for each machine based on the machines global variable.
            for desc, machine_list in machines.items():
                for machine in machine_list:
                    all_machines_data[machine] = defaultdict(lambda: [0, 0, 0])
            
            for _, row in df.iterrows():
                description = row.iloc[3]
                machine = row.iloc[4].strip()
                date_time = row.iloc[1]
                try:
                    # Process data for all machines regardless of date and description.
                    time_str = date_time.split()[1]
                    hour = int(time_str.split(':')[0])
                except Exception:
                    continue
                state = row.iloc[2].lower()
                if machine in all_machines_data:
                    all_machines_data[machine][hour][0] += 1
                    if state == "pass":
                        all_machines_data[machine][hour][1] += 1
                    else:
                        all_machines_data[machine][hour][2] += 1
        except Exception as e:
            print("Error processing multi-machine data:", e)
    
    # Compute aggregated FPY for ICT machines
    ict_list = ["ICT1", "ICT2", "ICT3", "ICT4"]
    aggregated_fpy = {}
    for m in ict_list:
        total_parts = 0
        total_pass = 0
        if m in all_machines_data:
            for hour, vals in all_machines_data[m].items():
                total_parts += vals[0]
                total_pass += vals[1]
        aggregated_fpy[m] = (total_pass / total_parts * 100) if total_parts else 0

    return render_template('bcp.html',
                           all_machines_data=all_machines_data,
                           aggregated_fpy=aggregated_fpy)

@app.route('/reset')
def reset():
    global fpy_data, parts_tested_data, selected_description, selected_machine, selected_date, file_path, file_name, machines, description_dates
    fpy_data.clear()
    parts_tested_data.clear()
    selected_description = None
    selected_machine = None
    selected_date = None
    file_path = None
    file_name = None
    machines.clear()
    description_dates.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
