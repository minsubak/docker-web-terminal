# --- Build stage ---
FROM node:20-alpine AS build
WORKDIR /app

# 설치 속도 최적화
ENV npm_config_fund=false npm_config_audit=false

#  의존성 설치
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Vite 빌드타임 주입
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}

# 소스 복사 및 빌드
COPY . .
RUN npm run build

# --- Runtime stage ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html