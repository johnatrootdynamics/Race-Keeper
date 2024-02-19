# Use an appropriate base image
FROM python:3.11-slim-bullseye
EXPOSE 80
# Install Git
RUN apt update  -y
RUN apt install -y git 
RUN apt install -y python3-full
RUN apt install -y python3-pip
#RUN python -m pip install --upgrade pip
# Clone the repository
RUN git clone https://github.com/johnatrootdynamics/Race-Keeper /app

# Copy files from the cloned repository to the desired location in the Docker image


# Set the working directory
WORKDIR /app
#RUN pip3 install -r requirements.txt --break-system-packages
RUN pip3 install pypng==0.20220715.0 --break-system-packages
RUN pip3 install blinker==1.7.0 --break-system-packages
RUN pip3 install certifi==2024.2.2 --break-system-packages
RUN pip3 install charset-normalizer==3.3.2 --break-system-packages
RUN pip3 install click==8.1.7 --break-system-packages
RUN pip3 install Flask==3.0.0 --break-system-packages
RUN pip3 install Flask-MySQLdb==2.0.0 --break-system-packages
RUN pip3 install idna==3.6 --break-system-packages
RUN pip3 install itsdangerous==2.1.2 --break-system-packages
RUN pip3 install Jinja2==3.1.3 --break-system-packages
RUN pip3 install mysql-connector-python==8.3.0 --break-system-packages
RUN pip3 install mysqlclient==2.2.1 --break-system-packages
RUN pip3 install pypng==0.20220715.0 --break-system-packages
RUN pip3 install qrcode==7.4.2 --break-system-packages
RUN pip3 install requests==2.30.0 --break-system-packages
RUN pip3 install setuptools==65.5.0 --break-system-packages
RUN pip3 install typing_extensions==4.9.0 --break-system-packages
RUN pip3 install urllib3==2.2.1 --break-system-packages
RUN pip3 install Werkzeug==3.0.1 --break-system-packages
#RUN python -m pip install werkzeug


# Specify the default command to run when the container starts
CMD [ "python3", "app.py" ]