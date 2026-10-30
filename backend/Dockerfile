FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=7860

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces requires a user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Install lightweight CPU-only PyTorch first
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies
COPY --chown=user requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

# Pre-cache embedding and reranker models in image for instant startup
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Copy application and entrypoint script
COPY --chown=user app/ ./app/
COPY --chown=user start.sh .

# Ensure start.sh is executable and create uploads directory
RUN chmod +x start.sh && mkdir -p /home/user/app/uploads

# Expose default Hugging Face Spaces port
EXPOSE 7860

# Launch both Celery worker and FastAPI server
CMD ["bash", "start.sh"]
