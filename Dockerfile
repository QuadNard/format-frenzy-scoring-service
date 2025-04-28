# 1. Base image with Python
FROM python:3.12-slim
# 2. Set a working directory
WORKDIR /app
# 3. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 4. Copy the rest of the source code
COPY . .
# 5. Expose the port (Heroku will inject $PORT)
EXPOSE 8000  
# 6. Start Uvicorn, use $PORT from env (important!)
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
