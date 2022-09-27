# syntax=docker/dockerfile:1

FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the code into a folder named app
ADD . /app

# switch the working directory to app
WORKDIR /app

# Install App dependencies
RUN pip3 install -r requirements.txt

CMD ["python", "-u", "app.py"]