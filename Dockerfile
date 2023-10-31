# Use the official Conda image as the base image
FROM continuumio/miniconda3

# Set the working directory in the container
WORKDIR /app

# Copy your application code into the container
COPY . .

# Install dependencies
RUN apt-get update && apt-get -y upgrade

RUN pip install -r requirements.txt && pip install gunicorn
COPY ./extra/json.py /opt/conda/lib/python3.11/site-packages/flask_mongoengine/json.py
COPY ./extra/flask_uploads.py /opt/conda/lib/python3.11/site-packages/flask_uploads.py

# Expose the port that your Flask app will run on
EXPOSE 8181

# Define the command to run your Flask app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8181", "app:app"]
