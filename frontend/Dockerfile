# Multi-Stage: Frontend bauen und per nginx ausliefern.
# Ermöglicht `docker compose up --build` ohne vorher lokal `npm run build`.
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
# nginx.conf wird per docker-compose als Volume gemountet (bleibt editierbar).
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
