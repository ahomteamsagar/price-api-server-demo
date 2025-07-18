# Build the Docker image
docker build -t price-api-server .

# Run the container
docker run -p 8000:8000 price-api-server

# Or run in detached mode with a name
docker run -d -p 8000:8000 --name price-api price-api-server

# View running containers
docker ps

# Stop the container
docker stop price-api

# View logs
docker logs price-api

# Remove container
docker rm price-api