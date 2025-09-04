# Dockerfile para a aplicação Assistente
FROM python:3.11-slim

# Configurar diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar flower para monitoramento do Celery
RUN pip install --no-cache-dir flower

# Copiar código da aplicação
COPY . .

# Criar diretório de logs
RUN mkdir -p /app/logs

# Expor porta da API
EXPOSE 7000

# Comando padrão (sobrescrito pelo docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7000"]