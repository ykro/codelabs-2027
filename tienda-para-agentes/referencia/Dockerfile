# Imagen de la referencia en línea. desplegar.sh arma la carpeta: solucion/ (o inicio/) + referencia/.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV APP_MODULE="servidor:app"
CMD ["sh", "-c", "uvicorn $APP_MODULE --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
