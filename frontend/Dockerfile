# --- Build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
# 任选一种包管理器，这里以 npm 为例
RUN npm install
COPY . .
RUN npm run build

# --- Export dist to a volume path for compose volume mount ---
FROM alpine:3.20 AS export
WORKDIR /app
COPY --from=build /app/dist ./dist
# 在 docker-compose 中可用 volumes: - frontend_build:/app/dist 提取构建产物

