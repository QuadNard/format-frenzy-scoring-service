# 1. Base image with Python
FROM python:3.12-slim

# 2. Set a working directory
WORKDIR /app

# 3. Copy your requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy your source code
COPY . .

# 5. Expose the port the app runs on
EXPOSE 8000

# 6. Start Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
