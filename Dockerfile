# Use the official Python image
From python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy the Streamlit app into the container
COPY app.py

#Expose the port that Streamlit runs on
EXPOSE 8501

# Command to run the Steamlit app
CMD ["streamlit","run","app.py", "--server.port=8501","--server.host==0.0.0.0"]
