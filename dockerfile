FROM python:3.10.2
ENV PYTHONUNBUFFERED 1
COPY ./requirements.txt /requirements.txt
RUN pip install --upgrade pip
RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && apt-get -y install wkhtmltopdf
    
RUN pip install -r /requirements.txt
RUN mkdir /app
COPY . /app
WORKDIR /app
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
ENV QT_QPA_PLATFORM='offscreen'



