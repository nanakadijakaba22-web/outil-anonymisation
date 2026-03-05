# Next.js Frontend Development Dockerfile
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies (only copy package files first for caching)
COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN \
  if [ -f package-lock.json ]; then npm install; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm install; \
  else npm install; \
  fi

# Note: In development, we mount the source code as a volume
# but we copy it here just in case or for non-compose usage
COPY . .

# Expose Next.js port
EXPOSE 3000

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development

# Run development server
CMD ["npm", "run", "dev"]
