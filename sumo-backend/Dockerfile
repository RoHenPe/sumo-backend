# 1. Usar a imagem "main" que você acabou de baixar
FROM ghcr.io/eclipse-sumo/sumo:main

# 2. Definir o diretório de trabalho
WORKDIR /app

# 3. Instalar as bibliotecas Python
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar seu código da API
COPY . .

# 5. Expor a porta interna da API
EXPOSE 8000

# 6. Comando para iniciar a API Python
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]