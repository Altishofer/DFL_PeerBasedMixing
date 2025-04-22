# DFL_PeerBasedMixing


## Features

- Peer-based DFL simulation using Docker  
- Stateless mixnet communication with inline acknowledgments  
- FastAPI backend for launching and managing node scenarios  
- React frontend for user control and node status

## Quickstart

### 1. Clone the repository

git clone https://github.com/Altishofer/DFL_PeerBasedMixing.git  
cd DFL_PeerBasedMixing

### 2. Build the node Docker image

docker build -t dfl_node ./node

### 2. Install requirements
pip install -r requirements.txt


### 3. Start the FastAPI manager backend

cd manager  
uvicorn app:app --reload

The backend runs at http://localhost:8000 and exposes endpoints for starting and stopping nodes.

### 4. Install Node.js and set up the frontend

sudo apt install npm   
cd frontend  
npm install

### 5. Start the React frontend

npm start

Then open http://localhost:3000 in your browser.

## Project Structure

DFL_PeerBasedMixing/  
├── node/ — Dockerized DFL node logic  
├── manager/ — FastAPI backend controller  
├── frontend/ — React frontend interface  
├── requirements.txt  
└── README.md


sudo /home/students/DFL_PeerBasedMixing/.venv/bin/uvicorn app:app --reload

docker ps -aq | xargs -r docker rm -f
