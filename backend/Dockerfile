FROM python:3.11-slim

WORKDIR /app

# System deps (pypdf, numpy sometimes need these)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# FastAPI needs PORT + host=0.0.0.0 in container
ENV PORT=8000
ENV OPENAI_API_KEY=changeme-in-deploy

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
