#!/bin/bash

# Define colors
RED='\033[0;31m'   # Red colored text
NC='\033[0m'       # Normal text
YELLOW='\033[33m'  # Yellow Color
GREEN='\033[32m'   # Green Color

# Update packages
echo -e "${YELLOW}Updating packages...${NC}"
if ! sudo apt update; then
    echo -e "${RED}Failed to update packages.${NC}"
    exit 1
fi

# Install Docker if not already installed
echo -e "${YELLOW}Installing Docker...${NC}"
if ! sudo apt install docker.io -y; then
    echo -e "${RED}Failed to install Docker.${NC}"
    exit 1
fi

# Change directory to NEW_CODES
read -p "Enter the project folder name: " project_folder
cd "$project_folder" || { echo -e "${RED}Failed to change directory.${NC}"; exit 1; }

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
if ! sudo docker build -t bill_import_image:1.0 .; then
    echo -e "${RED}Failed to build Docker image.${NC}"
    exit 1
fi

# Check if Docker image is created
echo -e "${YELLOW}Checking Docker image...${NC}"
if ! sudo docker images | grep -q "bill_import_image"; then
    echo -e "${RED}Docker image 'bill_import_image:1.0' not found.${NC}"
    exit 1
fi

# Run Docker container
echo -e "${YELLOW}Running Docker container...${NC}"
if ! sudo docker run -d -p 5000:5000 bill_import_image:1.0; then
    echo -e "${RED}Failed to run Docker container.${NC}"
    exit 1
fi

# Check open ports
echo -e "${YELLOW}Checking open ports...${NC}"
if ! sudo apt install net-tools -y; then
    echo -e "${RED}Failed to install net-tools.${NC}"
    exit 1
fi

if ! sudo ss -tuln | grep -q ":5000"; then
    echo -e "${RED}Port 5000 is not open.${NC}"
    exit 1
fi

# Check connection
# Check connection
echo -e "${YELLOW}Checking connection...${NC}"
ip_service="ifconfig.me/ip"  # or "ipecho.net/plain"
public_ip=$(curl -sS "$ip_service")

# Check if the public IP retrieval was successful
if [ -z "$public_ip" ]; then
    echo -e "${RED}Failed to retrieve public IP.${NC}"
    exit 1
fi

# Double quote the variable to handle special characters
if ! nc -zv "$public_ip" 5000; then
    echo -e "${RED}Connection to port 5000 failed.${NC}"
    exit 1
fi


# Additional curl commands
echo -e "${YELLOW}Additional curl commands...${NC}"
if ! curl -sS "http://$public_ip:5000/process-emails"; then
    echo -e "${RED}Failed to curl http://$public_ip:5000/process-emails.${NC}"
fi

if ! curl -sS "http://$public_ip:5000/check-both-connections"; then
    echo -e "${RED}Failed to curl http://$public_ip:5000/check-both-connections.${NC}"
fi

if ! curl -sS "http://$public_ip:5000/check-db-connection"; then
    echo -e "${RED}Failed to curl http://$public_ip:5000/check-db-connection.${NC}"
fi

if ! curl -sS "http://$public_ip:5000/check-url-connection"; then
    echo -e "${RED}Failed to curl http://$public_ip:5000/check-url-connection.${NC}"
fi

echo -e "${GREEN}Script execution completed.${NC}"