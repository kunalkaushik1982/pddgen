FROM node:20-alpine AS build

WORKDIR /app/frontend

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

COPY frontend/package*.json ./
RUN npm ci

COPY frontend /app/frontend
COPY tsconfig.base.json /app/tsconfig.base.json
COPY release.json /app/release.json
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
