FROM python:3.11-slim

WORKDIR /app

# build-essential is required to compile cmdstan (Prophet's Stan backend).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install a working cmdstan and disable Prophet's broken bundled one, so
# /zip/projection and the refresh_zip_forecasts task can train models.
RUN python scripts/setup_prophet.py

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
