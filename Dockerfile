# ==========================================
# FormFix Production Runtime Container
# Pre-built Frontend + High-Performance FastAPI Backend
# ==========================================
FROM python:3.10-slim

WORKDIR /app

# Install system libraries needed by OpenCV and PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy pre-compiled production frontend (built with Vite)
COPY frontend/dist/ ./frontend/dist/

# Set working directory to backend
WORKDIR /app/backend

# Ensure ephemeral storage directory exists
RUN mkdir -p /app/backend/temp_uploads

# Default port (Render automatically provides $PORT)
ENV PORT=8000
EXPOSE 8000

# Start unified production server
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
