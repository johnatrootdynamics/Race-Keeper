# Use an appropriate base image
FROM python:3.11.0a1-slim
EXPOSE 80
# Install Git
RUN apt update  -y
RUN apt install -y git 
RUN apt install -y python3
RUN apt-get install -y python3-pip

# Clone the repository
RUN git clone https://github.com/johnatrootdynamics/Race-Keeper /app

# Copy files from the cloned repository to the desired location in the Docker image


# Set the working directory
WORKDIR /app
RUN pip3 install -r requirements.txt
#RUN python -m pip install werkzeug


# Specify the default command to run when the container starts
CMD [ "python3", "app.py" ]