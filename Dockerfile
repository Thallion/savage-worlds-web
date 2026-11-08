FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Nicht als root laufen. UID 1000 = Besitzer von ./data auf dem Pi (exnef),
# damit das gemountete Volume ohne Rechte-Klimmzüge beschreibbar bleibt.
RUN useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin chargen
USER chargen

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
