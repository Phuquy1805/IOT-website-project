FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build
RUN npm install --no-audit --silent --global serve

EXPOSE 9000
CMD ["serve","-s","dist","-l","9000"]
# CMD ["npm", "run", "dev", "--host", "0.0.0.0", "--port", "9000"]