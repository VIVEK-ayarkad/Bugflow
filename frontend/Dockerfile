# ── Step 1: Build React Assets ────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies with npm clean install
COPY package*.json ./
RUN npm ci

# Copy source code and build bundle
COPY . .
RUN npm run build

# ── Step 2: Serve with Nginx ─────────────────────────────────────────────────
FROM nginx:alpine

# Copy built assets to Nginx html root
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose standard HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
