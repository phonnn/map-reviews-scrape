# Use Python 3.12 as the base image
FROM python:3.12

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       libc-dev \
       libffi-dev \
       libssl-dev \
       python3-dev \
       python3-setuptools \
       python3-pip \
       curl \
       wget \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy the rest of the application code
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask default port
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
