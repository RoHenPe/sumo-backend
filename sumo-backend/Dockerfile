FROM ghcr.io/eclipse-sumo/sumo:main

WORKDIR /app

RUN apt-get update && apt-get install -y python3 python3-pip

RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "5000"]