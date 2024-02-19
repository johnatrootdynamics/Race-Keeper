# Use an appropriate base image
FROM debian:12
EXPOSE 80
# Install Git
RUN apt update  -y
RUN apt install -y git 
RUN apt install -y python3-full
RUN apt install -y python3-pip
#RUN python -m pip install --upgrade pip
RUN python3 -m venv .venv
RUN source .venv/bin/activate
# Clone the repository
RUN git clone https://github.com/johnatrootdynamics/Race-Keeper /app

# Copy files from the cloned repository to the desired location in the Docker image


# Set the working directory
WORKDIR /app
RUN python3 -m pip install -r requirements.txt
#RUN python -m pip install werkzeug


# Specify the default command to run when the container starts
CMD [ "python3", "app.py" ]