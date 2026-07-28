# Use a slim Python base image
FROM python:3.11-slim

# Avoid interactive prompts and set a working directory
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# System deps (if you know you need extras, add them here)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Copy the rest of the code
COPY . /app

# Environment variables (these will be set at runtime / in compose)
# Example: Discord & ADO tokens mentioned in README/setup
ENV DISCORD_BOT_TOKEN="" \
    DISCORD_GUILD_ID="" \
    AZURE_DEVOPS_PAT=""

# Default command – adjust if you want a different process
CMD ["python", "discord_bot.py"]
