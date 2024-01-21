# app.py

from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
from MySQLdb.cursors import DictCursor
import qrcode 
from datetime import datetime
app = Flask(__name__)

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'raceapp'
app.config['MYSQL_PASSWORD'] = 'password123'
app.config['MYSQL_DB'] = 'race_car_db'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

def get_driver_data(driver_id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM drivers WHERE id = %s", (driver_id,))
    driver_data = cur.fetchone()
    cur.close()
    return driver_data

def get_car_data(car_id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car_data = cur.fetchone()
    cur.close()
    return car_data

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)



def get_events_for_today():
    today = datetime.now().date()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM events WHERE DATE(event_date) = %s", (today,))
    events = cur.fetchall()
    cur.close()
    return events



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    # Fetch and display list of drivers
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM drivers")
    drivers = cur.fetchall()
    cur.close()
    return render_template('index.html', drivers=drivers)

@app.route('/driver_qr/<int:driver_id>')
def driver_qr_code(driver_id):
    # Assuming you have a function to get the driver's data
    driver_data = get_driver_data(driver_id)

    # Generate QR code
    qr_data = f"Driver: {driver_data['first_name']} {driver_data['last_name']}, ID: {driver_data['id']}"
    filename = f"static/qrcodes/driver_{driver_id}.png"
    generate_qr_code(qr_data, filename)

    return send_file(filename, mimetype='image/png')

@app.route('/car_qr/<int:car_id>')
def car_qr_code(car_id):
    # Assuming you have a function to get the driver's data
    car_data = get_car_data(car_id)

    # Generate QR code
    qr_data = f"Driver: {car_data['driver_id']}, Make: {car_data['make']}, Model: {car_data['model']}, ID: {car_data['id']}"
    filename = f"static/qrcodes/car_{car_id}.png"
    generate_qr_code(qr_data, filename)

    return send_file(filename, mimetype='image/png')

@app.route('/driver/<int:driver_id>', methods=['GET', 'POST'])
def driver_profile(driver_id):
    if request.method == 'POST':
        # Handle adding a new note
        note_text = request.form.get('note_text')

        if note_text:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO notes (driver_id, note_text) VALUES (%s, %s)", (driver_id, note_text))
            mysql.connection.commit()
            cur.close()

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM drivers WHERE id = %s", (driver_id,))
    driver = cur.fetchall()
    cur.execute("SELECT * FROM cars WHERE driver_id = %s", (driver_id,))
    cars = cur.fetchall()

    cur.execute("SELECT * FROM check_ins WHERE driver_id = %s", (driver_id,))
    checkedin = cur.fetchall()
    # Fetch notes for the driver
    cur.execute("SELECT * FROM notes WHERE driver_id = %s ORDER BY created_at DESC ", (driver_id,))
    notes = cur.fetchall()
    cur.close()

    return render_template('driver_profile.html', driver=driver, cars=cars, notes=notes, checkedin=checkedin)


@app.route('/check_in', methods=['GET', 'POST'])
def check_in():
    events = get_events_for_today()
    messages = []

    if request.method == 'POST':
        driver_id = request.form.get('driver_id')
        event_id = request.form.get('event_id')

        if driver_id:
            # Check if the car has already checked in for today
            cur = mysql.connection.cursor()
            cur.execute("SELECT checked_in FROM check_ins WHERE driver_id = %s AND event_id = %s ORDER BY check_in_time DESC LIMIT 1", (driver_id, event_id,))
            last_check_in = cur.fetchone()

            # Check if the driver exists
            cur.execute("SELECT id FROM drivers WHERE id = %s", (driver_id,))
            existing_driver = cur.fetchone()

            if not existing_driver:
                messages.append("Driver doesn't exist.")

            if last_check_in and last_check_in['checked_in']:
                messages.append("Car already checked in for today.")

            if not messages:
                cur.execute("INSERT INTO check_ins (driver_id, event_id, checked_in) VALUES (%s, %s, TRUE) ON DUPLICATE KEY UPDATE checked_in = TRUE", (driver_id, event_id,))
                mysql.connection.commit()
                cur.close()
                return redirect(url_for('index'))

    return render_template('check_in.html', messages=messages, events=events)

@app.route('/delete_driver/<int:driver_id>', methods=['POST'])
def delete_driver(driver_id):
    # Check if the driver exists
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM drivers WHERE id = %s", (driver_id,))
    existing_driver = cur.fetchone()

    if existing_driver:
        # Delete check-in data associated with the driver
        cur.execute("DELETE FROM check_ins WHERE driver_id = %s", (driver_id,))

        # Delete the driver and associated cars
        cur.execute("DELETE FROM drivers WHERE id = %s", (driver_id,))
        cur.execute("DELETE FROM cars WHERE driver_id = %s", (driver_id,))
        
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('index'))
    else:
        return "Driver not found"








@app.route('/car/<int:car_id>')
def car_info(car_id):
    # Fetch car details
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car = cur.fetchone()
    cur.close()

    if car:
        return render_template('car_info.html', car=car)
    else:
        return "Car not found"


@app.route('/<filename>', methods=['POST'])
def get_picture():
    return 'upload/'


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return 'File uploaded successfully'

    return 'Invalid file format'

@app.route('/add_driver', methods=['GET', 'POST'])
def add_driver():
    if request.method == 'POST':
        # Get form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        address = request.form['address']
        phone_number = request.form['phone_number']
        dclass = request.form['dclass']

        # Handle file upload (picture)
        if 'picture' in request.files:
            picture = request.files['picture']
            if picture.filename != '':
                picture_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(picture.filename))
                #picture_path = secure_filename(picture.filename)
                picture.save(picture_path)
            else:
                picture_path = None
        else:
            picture_path = None

        # Insert data into the 'drivers' table
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO drivers (first_name, last_name, date_of_birth, address, phone_number, picture_path, class) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (first_name, last_name, date_of_birth, address, phone_number, picture_path, dclass))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('index'))

    return render_template('add_driver.html')

@app.route('/add_car/<int:driver_id>', methods=['GET', 'POST'])
def add_car(driver_id):
    if request.method == 'POST':
        # Get form data
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        inspection_passed = request.form['inspection_passed']
        inspection_date = request.form['inspection_date']
        # Add other form fields
        # Handle file upload (picture)
        if 'picture' in request.files:
            picture = request.files['picture']
            if picture.filename != '':
                picture_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(picture.filename))
                #picture_path = secure_filename(picture.filename)
                picture.save(picture_path)
            else:
                picture_path = None
        else:
            picture_path = None

        
        # Insert data into database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO cars (make, model, year, inspection_passed, inspection_date, picture_path, driver_id) VALUES (%s, %s, %s, %s, %s, %s)", (make, model, inspection_passed, inspection_date, picture_path, driver_id))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('driver_profile', driver_id=driver_id))

    return render_template('add_car.html', driver_id=driver_id)


@app.route('/delete_car/<int:car_id>/<int:driver_id>', methods=['POST', 'GET'])
def delete_car(car_id,driver_id):
    cur = mysql.connection.cursor()
    driverid = driver_id
    cur.execute("DELETE FROM cars WHERE id = %s", (car_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('driver_profile',driver_id=driver_id))
    #return redirect(url_for('index'))

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']

        # Insert data into the 'events' table
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO events (event_name, event_date) VALUES (%s, %s)",
                    (event_name, event_date))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('index'))  # Redirect to the homepage or any other page

    return render_template('create_event.html')




@app.route('/events')
def events():
    today = datetime.now().date()
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM events WHERE event_date = %s", (today,))
    events = cur.fetchall()
    cur.close()
    return render_template('events.html', events=events)



@app.route('/event_check_ins', methods=['GET', 'POST'])
def event_check_ins():
    # Fetch all events for the dropdown
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, event_name FROM events")
    events = cur.fetchall()
    cur.close()

    selected_event_id = None

    if request.method == 'POST':
        selected_event_id = int(request.form.get('event_id'))

    # Fetch check-ins for the selected event
    if selected_event_id:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT drivers.id, drivers.first_name, drivers.last_name, check_ins.check_in_time, cars.inspection_passed
            FROM drivers
            LEFT JOIN check_ins ON drivers.id = check_ins.driver_id
            LEFT JOIN cars ON drivers.id = cars.driver_id
            WHERE check_ins.event_id = %s
            ORDER BY check_ins.check_in_time ASC
        """, (selected_event_id,))
        check_ins = cur.fetchall()
        cur.close()

        return render_template('event_check_ins.html', check_ins=check_ins, events=events, selected_event_id=selected_event_id)

    return render_template('event_check_ins.html', events=events, selected_event_id=selected_event_id)





if __name__ == '__main__':
    app.run(debug=True)
