from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'raceapp'
app.config['MYSQL_PASSWORD'] = 'password123'
app.config['MYSQL_DB'] = 'driver_info'

mysql = MySQL(app)

@app.route('/', methods=['GET', 'POST'])
def index():

    # Retrieve data from MySQL database
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, car, class FROM driver_info")
    data = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
    cur.close()

    return render_template('index.html', data=data)

@app.route('/cars', methods=['GET'])

def cars():
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        car = request.form['car']
        class_ = request.form['class']
        driver_number = request.form['driver_number']
        car_number = request.form['car_number']

        # Insert data into MySQL database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO driver_info (name, car, class, driver_number, car_number) VALUES (%s, %s, %s, %s, %s)",
                    (name, car, class_, driver_number, car_number))
        mysql.connection.commit()
        cur.close()

        # Redirect back to the home page
        return redirect(url_for('index'))

    return render_template('cars.html')

# New route for individual driver pages
@app.route('/driver/<string:driver_id>', methods=['GET'])
def driver(driver_id):
    # Retrieve data for the specified driver from MySQL database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM driver_info WHERE id = %s", (driver_id,))
    driver_data = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
    cur.close()

    return render_template('driver.html', driver_data=driver_data)

if __name__ == '__main__':
    app.run(debug=True)