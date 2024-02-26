# app.pyd

from flask import *
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
from MySQLdb.cursors import DictCursor
import qrcode 
from minio import Minio
from datetime import datetime
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
# Configure MySQL
app.config['MYSQL_HOST'] = 'racedb-db.root-dynamics.com'
app.config['MYSQL_USER'] = 'raceapp'
app.config['MYSQL_PASSWORD'] = 'racecar123!@#'
app.config['MYSQL_DB'] = 'race_car_db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
ACCESS_KEY = "mY9xQ0dLHLOC2qRxWjGU"
SECRET_KEY = "GSypLUEoucbfk1rVm7EmKSu5ApdEwkqiFHq8VzV4"
BUCKET_NAME = "oswimages"
MINIO_API_HOST = "https://s3-api.root-dynamics.com"



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


def get_car_data_by_driver(driver_id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM cars WHERE driver_id = %s", (driver_id,))
    cars = cur.fetchall()
    cur.close()
    return cars

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    # Fetch and display list of drivers
    cur = mysql.connection.cursor()
    print(cur)
    cur.execute("SELECT * FROM drivers")
    drivers = cur.fetchall()
    cur.close()
    return render_template('index.html', drivers=drivers)

@app.route('/driver_qr/<int:driver_id>')
def driver_qr_code(driver_id):
    # Assuming you have a function to get the driver's data
    driver_data = get_driver_data(driver_id)

    # Generate QR code
    qr_data = f"Driver-ID: {driver_data['id']}"
    filename = f"static/qrcodes/driver_{driver_id}.png"
    generate_qr_code(qr_data, filename)

    return send_file(filename, mimetype='image/png')

@app.route('/car_qr/<int:car_id>')
def car_qr_code(car_id):
    # Assuming you have a function to get the driver's data
    car_data = get_car_data(car_id)

    # Generate QR code
    qr_data = f"Driver: {car_data['driver_id']}, Make: {car_data['make']}, Model: {car_data['model']}, Car-ID: {car_data['id']}"
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

@app.route('/final_check_in', methods=['POST'])
def final_check_in():
    driver_id = request.form.get('driver_id')
    car_id = request.form.get('car_id')
    event_id = request.form.get('event_id')

    if driver_id and car_id and event_id:
         # Check if the car has already checked in for today
         cur = mysql.connection.cursor()
         cur.execute("SELECT checked_in FROM check_ins WHERE driver_id = %s AND event_id = %s ORDER BY check_in_time DESC LIMIT 1", (driver_id, event_id,))
         last_check_in = cur.fetchone()

         # Check if the driver exists
         cur.execute("SELECT id FROM drivers WHERE id = %s", (driver_id,))
         existing_driver = cur.fetchone()

         if not existing_driver:
             flash("Driver does not exist.", 'error')

         if last_check_in and last_check_in['checked_in']:
             flash("Car already checked in for today.", 'error')
         
         else:
           cur.execute("INSERT INTO check_ins (driver_id, car_id, event_id, checked_in) VALUES (%s, %s, %s, TRUE)", (driver_id, car_id, event_id,))
           mysql.connection.commit()
           cur.close()
           flash("Driver Check-in Successful.", 'success')



           flash('Check-in successful!', 'success')
    else:
        flash('Check-in failed. Please ensure all fields are filled.', 'danger')

    return redirect(url_for('check_in'))

@app.route('/check_in', methods=['GET', 'POST'])
def check_in():
    messages = []
    cars, events, driver_id, driver = [], get_events_for_today(), None, None
    if request.method == 'POST' and 'driver_id' in request.form:
        driver_id = request.form['driver_id']
        cars = get_car_data_by_driver(driver_id)
        driver = get_driver_data(driver_id)
        if driver:
            if not cars:
                flash('No cars found for this driver.', 'danger')
        elif not driver:
            flash('No driver found. Please try again.', 'danger')
        elif driver and cars:
            pass
        else:
            flash('Something went wrong. Please try again', 'danger')
        
            

    return render_template('check_in.html', cars=cars, events=events, driver_id=driver_id, messages=messages, driver=driver)


# @app.route('/check_in', methods=['GET', 'POST'])
# def check_in():
#     messages = []
#     if request.method == 'POST':
#         driver_id = request.form.get('driver_id')
#         event_id = request.form.get('event_id')

#         if driver_id and event_id:
#             # Fetch the cars associated with the driver_id
#             cur = mysql.connection.cursor()
#             cur.execute("SELECT * FROM cars WHERE driver_id = %s", (driver_id,))
#             cars = cur.fetchall()
            
#             cur.execute("SELECT id FROM drivers WHERE id = %s", (driver_id,))
#             existing_driver = cur.fetchone()
#             cur.close()
#             if not existing_driver:
#                 messages.append("Driver does not exist.")
#                 driver_id = None
#             # Fetch today's events
#             events = get_events_for_today()
#             session['driver_id'] = driver_id

#             return render_template('check_in.html', cars=cars, events=events, driver_id=driver_id, event_id=event_id, messages=messages)

#     # Fetch today's events
#     events = get_events_for_today()
#     return render_template('check_in.html', events=events, messages=messages)

# # Add a new route to handle the final check-in after selecting a car
# @app.route('/final_check_in', methods=['POST'])
# def final_check_in():
#     messages = []
#     driver_id = request.form.get('driver_id')
#     car_id = request.form.get('car_id')
#     event_id = request.form.get('event_id')

#     if driver_id and car_id and event_id:
#         # Check if the car has already checked in for today
#         cur = mysql.connection.cursor()
#         cur.execute("SELECT checked_in FROM check_ins WHERE driver_id = %s AND event_id = %s ORDER BY check_in_time DESC LIMIT 1", (driver_id, event_id,))
#         last_check_in = cur.fetchone()

#         # Check if the driver exists
#         cur.execute("SELECT id FROM drivers WHERE id = %s", (driver_id,))
#         existing_driver = cur.fetchone()

#         if not existing_driver:
#             messages.append("Driver does not exist.")

#         if last_check_in and last_check_in['checked_in']:
#             messages.append("Car already checked in for today.")

#         cur.execute("INSERT INTO check_ins (driver_id, car_id, event_id, checked_in) VALUES (%s, %s, %s, TRUE)", (driver_id, car_id, event_id,))
#         mysql.connection.commit()
#         cur.close()
#         messages.append("Driver Check-in Successful.")

#     return redirect(url_for('check_in', messages=messages))


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
        bucket = 'drivers'
        # Get form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        address = request.form['address']
        phone_number = request.form['phone_number']
        dclass = request.form['dclass']

        if "picture" in request.files:
            file = request.files["picture"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
            if file.filename != "":
                picture = request.files['picture']
                if picture and allowed_file(file.filename):
                    filename = secure_filename(picture.filename)
                    size = os.fstat(picture.fileno()).st_size
                    picture_path = MINIO_API_HOST + '/drivers/' + filename
                    upload_object(filename, file, size, bucket)
                else:
                    flash('Invalid File Type','danger')
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
        bucket = 'cars'
        # Get form data
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        # Add other form fields
        # Handle file upload (picture)
        if "picture" in request.files:
            file = request.files["picture"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
            if file.filename != "":
                picture = request.files['picture']
                if picture and allowed_file(file.filename):
                    filename = secure_filename(picture.filename)
                    size = os.fstat(picture.fileno()).st_size
                    picture_path = MINIO_API_HOST + '/cars/' + filename
                    upload_object(filename, file, size, bucket)
                else:
                    flash('Invalid File Type','danger')
                    picture_path = None
            else:
                picture_path = None

        
        # Insert data into database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO cars (make, model, year, picture_path, driver_id) VALUES (%s, %s, %s, %s, %s)", (make, model, year, picture_path, driver_id))
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
    messages = []

    if request.method == 'POST':
        selected_event_id = int(request.form.get('event_id'))

    # Fetch check-ins for the selected event
    if selected_event_id:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT DISTINCT
                drivers.first_name,
                drivers.last_name,
                check_ins.check_in_time,
                car_inspections.inspection_status
            FROM check_ins
            JOIN drivers ON check_ins.driver_id = drivers.id
            LEFT JOIN car_inspections ON check_ins.car_id = car_inspections.car_id
            WHERE check_ins.event_id = %s
        """, (selected_event_id,))
        check_ins = cur.fetchall()
        cur.close()

        for check_in in check_ins:
            hello = "hello"
        return render_template('event_check_ins.html', check_ins=check_ins, events=events, selected_event_id=selected_event_id)

    return render_template('event_check_ins.html', events=events, selected_event_id=selected_event_id)





@app.route('/car_inspection', methods=['GET', 'POST'])
def car_inspection():
    messages = []  # Create an empty list to store messages

    if request.method == 'POST':
        car_id = request.form.get('car_id')
        event_id = request.form.get('event_id')
        ins_fluid = request.form.get('ins_fluid')
        ins_helmet = request.form.get('ins_helmet')
        ins_fireext = request.form.get('ins_fireext')
        ins_cage = request.form.get('ins_cage')
        ins_bat = request.form.get('ins_bat')

        # Validate if the car exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT driver_id FROM cars WHERE id = %s", (car_id,))
        car_data = cur.fetchone()
        cur.close()

        if car_data:
            driver_id = car_data['driver_id']
            # Get driver_class from drivers table
            cur = mysql.connection.cursor()
            cur.execute("SELECT class FROM drivers WHERE id = %s", (driver_id,))
            driver_class = cur.fetchone()
            cur.close()

            # Check if the driver is checked in for the selected event
            cur = mysql.connection.cursor()
            cur.execute("SELECT checked_in FROM check_ins WHERE driver_id = %s AND event_id = %s", (driver_id, event_id,))
            check_in_data = cur.fetchone()
            cur.close()

            if check_in_data and check_in_data['checked_in']:
                # Driver is checked in, proceed with inspection

                # Check if the car has already passed inspection for the specified event
                cur = mysql.connection.cursor()
                cur.execute("SELECT inspection_status FROM car_inspections WHERE car_id = %s AND event_id = %s", (car_id, event_id,))
                inspection_data = cur.fetchone()
                cur.close()

                if not inspection_data:
                    # Check if all checkboxes are checked
                    if ins_fluid and ins_helmet and ins_fireext and ins_cage and ins_bat:
                        # Car has not been inspected for this event and all checkboxes are checked, proceed with inspection
                        cur = mysql.connection.cursor()
                        cur.execute("INSERT INTO car_inspections (car_id, event_id, driver_id, driver_class, inspection_status, inspection_datetime) VALUES (%s, %s, %s, %s, 'Passed', NOW())",
                                    (car_id, event_id, driver_id, driver_class['class']))
                        mysql.connection.commit()
                        cur.close()

                        messages.append("Car inspection passed successfully.")
                    else:
                        messages.append("All checkboxes must be checked to pass inspection.")
                else:
                    messages.append("Car has already passed inspection for this event.")
            else:
                messages.append("Driver is not checked in for the selected event.")
        else:
            messages.append("Car not found.")

    # Fetch today's events
    events = get_events_for_today()

    return render_template('car_inspection.html', events=events, messages=messages)

















def upload_object(filename, data, length, bucket):
    client = Minio('s3-api.root-dynamics.com', ACCESS_KEY, SECRET_KEY)

    # Make bucket if not exist.
    found = client.bucket_exists(bucket)
    if not found:
        client.make_bucket(bucket)
    else:
        print(f"Bucket {bucket} already exists")

    client.put_object(bucket, filename, data, length)
    print(f"{filename} is successfully uploaded to bucket {bucket}.")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/minio", methods=["GET", "POST"])
def upload_s3file():
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            size = os.fstat(file.fileno()).st_size
            upload_object(filename, file, size)
            return redirect(request.url)

    return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>UPLOAD</title>
        </head>
        <body>
          <h1>Upload File</h1>
          <form method=post enctype=multipart/form-data>
            <input type=file name=file>
            <input type=submit value=Upload>
          </form>
        </body>
        </html>
        """





    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
    
    #app.run(debug=True)