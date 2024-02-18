# Use an appropriate base image
FROM ubuntu:20.04

# Install Git
RUN apt update && \
    apt install -y git && \
    apt install -y mysql-server


# Clone the repository
RUN git clone https://github.com/johnatrootdynamics/Race-Keeper /app

# Copy files from the cloned repository to the desired location in the Docker image
COPY /app/yourfile.txt /destination/path/yourfile.txt


# Set the working directory
WORKDIR /app



# Specify the default command to run when the container starts
CMD ["python", "app.py"]