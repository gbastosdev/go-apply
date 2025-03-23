# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Copy the requirements file from the root folder to the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code from the root folder to the container
COPY . .

# Expose port 80 for the FastAPI app
EXPOSE 80

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]