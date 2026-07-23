# TravelMind-Multi-Agent-AI-Travel-Planner

## WSL Installation
## 🐧 Installing Ubuntu via WSL and Docker Engine Inside Ubuntu (on Windows)

### 🔧 Step 1: Enable WSL and Virtualization
Open **PowerShell as Administrator** and run:
```powershell
wsl --install
```
If WSL is already installed, update it:
```powershell
wsl --update
```
> Reboot your system if prompted.
---

### 🛍️ Step 2: Install Ubuntu
1. Open **Microsoft Store**
2. Search for **Ubuntu**
3. Choose a version (e.g., **Ubuntu 22.04 LTS**)
4. Click **Get** or **Install**
5. Launch Ubuntu from Start Menu and set up username/password
---

### 🐳 Step 3: Install Docker Engine in Ubuntu (WSL)
Run the following commands in the Ubuntu terminal:
```bash
# 1. Update package index and install dependencies
sudo apt update
sudo apt install ca-certificates curl gnupg lsb-release -y

# 2. Add Docker’s official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 3. Set up the Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Install Docker Engine
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# 5. Add user to docker group (optional but recommended)
sudo usermod -aG docker $USER
```
> 🔁 **Restart the Ubuntu terminal** after running the above to apply group changes.
---
✅ You can now run Docker inside Ubuntu WSL:
```bash
docker --version
```
---

# 🛠️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Iamdeepaksaxena/TravelMind-Multi-Agent-AI-Travel-Planner.git
```

### 2. Create and Activate a Virtual Environment
#### On Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
Install the required libraries using:
```bash
pip install -e .
```

### 4. Run the Application Locally
```bash
python app/main.py
```

---

## ✅ Progress Checklist
The following essential setup steps have been completed:
- ✅ **WSL Setup Full**
  - Ubuntu installed via Microsoft Store
  - Docker Engine installed inside Ubuntu WSL
  - Project runs successfully in WSL

- ✅ **Dockerfile Created**
  - Dockerfile written for the project
  - Environment variables setup will be handled later
  - Do **not** include `.env` in the Dockerfile for now

- ✅ **GitHub Setup Completed**
  - Project is pushed to GitHub
  - `.gitignore` is properly configured and includes `.env`

---

🟢 **You are now ready to move forward with Deployment phase.**
Follow the steps below to deploy the application.
- Make sure you run commands inside a WSL terminal in VS Code
---
## 🛠️ Step 1 : Jenkins Setup for CI/CD (via Docker)
Follow the steps below to set up Jenkins inside a Docker container and configure it for the project:
### 1. Create `custom_jenkins` Folder ( already done if cloned )
### 2. Create Dockerfile Inside `custom_jenkins` ( already done if cloned )
### 3. Build Docker Image
Build the Docker image for Jenkins:
```bash
docker build -t jenkins-dind .
```
### 4. Run Jenkins Container
Run the Jenkins container with the following command:
```bash
docker run -d --name jenkins-dind \
  --privileged \
  -p 8080:8080 -p 50000:50000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v jenkins_home:/var/jenkins_home \
  jenkins-dind
```
> After successful execution, you'll receive a long alphanumeric string.
### 5. Verify the Running Container
To verify if the Jenkins container is running:
```bash
docker ps
```
### 6. Get Jenkins Logs and Password
To retrieve Jenkins logs and get the initial admin password:
```bash
docker logs jenkins-dind
```
You should see a password in the output. Copy that password.
### 7. Find WSL IP Address
Run the following command to get the IP address of your WSL environment:
```bash
ip addr show eth0 | grep inet
```
### 8. Access Jenkins
Now, access Jenkins on your browser using the following URL (replace `172.23.129.123` with the actual WSL IP address you retrieved):
```text
http://172.23.129.123:8080
```
### 9. Install Python and Set Up Jenkins
Return to the terminal and run the following commands to install Python inside the Jenkins container:
```bash
docker exec -u root -it jenkins-dind bash
apt update -y
apt install -y python3
python3 --version
ln -s /usr/bin/python3 /usr/bin/python
python --version
apt install -y python3-pip
exit
```

### 10. Restart Jenkins Container
Restart the Jenkins container to apply changes:
```bash
docker restart jenkins-dind
```

### 11. Sign in to Jenkins
Go to the Jenkins dashboard and sign in using the initial password you retrieved earlier.
---
