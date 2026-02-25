FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any are needed (e.g. for building wheels)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for database
RUN mkdir -p /root/.local/share/food

# Expose the port the app runs on
EXPOSE 8787

ARG APP_VERSION=dev
ARG APP_COMMIT=unknown
ARG APP_ENV=dev
ENV APP_VERSION=${APP_VERSION}
ENV APP_COMMIT=${APP_COMMIT}
ENV APP_ENV=${APP_ENV}

# Command to run the application
CMD ["python", "-m", "cli.main", "ui", "--host", "0.0.0.0", "--port", "8787"]
