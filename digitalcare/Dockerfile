FROM python:3.12.6-alpine

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apk update \
    && apk add --no-cache \
       gcc \
       musl-dev \
       postgresql-dev \
       python3-dev \
       libffi-dev \
       netcat-openbsd \
       zlib \
       zlib-dev \
       jpeg-dev \
       bash \
       curl

# Upgrade pip and install Python dependencies
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn whitenoise

# Copy entrypoint and set executable permissions
COPY ./entrypoint.sh /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh

# Copy the rest of the application code
COPY . /usr/src/app/

# Expose the port Render will bind
EXPOSE 8000

# Entrypoint script will handle migrations, collectstatic, and start Gunicorn
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
