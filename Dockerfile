# Stage 1: Build Stage (install dependencies)
# Use a slim Python image for smaller final image size
FROM python:3.13-alpine AS builder
# python:3.13-slim-buster AS builder

# Set the working directory inside the container
WORKDIR /app

# Install uv (if you prefer uv over pip for dependency management)
# Replace with pip if you're using requirements.txt or just pip directly
RUN pip install uv --index-url https://pypi.tuna.tsinghua.edu.cn/simple/

# Copy only the dependency file first to leverage Docker cache
# If you're using pyproject.toml with uv:
COPY pyproject.toml uv.lock ./

# Install project dependencies
# Using uv:
RUN uv sync --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple/

# If you were using pip with requirements.txt:
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Production Stage (copy only necessary files for runtime)
FROM python:3.13-alpine

# Set the working directory
WORKDIR /app

# Copy the installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your application code
COPY . .

# Expose the port Gunicorn will listen on
EXPOSE 9999

# Set environment variables for Flask (optional, but good practice)
ENV FLASK_APP=app.py
ENV FLASK_ENV=production 
# Or 'development' if you want Flask's debugger (not recommended for prod)

# Define the command to run your application using Gunicorn
# 'app:app' refers to the 'app' variable in 'app.py'
CMD ["uv", "run", "gunicorn", "-b", "0.0.0.0:9999", "app:app"]



