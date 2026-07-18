# Use the latest Jenkins LTS image
FROM jenkins/jenkins:lts

USER root

# Install Docker from Debian repositories
RUN apt-get update && \
    apt-get install -y docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add Jenkins user to docker group
RUN groupadd -f docker && \
    usermod -aG docker jenkins

# Docker working directory
RUN mkdir -p /var/lib/docker
VOLUME /var/lib/docker

USER jenkins