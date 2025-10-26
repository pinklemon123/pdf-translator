FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
COPY frontend/ ./
COPY nginx/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80