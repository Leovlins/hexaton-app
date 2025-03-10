# Use uma imagem oficial do Python como base
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos
COPY . .

# Expõe a porta em que a aplicação vai rodar
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
