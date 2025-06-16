FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN pip install --upgrade pip
RUN pip install uv

# Copy all source code
COPY . .

# Install dependencies using uv
RUN uv pip install --system -e .

# Use uvicorn to run the FastAPI app
CMD ["uvicorn", "src.instaserver:app", "--host", "0.0.0.0", "--port", "8000"]
