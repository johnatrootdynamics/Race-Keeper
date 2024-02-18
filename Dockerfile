# Use an appropriate base image
FROM ubuntu:20.04

# Install Git
RUN apt update  -y 
RUN apt install -y git 
RUN apt install -y python
RUN apt-get install -y python-pip
RUN pip install -r requirements.txt

# Clone the repository
RUN git clone https://github.com/johnatrootdynamics/Race-Keeper /app

# Copy files from the cloned repository to the desired location in the Docker image


# Set the working directory
WORKDIR /app



# Specify the default command to run when the container starts
CMD ["python", "app.py"]
CMD ["ls"]