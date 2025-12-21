# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# C64_HOST can be set at runtime to configure the Ultimate C64 device URL
# Example: docker run -e C64_HOST=http://192.168.1.64:6464 ...

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY mcp_ultimate_server.py .
COPY config.json .
COPY docker-entrypoint.sh .

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash mcp && \
    chown -R mcp:mcp /app
USER mcp

# Expose port 8000 for the web server
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default command (can be overridden)
# We don't set a default CMD argument here because the python script handles
# the default URL via environment variable or internal default.
# If users want to pass arguments, they can append them to `docker run`.
