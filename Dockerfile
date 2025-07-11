# Stage 1: Build the Next.js application
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production image with Node.js and Python
FROM python:3.9-slim
WORKDIR /app

# Install Node.js and npm
RUN apt-get update && \
    apt-get install -y --no-install-recommends nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# Copy built Next.js app from the builder stage
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/public ./public
# Note: The standalone output includes node_modules

# Copy the Python wrapper script
COPY app.py ./

# Expose the port Next.js will run on
EXPOSE 3000
ENV PORT 3000

# Set the command to run the Python wrapper
CMD ["python", "app.py"]