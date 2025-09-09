# Build stage
FROM node:18 as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Serve stage (nginx)
FROM nginx:alpine
# Copy built assets to default nginx html dir
COPY --from=build /app/dist /usr/share/nginx/html
# Optional: add your nginx.conf if you need custom routing
# COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
