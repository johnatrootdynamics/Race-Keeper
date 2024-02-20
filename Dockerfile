# Use an appropriate base image
FROM python:3.11.3
EXPOSE 80
# Install Git
RUN apt update  -y
RUN apt install python3-venv -y
RUN apt install -y git
#RUN python -m pip install --upgrade pip
# Clone the repository

# Copy files from the cloned repository to the desired location in the Docker image
RUN mkdir /app
RUN git clone https://github.com/johnatrootdynamics/Race-Keeper /app
WORKDIR /app
COPY * /opt/venv/
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies:



# Set the working directory
#RUN pip3 install -r requirements.txt  
RUN pip3 install pypng==0.20220715.0   
RUN pip3 install Flask==2.0.2 
RUN pip3 install Flask-MySQLdb==2.0.0  
RUN pip3 install Jinja2==3.1.3  
RUN pip3 install mysql-connector-python==8.3.0  
RUN pip3 install mysqlclient==2.2.1  
RUN pip3 install pypng==0.20220715.0  
RUN pip3 install qrcode==7.4.2  
RUN pip3 install requests==2.30.0  
RUN pip3 install urllib3==2.2.1  
RUN pip3 install Werkzeug
RUN pip3 install pyopenssl
#RUN python -m pip install werkzeug



# Run the application:
CMD ["python3", "app.py"]