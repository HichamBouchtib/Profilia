# Use the official Playwright Python image which includes all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install system dependencies (PostgreSQL client for database connectivity)
RUN apt-get update --fix-missing && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Install Playwright browsers (they should already be installed in the base image, but this ensures they're up to date)
RUN playwright install --with-deps chromium

EXPOSE 5000

CMD ["python", "app.py"]
