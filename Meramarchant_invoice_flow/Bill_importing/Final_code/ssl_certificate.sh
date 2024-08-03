#!/bin/bash

# Define colors
RED='\033[0;31m'   # Red colored text
NC='\033[0m'       # Normal text
YELLOW='\033[33m'  # Yellow Color
GREEN='\033[32m'   # Green Color

# Function to display error message and exit
error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

# Function to display success message
success() {
    echo -e "${GREEN}$1${NC}"
}

# Update packages
echo -e "${YELLOW}Updating packages...${NC}"
if ! sudo apt update; then
    error "Failed to update packages."
fi

# Install Docker if not already installed
echo -e "${YELLOW}Installing Docker...${NC}"
if ! sudo apt install docker.io -y; then
    error "Failed to install Docker."
fi

# Prompt user for domain name
read -p "Enter your domain name (e.g., example.com): " domain_name

# Install certbot for SSL certificate
echo -e "${YELLOW}Installing Certbot for SSL certificate...${NC}"
if ! sudo apt install certbot -y; then
    error "Failed to install Certbot."
fi

# Obtain SSL certificate
echo -e "${YELLOW}Obtaining SSL certificate for domain $domain_name...${NC}"
if ! sudo certbot certonly --standalone -d "$domain_name"; then
    error "Failed to obtain SSL certificate for domain $domain_name."
fi

# Add cron job for certificate auto-renewal
echo -e "${YELLOW}Adding cron job for certificate auto-renewal...${NC}"
if ! (sudo crontab -l | { cat; echo "0 0 1 * * certbot renew --quiet"; }) | sudo crontab -; then
    error "Failed to add cron job for certificate auto-renewal."
fi

# Change directory to project folder
read -p "Enter the project folder name: " project_folder
cd "$project_folder" || error "Failed to change directory to $project_folder."

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
if ! sudo docker build -t bill_import_image:1.0 .; then
    error "Failed to build Docker image."
fi

# Check if Docker image is created
echo -e "${YELLOW}Checking Docker image...${NC}"
if ! sudo docker images | grep -q "bill_import_image"; then
    error "Docker image 'bill_import_image:1.0' not found."
fi

# Run Docker container
echo -e "${YELLOW}Running Docker container...${NC}"
if ! sudo docker run -d -p 5000:5000 bill_import_image:1.0; then
    error "Failed to run Docker container."
fi

# Check open ports
echo -e "${YELLOW}Checking open ports...${NC}"
if ! sudo apt install net-tools -y; then
    error "Failed to install net-tools."
fi

if ! sudo ss -tuln | grep -q ":5000"; then
    error "Port 5000 is not open."
fi

# Check connection
echo -e "${YELLOW}Checking connection...${NC}"
ip_service="ifconfig.me/ip"  # or "ipecho.net/plain"
public_ip=$(curl -sS "$ip_service")

# Check if the public IP retrieval was successful
if [ -z "$public_ip" ]; then
    error "Failed to retrieve public IP."
fi

# Double quote the variable to handle special characters
if ! nc -zv "$public_ip" 5000; then
    error "Connection to port 5000 failed."
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

# SSL Configuration
echo -e "${YELLOW}Configuring SSL...${NC}"
sudo cp /etc/letsencrypt/live/$domain_name/fullchain.pem /path/to/your/app/cert.pem || error "Failed to copy SSL certificate."
sudo cp /etc/letsencrypt/live/$domain_name/privkey.pem /path/to/your/app/privkey.pem || error "Failed to copy SSL private key."

# Application Configuration
echo -e "${YELLOW}Configuring application...${NC}"
# Update your Flask app configuration to use the copied SSL certificate and private key.

# HTTP to HTTPS Redirect
echo -e "${YELLOW}Configuring HTTP to HTTPS redirect...${NC}"
# Assuming you're using Nginx as a reverse proxy, configure it to redirect HTTP traffic to HTTPS.
# Add a server block for HTTP to redirect to HTTPS. Example configuration:
# server {
#     listen 80;
#     server_name example.com;
#     return 301 https://$host$request_uri;
# }

success "Script execution completed."
exit 0  # Add exit command to indicate successful completion
