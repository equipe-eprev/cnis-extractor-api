# Dockerfile para API de Extração de CNIS
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements_api.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements_api.txt

# Copia código da API
COPY api_cnis.py .

# Expõe porta
EXPOSE 8080

# Comando para rodar
CMD exec gunicorn --bind :8080 --workers 2 --threads 4 --timeout 120 api_cnis:app
