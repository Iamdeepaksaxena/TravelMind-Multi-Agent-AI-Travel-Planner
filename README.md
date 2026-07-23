# TravelMind: Multi-Agent AI Travel Planner
TravelMind is an end-to-end multi-agent AI platform designed to automate travel planning using Agentic AI and LLM-powered workflows. The application employs LangGraph for agent orchestration and LangChain for tool integration, enabling specialized agents to collaboratively generate personalized travel itineraries, recommend hotels and flights, provide weather insights, perform currency conversion, and retrieve location-based information. The backend is built with FastAPI, PostgreSQL, Docker, and LangSmith, following production-oriented software engineering practices.

## 📂 Project Structure

```text
TravelMind-Multi-Agent-AI-Travel-Planner/
│
├── agent/
│   ├── __init__.py
│   └── agent.py
│
├── assets/
│   ├── Image1.png
│   ├── Image2.png
│   ├── Jenkins.png
│   ├── LangSmith.png
│   ├── SonarQube.png
│   └── Video.mp4
│
├── backend/
│   └── fastapi.py
│
├── common/
│   ├── __init__.py
│   ├── custom_exceptions.py
│   └── logger.py
│
├── config/
│   ├── __init__.py
│   └── settings.py
│
├── custom_jenkins/
│   └── Dockerfile
│
├── logs/
│
├── tools/
│   ├── __init__.py
│   ├── currency_tool.py
│   ├── flight_tool.py
│   ├── maps_tool.py
│   ├── tavily_tool.py
│   └── weather_tool.py
│
├── .env
├── .gitignore
├── app.py
├── Jenkinsfile
├── LICENSE
├── README.md
├── requirements.txt
└── setup.py
```

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
## 🔗 Step 2 : GitHub Integration with Jenkins
Follow the steps below to integrate GitHub with Jenkins for automated pipeline execution:
### 1. Generate Personal GitHub Access Token
1. Go to **GitHub**.
2. Navigate to **Settings** -> **Developer Settings** -> **Personal Access Tokens** -> **Classic**.
3. Click on **Generate New Token**.
4. Provide a **name** and select the following **permissions**:
   - `repo` (for repository access)
   - `repo_hook` (for hook access)
5. Click **Generate Token**.
6. **Save** the token securely somewhere (you will not be able to view it again after this page).
---

### 2. Add GitHub Token to Jenkins
1. Go to the **Jenkins Dashboard**.
2. Click **Manage Jenkins** -> **Manage Credentials** -> **Global**.
3. Click **Add Credentials**.
4. In the **Username** field, enter your **GitHub account name**.
5. In the **Password** field, paste the **GitHub token** you just generated.
6. In the **ID** field, enter a name for this credential (e.g., `github-token`).
7. Add a **Description** (e.g., `GitHub access token`).
8. Click **OK** to save the credentials.
---

### 3. Create a Pipeline Job in Jenkins
1. Go to the **Jenkins Dashboard**.
2. Click on **New Item**.
3. Select **Pipeline** and provide a name for the job.
4. Click **Apply** and then **Create**.
---

### 4. Configure Pipeline Checkout
1. On the left sidebar of the Jenkins job, click **Pipeline Syntax**.
2. Under **Step**, select **checkout**.
3. Fill in the necessary details, such as:
   - **Repository URL** (your GitHub repository URL)
   - **Credentials** (select the `github-token` created earlier)
4. Click **Generate Pipeline Script**.
5. Copy the generated script.
---

### 5. Create `Jenkinsfile` in VS Code
1. Open **VS Code** and create a file named **`Jenkinsfile`** ( already done if cloned )
2. For now only keep the first stage of Jenkinsfile rest should be commendted out.
> **Explanation**: This simple pipeline has one stage, **Checkout**, where Jenkins will fetch the latest code from your GitHub repository.
3. Push the `Jenkinsfile` to your GitHub repository.
---

### 7. Run the Pipeline
1. Go back to the **Jenkins Dashboard**.
2. Click on **Build Now** for your pipeline job.
3. Wait for the build process to complete.
---

### 8. Check Pipeline Success
Once the pipeline finishes, you will see a success message, indicating that your first pipeline run was successful. Additionally, in the **Workspace** of the job, you will see that Jenkins has cloned your GitHub repository.
---


# 📊 Step 3 : SonarQube Integration with Jenkins
Follow these steps to integrate **SonarQube** with Jenkins for code quality analysis.
### 1. Download and Run SonarQube Docker Container
1. Go to **DockerHub** and search for **SonarQube**. Scroll down to find the commands.
2. Run the following commands in a new WSL terminal to configure the system:
```bash
sysctl -w vm.max_map_count=524288
sysctl -w fs.file-max=131072
ulimit -n 131072
ulimit -u 8192
```
3. Run the SonarQube container with the appropriate settings. Make sure to change the container name to `sonarqube-dind` and remove the dollar sign (`$`) from the command. You will find the command in the **Demo** section of DockerHub.
```bash
docker run -d --name sonarqube-dind \
  -p 9000:9000 \
  -e SONARQUBE_JDBC_URL=jdbc:postgresql://localhost/sonar \
  sonarqube
```
4. Check if the container is running:
```bash
docker ps
```
5. Access **SonarQube** on `http://<WSL_IP>:9000` (replace `<WSL_IP>` with your WSL IP address). Log in using the default credentials:
- **Username:** `admin`
- **Password:** `admin`
---

### 2. Install Jenkins Plugins for SonarQube
1. Go to **Jenkins Dashboard** -> **Manage Jenkins** -> **Manage Plugins**.
2. Install the following plugins:
   - **SonarScanner**
   - **SonarQualityGates**
3. Restart the Jenkins container inside wsl:
```bash
docker restart jenkins-dind
```
---
### 3. Set Up SonarQube in Jenkins
1. Go to **SonarQube** -> **Create a Local Project**.
   - Enter a name for the project (e.g., `TravelMind LLMOps`).
   - Set the **Main Branch**.
   - Save the project.
2. Go to **SonarQube** -> **My Account** (top-right) -> **Security** -> **Generate New Token**.
   - Provide a name (e.g., `global-analysis-token`) and generate the token.
   - Copy the generated token.
3. Go to **Jenkins Dashboard** -> **Manage Jenkins** -> **Credentials** -> **Global**.
4. Add a new **Secret Text** credential:
   - **ID:** `sonarqube-token`
   - **Secret:** Paste the token from SonarQube.
   - Click **OK** to save.
---

### 4. Configure SonarQube in Jenkins
1. Go to **Manage Jenkins** -> **System Configuration**.
2. Scroll down to **SonarQube Servers** and click **Add SonarQube**.
   - **Name:** `SonarQube` (or any name you prefer)
   - **URL:** `http://<WSL_IP>:9000` (replace `<WSL_IP>` with your actual IP address)
   - Select **SonarQube Token** from the credentials dropdown.
   - Apply and save.
3. Go to **Manage Jenkins** -> **Tools** and look for **SonarQube Scanner**.
   - Select **SonarQube Scanner** and configure it.
   - Tick the option **Install Automatically**.
---

### 5. Create a Stage in `Jenkinsfile` for SonarQube
1. Open the **Jenkinsfile** in **VS Code** and add the Sonarqube stage ( already provided in the code )
2. Push the changes to your **GitHub** repository.
---

### 6. Create a Docker Network for Jenkins and SonarQube
1. Run the following command to create a new Docker network:
```bash
docker network create dind-network
```
2. Connect both containers to the new network:
```bash
docker network connect dind-network jenkins-dind
docker network connect dind-network sonarqube-dind
```
3. Update the `Jenkinsfile` to use the container name instead of the IP address: (already done in code)
```groovy
-Dsonar.host.url=http://sonarqube-dind:9000
```
---
### 8. Final Pipeline Run
1. Trigger the **Jenkins Pipeline**.
2. The build should now be successful, and the code will be analyzed by **SonarQube**.

---
### 9. View Results in SonarQube
Go to **SonarQube** and see the code quality report generated for your project.
---

