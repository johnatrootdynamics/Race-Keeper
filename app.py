# app.py

from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'raceapp'
app.config['MYSQL_PASSWORD'] = 'password123'
app.config['MYSQL_DB'] = 'race_car_db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

mysql = MySQL(app)

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

@app.route('/driver/<int:driver_id>')
def driver_profile(driver_id):
    # Fetch and display driver details
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM drivers WHERE id = %s", (driver_id,))
    driver = cur.fetchone()
    cur.execute("SELECT * FROM cars WHERE driver_id = %s", (driver_id,))
    cars = cur.fetchall()
    cur.close()
    return render_template('driver_profile.html', driver=driver, cars=cars)


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

        # Handle file upload (picture)
        if 'picture' in request.files:
            picture = request.files['picture']
            if picture.filename != '':
                picture_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(picture.filename))
                picture.save(picture_path)
            else:
                picture_path = None
        else:
            picture_path = None

        # Insert data into the 'drivers' table
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO drivers (first_name, last_name, date_of_birth, address, phone_number, picture_path) VALUES (%s, %s, %s, %s, %s, %s)",
                    (first_name, last_name, date_of_birth, address, phone_number, picture_path))
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
        # Add other form fields

        # Insert data into database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO cars (make, model, driver_id) VALUES (%s, %s, %s)", (make, model, driver_id))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('driver_profile', driver_id=driver_id))

    return render_template('add_car.html', driver_id=driver_id)


if __name__ == '__main__':
    app.run(debug=True)
