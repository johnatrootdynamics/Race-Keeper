from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL

app = Flask(__name__)

# Configure MySQL
app.config['localhost'] = 'your_mysql_host'
app.config['raceapp'] = 'your_mysql_user'
app.config['password123'] = 'your_mysql_password'
app.config['driver_info'] = 'your_mysql_database'

mysql = MySQL(app)

@app.route('/', methods=['GET', 'POST'])
def index():
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

    return render_template('index.html')

@app.route('/cars', methods=['GET'])
def cars():
    # Retrieve data from MySQL database
    cur = mysql.connection.cursor()
    cur.execute("SELECT car, name FROM driver_info")
    data = cur.fetchall()
    cur.close()

    return render_template('cars.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)