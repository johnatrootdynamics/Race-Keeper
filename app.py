# app.pyd

from flask import *
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from MySQLdb.cursors import DictCursor
import qrcode 
from minio import Minio
from datetime import datetime
from functools import wraps
import requests
from requests.auth import HTTPBasicAuth
import logging
import json

app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True
)
app.config['PREFERRED_URL_SCHEME'] = 'https'
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


app.config['BOLD_API_BASE']    = "https://api.boldsign.com/v1"
app.config['BOLD_API_KEY']     = "MzdkZDFmN2YtOWQwZS00YjM4LWIyYTUtMmFkNDdiMjMxZGMw"
app.config['BOLD_TEMPLATE_ID'] = "e5c8f024-64df-4bdc-9142-3a04c01a154a"





mysql = MySQL(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

roles = ["user","admin"]


@app.template_global()
def get_all_drivers():
    cur = mysql.connection.cursor(DictCursor)
    cur.execute("SELECT id, first_name, last_name FROM drivers")
    ds = cur.fetchall()
    cur.close()
    return ds

#To pull profile picture for navbar
@app.context_processor
def inject_profile_pic():
    fallback = url_for("static", filename="img/default_profile.png")
    if current_user.is_authenticated:
        cur = mysql.connection.cursor()
        cur.execute("SELECT picture_path FROM drivers WHERE id = %s", (current_user.id,))
        row = cur.fetchone()
        cur.close()
        if row and row["picture_path"]:
            return dict(profile_pic_url=row["picture_path"])
    return dict(profile_pic_url=fallback)
    
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not (current_user.is_authenticated and current_user.role in roles):
                abort(403)          # Forbidden
            return view(*args, **kwargs)
        return wrapped
    return decorator

@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM drivers WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(id=user['id'], username=user['username'], role=user['role'])
    return None

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # only admins get to pick role; everyone else is treated as anonymous self-register
    show_role_selection = current_user.is_authenticated and current_user.role == 'admin'
    if current_user.is_authenticated and current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        # basic fields…
        first_name    = request.form['first_name']
        last_name     = request.form['last_name']
        date_of_birth = request.form['date_of_birth']
        address       = request.form['address']
        city          = request.form['city']
        state         = request.form['state']
        zipcode       = request.form['zip']
        phone_number  = request.form['phone_number']
        dclass        = request.form['dclass']
        username      = request.form['username']
        email         = request.form['email']          # ← NEW
        password      = request.form['password']
        hashed_pwd    = generate_password_hash(password, method='scrypt')

        # pick role: admin-chosen or default to 'user'
        if show_role_selection:
            role = request.form.get('role', 'user')
            if role not in roles:
                role = 'user'
        else:
            role = 'user'

        # handle optional picture upload…
        picture_path = None
        if 'picture' in request.files:
            pic = request.files['picture']
            if pic and pic.filename and allowed_file(pic.filename):
                filename = secure_filename(pic.filename)
                size = os.fstat(pic.fileno()).st_size
                picture_path = f"{MINIO_API_HOST}/drivers/{filename}"
                upload_object(filename, pic, size, 'drivers')

        # insert—including the new role and email columns!
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO drivers
              (first_name, last_name, city, state, zip,
               date_of_birth, address, phone_number, picture_path,
               class, username, email, password, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            first_name, last_name, city, state, zipcode,
            date_of_birth, address, phone_number, picture_path,
            dclass, username, email, hashed_pwd, role      # ← email inserted here
        ))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('login'))

    # GET -> show form
    return render_template(
        'register.html',
        show_role_selection=show_role_selection
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor(DictCursor)
        cursor.execute('SELECT * FROM drivers WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            user_obj = User(id=user['id'], username=user['username'], role=user['role'])
            login_user(user_obj)

            # Explicit role routing
            if user_obj.role == 'admin':
                return redirect(url_for('index'))
            elif user_obj.role == 'user':
                return redirect(url_for('driver_profile', driver_id=user_obj.id))
            else:
                # Unknown role—log out and forbid
                logout_user()
                abort(403)

        flash('Invalid username or password', 'danger')

    return render_template('login.html')


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
@login_required
def index():
    # Regular users go straight to their own profile
    if current_user.role == 'user':
        return redirect(url_for('driver_profile', driver_id=current_user.id))

    # Admins see the full driver dashboard
    if current_user.role == 'admin':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM drivers")
        drivers = cur.fetchall()
        cur.close()
        return render_template('index.html', drivers=drivers)

    # Any other role is forbidden
    abort(403)

@app.route('/driver_qr/<int:driver_id>')
def driver_qr_code(driver_id):
    show_role_selection = current_user.is_authenticated and current_user.role == 'admin'
    # Assuming you have a function to get the driver's data
    driver_data = get_driver_data(driver_id)

    # Generate QR code
    qr_data = f"Driver-ID: {driver_data['id']}"
    filename = f"static/qrcodes/driver_{driver_id}.png"
    generate_qr_code(qr_data, filename)

    return send_file(filename, mimetype='image/png')

@app.route('/car_qr/<int:car_id>')
def car_qr_code(car_id):
    if current_user.id != current_user.id and current_user.role != 'admin':
        abort(403)  
    # Assuming you have a function to get the driver's data
    car_data = get_car_data(car_id)

    # Generate QR code
    qr_data = f"Driver: {car_data['driver_id']}, Make: {car_data['make']}, Model: {car_data['model']}, Car-ID: {car_data['id']}"
    filename = f"static/qrcodes/car_{car_id}.png"
    generate_qr_code(qr_data, filename)

    return send_file(filename, mimetype='image/png')

@app.route('/driver/<int:driver_id>', methods=['GET', 'POST'])
@login_required
def driver_profile(driver_id):
    # only the driver themself or an admin can view
    if not (current_user.id == driver_id or current_user.role == 'admin'):
        abort(403)
        
        # If they’ve just come back from BoldSign:
    status = request.args.get('status')
    if status and status.lower() in ('signed', 'completed'):
        flash('✅ Waiver signed successfully!', 'success')
    # handle new note submission
    if request.method == 'POST':
        note_text = request.form.get('note_text')
        if note_text:
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO notes (driver_id, note_text) VALUES (%s, %s)",
                (driver_id, note_text)
            )
            mysql.connection.commit()
            cur.close()

    cur = mysql.connection.cursor(DictCursor)

    # 1) driver & cars
    cur.execute("SELECT * FROM drivers WHERE id = %s", (driver_id,))
    driver = cur.fetchone()
    cur.execute("SELECT * FROM cars WHERE driver_id = %s", (driver_id,))
    cars = cur.fetchall()

    # 2) today’s events + check-in + waiver status + event time
    today = datetime.now().date()
    cur.execute("""
        SELECT
          e.id                           AS event_id,
          e.event_name                   AS event_name,
          e.event_date                   AS event_datetime,
          COALESCE(ci.checked_in, FALSE) AS checked_in,
          COALESCE(w.signed,    FALSE)   AS waiver_signed
        FROM events e
        LEFT JOIN check_ins ci
          ON ci.event_id = e.id
         AND ci.driver_id = %s
        LEFT JOIN waivers w
          ON w.event_id  = e.id
         AND w.driver_id = %s
        WHERE DATE(e.event_date) = %s
        ORDER BY e.event_date
    """, (driver_id, driver_id, today))
    today_checkins = cur.fetchall()

    # 3) notes
    cur.execute("""
        SELECT * FROM notes
         WHERE driver_id = %s
         ORDER BY created_at DESC
    """, (driver_id,))
    notes = cur.fetchall()

    cur.close()



    return render_template(
        'driver_profile.html',
        driver=driver,
        cars=cars,
        notes=notes,
        today_checkins=today_checkins
    )




@app.route('/delete_driver/<int:driver_id>', methods=['POST'])
@login_required
def delete_driver(driver_id):
    if current_user.id != current_user.id and current_user.role != 'admin':
        abort(403)
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


@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
@role_required("admin")
def delete_event(event_id):
    if current_user.id != current_user.id and current_user.role != 'admin':
        abort(403)
    # Check if the driver exists
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM events WHERE id = %s", (event_id,))
    existing_event = cur.fetchone()

    if existing_event:
        # Delete check-in data associated with the driver
        cur.execute("DELETE FROM check_ins WHERE event_id = %s", (event_id,))
        cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('events'))
    else:
        return "Event not found"





@app.route('/car/<int:car_id>')
@login_required
def car_info(car_id):
    if current_user.id != current_user.id and current_user.role != 'admin':
        abort(403)
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


@app.route('/driver/<int:driver_id>/upload_picture', methods=['POST'])
@login_required
def upload_driver_picture(driver_id):
    # only the driver themself or an admin can change this picture
    if not (current_user.id == driver_id or current_user.role == 'admin'):
        abort(403)

    # make sure a file was sent
    if 'picture' not in request.files:
        flash('No file part in request', 'danger')
        return redirect(url_for('driver_profile', driver_id=driver_id))

    file = request.files['picture']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('driver_profile', driver_id=driver_id))

    if not allowed_file(file.filename):
        flash('Invalid file type', 'danger')
        return redirect(url_for('driver_profile', driver_id=driver_id))

    # save locally (optional) or push to Minio, just like in register()
    filename = secure_filename(file.filename)
    size = os.fstat(file.fileno()).st_size
    bucket = 'drivers'
    picture_path = f"{MINIO_API_HOST}/{bucket}/{filename}"
    upload_object(filename, file, size, bucket)

    # persist the new URL in the database
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE drivers SET picture_path = %s WHERE id = %s",
        (picture_path, driver_id)
    )
    mysql.connection.commit()
    cur.close()

    flash('Profile picture updated!', 'success')
    return redirect(url_for('driver_profile', driver_id=driver_id))



@app.route('/add_car/<int:driver_id>', methods=['GET', 'POST'])
@login_required
def add_car(driver_id):
    if current_user.id != current_user.id:
        abort(403)
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
@login_required
def delete_car(car_id,driver_id):
    if current_user.id != current_user.id and current_user.role != 'admin':
        abort(403)
    cur = mysql.connection.cursor()
    driverid = driver_id
    cur.execute("DELETE FROM cars WHERE id = %s", (car_id,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('driver_profile',driver_id=driver_id))
    #return redirect(url_for('index'))

@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if current_user.role != 'admin':
        abort(403)
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
@login_required
def events():
    if current_user.role != 'admin':
        abort(403)
    today = datetime.now().date()
    cur = mysql.connection.cursor()
    #cur.execute("SELECT * FROM events WHERE event_date = %s", (today,))
    cur.execute("SELECT * FROM events")
    events = cur.fetchall()
    cur.close()
    return render_template('events.html', events=events)



@app.route('/event_check_ins', methods=['GET', 'POST'])
@login_required
def event_check_ins():
    passed_event_id = request.args.get('event_id', None)


    
    if current_user.role != 'admin':
        abort(403)
    # Fetch all events for the dropdown
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, event_name FROM events")
    events = cur.fetchall()
    cur.close()

    selected_event_id = None
    messages = []
    if passed_event_id:
        event_id = passed_event_id
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
        """, (passed_event_id,))
        check_ins = cur.fetchall()
        cur.close()

        for check_in in check_ins:
            hello = "hello"
        return render_template('event_check_ins.html', check_ins=check_ins, events=events, passed_event_id=passed_event_id)
    

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
@login_required
def car_inspection():
    if current_user.role != 'admin':
        abort(403)
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
                messages.append("Driver is not checked in for the selected event. Please put a link here to check in")
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



@app.route('/register_run', methods=['GET', 'POST'])
def register_run():
    if current_user.role != 'admin':
        abort(403)
    cursor = mysql.connection.cursor()
    today = datetime.now().date()
    if request.method == 'POST':
        event_id = session.get('event_id', request.form['event_id'])
        car_id = request.form['car_id']

        # Check if the car passed inspection for the event
        cursor.execute('SELECT * FROM car_inspections WHERE car_id = %s AND event_id = %s AND inspection_status = "Passed"', (car_id, event_id))
        passed_inspection = cursor.fetchone()
        
        if passed_inspection:
            current_time = datetime.now()
            f_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
            # Insert car run
            cursor.execute('INSERT INTO car_runs (car_id, event_id, start_time) VALUES (%s, %s, %s)', (car_id, event_id, f_time))
            mysql.connection.commit()
            flash('Recorded.', 'success')
        else:
            flash('Car has not passed inspection for this event.', 'danger')
        return redirect(url_for('register_run'))
    
    # Fetch events for today to populate the dropdown
    cursor.execute('SELECT id, event_name FROM events WHERE DATE(event_date) = %s',(today,))
    events = cursor.fetchall()
    cursor.close()
    return render_template('laps.html', events=events)



@app.route('/event_info/<int:event_id>')
@login_required
def event_info(event_id):
    if current_user.role != 'admin':
        abort(403)

    cur = mysql.connection.cursor(DictCursor)

    # ➊ Fetch event metadata
    cur.execute(
        "SELECT event_name, event_date "
        "FROM events WHERE id = %s",
        (event_id,)
    )
    event = cur.fetchone()
    if not event:
        abort(404)

    # ➋ Count distinct checked‑in drivers
    cur.execute(
        "SELECT COUNT(DISTINCT driver_id) AS checked_in_count "
        "FROM check_ins "
        "WHERE event_id = %s AND checked_in = TRUE",
        (event_id,)
    )
    checked = cur.fetchone()
    checked_in_count = checked['checked_in_count'] or 0

    # ➌ Breakdown by class (checked‑in only)
    cur.execute("""
        SELECT d.class     AS class,
               COUNT(DISTINCT cr.driver_id) AS count
        FROM check_ins AS cr
        JOIN drivers   AS d  ON cr.driver_id = d.id
        WHERE cr.event_id = %s
          AND cr.checked_in = TRUE
        GROUP BY d.class
        ORDER BY d.class
    """, (event_id,))
    class_counts = cur.fetchall()

    # ➍ Calculate average runs by class
    cur.execute("""
        SELECT d.class            AS class,
               ROUND(AVG(runs.run_count), 2) AS avg_runs
        FROM (
            SELECT car_id, COUNT(*) AS run_count
            FROM car_runs
            WHERE event_id = %s
            GROUP BY car_id
        ) AS runs
        JOIN drivers AS d ON runs.car_id = d.id
        GROUP BY d.class
        ORDER BY d.class
    """, (event_id,))
    avg_runs_by_class = cur.fetchall()

    cur.close()

    return render_template(
        'event_info.html',
        event=event,
        checked_in_count=checked_in_count,
        class_counts=class_counts,
        avg_runs_by_class=avg_runs_by_class
    )





def create_boldsign_request(driver_id, event_id):
    driver      = get_driver_data(driver_id)
    driver_email = driver.get('email') or f"{driver['username']}@example.com"
    payload = {
        "roles": [{
            "roleIndex":   1,                     # 1-based index in your template
            "roleName":    "Racer",               # must match your template
            "signerName":  f"{driver['first_name']} {driver['last_name']}",
            "signerEmail": driver_email
        }],
        "disableEmailNotifications": True,
        # after signing, BoldSign will redirect this iframe back here:
        "redirectUrl": url_for('finish_waiver', driver_id=driver_id, event_id=event_id, _external=True)
    }

    url = f"{app.config['BOLD_API_BASE']}/template/send?templateId={app.config['BOLD_TEMPLATE_ID']}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key":    app.config['BOLD_API_KEY'],
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    req_id = data.get("requestId") or data.get("request_id")
    if not req_id:
        app.logger.error("BoldSign response missing requestId: %s", data)
        raise RuntimeError("BoldSign response missing requestId")
    return req_id

def get_boldsign_embedded_url(request_id):
    url = f"{app.config['BOLD_API_BASE']}/signing-request/{request_id}/embedded-url"
    headers = {"x-api-key": app.config['BOLD_API_KEY']}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data.get("embeddedUrl") or data.get("embedded_url")


@app.route('/driver/<int:driver_id>/waiver/<int:event_id>')
@login_required
def start_waiver(driver_id, event_id):
    if not (current_user.id == driver_id or current_user.role == 'admin'):
        abort(403)

    # 1) create the requestId
    try:
        req_id = create_boldsign_request(driver_id, event_id)
    except Exception:
        flash("Unable to start e-waiver. Please try again later.", "danger")
        return redirect(url_for('driver_profile', driver_id=driver_id))

    # 2) save it to your waivers table
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO waivers (driver_id, event_id, request_id, created_at)
        VALUES (%s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
          request_id = VALUES(request_id),
          signed     = FALSE
    """, (driver_id, event_id, req_id))
    mysql.connection.commit()
    cur.close()

    # 3) fetch the embedded signing URL and render it in an iframe
    try:
        embed_url = get_boldsign_embedded_url(req_id)
    except Exception:
        flash("Couldn’t load signing window. Please try again.", "danger")
        return redirect(url_for('driver_profile', driver_id=driver_id))

    return render_template('waiver_iframe.html', embed_url=embed_url)

@app.route('/driver/<int:driver_id>/waiver/finish/<int:event_id>')
@login_required
def finish_waiver(driver_id, event_id):
    # once BoldSign has redirected here, just bounce back to profile
    flash("Thank you — your waiver is complete!", "success")
    return redirect(url_for('driver_profile', driver_id=driver_id))


@app.route('/final_check_in', methods=['POST'])
@login_required
@role_required('admin')
def final_check_in():
    driver_id = request.form.get('driver_id')
    event_id  = request.form.get('event_id')
    car_id    = request.form.get('car_id')

    # ——— 1) Ensure all fields are present ———
    if not (driver_id and event_id and car_id):
        flash('Please select a driver, an event, and a car before checking in.', 'danger')
        return redirect(url_for('check_in'))

    cur = mysql.connection.cursor(DictCursor)

    # ——— 2) Car must belong to the driver ———
    cur.execute(
        "SELECT 1 FROM cars WHERE id = %s AND driver_id = %s",
        (car_id, driver_id)
    )
    if not cur.fetchone():
        flash('Invalid car selection.', 'danger')
        cur.close()
        return redirect(url_for('check_in'))

    # ——— 3) Waiver must be signed ———
    cur.execute("""
        SELECT signed
          FROM waivers
         WHERE driver_id = %s
           AND event_id  = %s
    """, (driver_id, event_id))
    waiver = cur.fetchone()
    if not waiver:
        flash('Cannot check in: waiver not started.', 'danger')
        cur.close()
        return redirect(url_for('check_in'))
    if not waiver['signed']:
        flash('Cannot check in: waiver not yet signed.', 'danger')
        cur.close()
        return redirect(url_for('check_in'))

    # ——— 4) Prevent duplicate check-ins ———
    cur.execute("""
        SELECT checked_in
          FROM check_ins
         WHERE driver_id = %s
           AND event_id  = %s
         ORDER BY check_in_time DESC
         LIMIT 1
    """, (driver_id, event_id))
    last = cur.fetchone()
    if last and last['checked_in']:
        flash('Driver already checked in.', 'warning')
        cur.close()
        return redirect(url_for('check_in'))

    # ——— 5) All good: insert the check-in ———
    cur.execute("""
        INSERT INTO check_ins
            (driver_id, car_id, event_id, checked_in)
        VALUES (%s, %s, %s, TRUE)
    """, (driver_id, car_id, event_id))
    mysql.connection.commit()
    cur.close()

    flash('Driver checked in successfully!', 'success')
    return redirect(url_for('check_in'))


@app.route('/check_in', methods=['GET', 'POST'])
@login_required
@role_required("admin")
def check_in():
    # 1) fetch today’s events
    events = get_events_for_today()
    selected_event_id = None
    driver_id = None
    driver = None
    cars = []

    if request.method == 'POST':
        # 2) read event + driver from the same form
        selected_event_id = request.form.get('event_id')
        driver_id = request.form.get('driver_id')

        if not selected_event_id:
            flash("Please select an event to check in.", "danger")
        elif not driver_id:
            flash("Please enter a Driver ID.", "danger")
        else:
            driver = get_driver_data(driver_id)
            if not driver:
                flash("Driver not found.", "danger")
                driver = None
            else:
                cars = get_car_data_by_driver(driver_id)
                if not cars:
                    flash("No cars found for this driver.", "danger")

    return render_template(
        'check_in.html',
        events=events,
        selected_event_id=selected_event_id,
        driver_id=driver_id,
        driver=driver,
        cars=cars
    )


    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
    
    #app.run(debug=True)
