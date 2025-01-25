# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install Memcached and its dependencies
RUN apt-get update && apt-get install -y \
    memcached \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application code into the container
COPY . .

# Expose the port that FastAPI will run on
EXPOSE 8000

# Start both Memcached and FastAPI application
CMD ["sh", "-c", "memcached -u memcache -m 64 -p 11211 -l 0.0.0.0 & uvicorn main:app --host 0.0.0.0 --port 8000"]
