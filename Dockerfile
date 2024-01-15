FROM python:3.10.7-slim

# Set the timezone to Chile
ENV TZ=America/Santiago
ENV PYTHONUNBUFFERED=1

# Update packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends

# Copy application code
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .

# Install Playwright dependencies (only Firefox)
RUN playwright install --with-deps firefox

# Set up container
EXPOSE 8000
CMD [ "python3", "-u", "main.py" ]
