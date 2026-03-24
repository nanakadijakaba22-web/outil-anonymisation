# Production-ready Next.js frontend Dockerfile
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Install build deps (copy lock files first to leverage cache)
COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN set -eux; \
  if [ -f package-lock.json ]; then npm ci --silent; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm install --silent; \
  else npm ci --silent; \
  fi

# Copy source and build
COPY . .
# Force Next.js to use webpack during build to avoid Turbopack/webpack conflict
RUN npm run build -- --webpack

########### Runtime image ###########
FROM node:20-alpine AS runtime
WORKDIR /app

# Install only production dependencies (if package-lock.json present)
COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN set -eux; \
  if [ -f package-lock.json ]; then npm ci --only=production --silent; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm install --prod --silent; \
  else npm ci --only=production --silent; \
  fi

# Copy built output from builder
COPY --from=builder /app/.next .next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose port and set env
EXPOSE 3000
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Start the Next.js server
CMD ["npm", "run", "start"]
