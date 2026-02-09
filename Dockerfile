FROM python:3.11-slim

WORKDIR /app

# Copy project files needed for installation
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies and package
RUN pip install --no-cache-dir -e .

# Copy config (separate step for better caching)
COPY config/ ./config/

# Create logs directory
RUN mkdir -p logs

# Expose the default port (can be overridden via config)
EXPOSE 5001

# Run the application
CMD ["python", "-m", "race_ticker.app"]
