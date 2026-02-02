FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Serve the app
EXPOSE 3000
CMD ["npm", "start"]
