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

# Update package index and install dependencies
echo -e "${YELLOW}Updating package index and installing dependencies...${NC}"
if ! sudo apt update && sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common; then
    error "Failed to update package index or install dependencies."
fi

# Add Docker's official GPG key
echo -e "${YELLOW}Adding Docker's official GPG key...${NC}"
if ! curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -; then
    error "Failed to add Docker's GPG key."
fi

# Add Docker repository
echo -e "${YELLOW}Adding Docker repository...${NC}"
if ! sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"; then
   error "Failed to add Docker repository."
fi

# Update package index again
echo -e "${YELLOW}Updating package index again...${NC}"
if ! sudo apt update; then
    error "Failed to update package index again."
fi

# Install Docker Engine
echo -e "${YELLOW}Installing Docker Engine...${NC}"
if ! sudo apt install -y docker-ce docker-ce-cli containerd.io; then
    error "Failed to install Docker Engine."
fi

# Add current user to docker group to run docker commands without sudo
echo -e "${YELLOW}Adding current user to docker group...${NC}"
if ! sudo usermod -aG docker $USER; then
    error "Failed to add current user to docker group."
fi

# Install Docker Compose
echo -e "${YELLOW}Installing Docker Compose...${NC}"
if ! sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    sudo chmod +x /usr/local/bin/docker-compose && \
    sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose; then
    error "Failed to install Docker Compose."
fi

# Output Docker and Docker Compose versions
success "Docker and Docker Compose installed successfully."
echo -e "${GREEN}Docker version:$(docker --version)${NC}"
echo -e "${GREEN}Docker Compose version:$(docker-compose --version)${NC}"

# Prompt user to logout for group changes to take effect
echo "Please log out and log back in for the group changes to take effect."
