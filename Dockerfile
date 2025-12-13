
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies (if needed, e.g., for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --upgrade pip
COPY ./requirements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .


# Collect static files (optional, if using Whitenoise or static files)
RUN python manage.py collectstatic --no-input

# Expose port
EXPOSE 8000

# Run with gunicorn (recommended for production)
CMD ["gunicorn", "rsvp.wsgi:application", "--bind", "0.0.0.0:8000"]

