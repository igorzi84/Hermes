FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Taskfile
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

# Install UV with verification
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    test -f /root/.local/bin/uv && \
    /root/.local/bin/uv --version

# Copy project files
COPY . .

# Install Python dependencies using UV with lock file
RUN /root/.local/bin/uv pip install --system .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"

# Default command
CMD ["task", "run"]
