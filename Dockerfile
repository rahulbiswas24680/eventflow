FROM python:3.11.7-bookworm
WORKDIR /app
COPY requirements.in ./
RUN pip install -r requirements.in
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]