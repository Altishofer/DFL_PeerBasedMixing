[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![SphinxMix](https://img.shields.io/badge/SphinxMix-6E4C1E?logo=tor&logoColor=white)](https://github.com/Katzenpost/sphinxmix)
[![Scikit-learn](https://img.shields.io/badge/Scikit--Learn-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-0A0A0A?logo=python&logoColor=white)](https://www.uvicorn.org/)


# Peer Based Mixing for Decentralized Federated Learning

Peer-based decentralized federated learning (DFL) over a stateless mixnet, with full control via FastAPI and a React frontend.

---

## Table of Contents

- [Features](#features)
- [Quickstart](#quickstart)
- [Project Structure](#project-structure)
- [Useful Commands](#useful-commands)
- [Main Technologies Used](#main-technologies-used)
- [To Do](#to-do)
- [Notes](#notes)

---

## Features

- Peer-based DFL simulation using Docker
- Stateless mixnet communication based on
- Federated learning over encrypted transport
- FastAPI backend for node management 
- React frontend for UI control
- Inline acknowledgments and message tracking

---

## Main Technologies Used

- [FastAPI](https://fastapi.tiangolo.com/) — Python async web framework for backend management
- [React.js](https://react.dev/) — Frontend JavaScript library for building user interfaces
- [Docker](https://www.docker.com/) — Containerization for node simulation
- [SphinxMix](https://sphinxmix.readthedocs.io/en/latest/) — Mixnet packet format used for anonymous routing
- [Scikit-learn](https://scikit-learn.org/) — For machine learning models
- [Uvicorn](https://www.uvicorn.org/) — ASGI server used to run FastAPI apps

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/Altishofer/DFL_PeerBasedMixing.git
cd DFL_PeerBasedMixing
```

### 2. Build the Docker image for nodes

```bash
docker build -t dfl_node ./node
```

*or for debugging purposes*

```bash
docker build -t dfl_node ./node --progress=plain --no-cache
```

### 3. Install Python requirements

```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI backend

```bash
uvicorn manager.app:app --host 0.0.0.0 --port 8000
```

Backend runs at [http://localhost:8000](http://localhost:8000).

### 5. Install Node.js and set up the React frontend

```bash
sudo apt install npm
npm install --prefix frontend
```

### 6. Start the React frontend

```bash
npm start --prefix frontend
```

Frontend runs at [http://localhost:3000](http://localhost:3000).

---

## Project Structure

```bash
DFL_PeerBasedMixing/
├── node/        # Dockerized node logic
├── manager/     # FastAPI backend for node control
└── frontend/    # React frontend interface
```

---

## Useful Commands

#### Force Stop and remove all Docker containers (force reset)

```bash
docker ps -aq | xargs -r docker rm -f
```

```bash
docker inspect --format '{{.State.Pid}}' $(docker ps -q) | xargs -r sudo kill -9
```


---

## To Do

### Jan
- Novelty of our implementation
- Model and network anonymity for DFL
- Wait for the implementation to condensate, start writing again

### Linn
- Parametrization of scenario through front & backend
- Implement streaming-based FL aggregation (send parts during each epoch)
- Enable and disable mixnet routing for experimental purposes
- Mixing strategies (delay, shuffle, batch, dummy)
- Cache fragment size 
- ✅ Switch to structured JSON model updates instead of serialized byte streams
- ✅ Aggregation algo which aggregates all model fragments, ignoring any identity and parameter distribution
- ✅ Implement more robust fragment-based aggregation
- Enable and disable mixnet routing for experimental purposes
- Mixing strategies (delay, shuffle, batch, dummy)

### Sandrin
- ✅ Allow free join/leave of nodes by decoupling strict round synchronization
- ✅ Add early stop of collecting models if peers * model_parts was received
- ✅ Add parametrization of number of nodes to join late or leave early
- ✅ Cut TCP connection if a node closes the connection
- ✅ Add new or restarted connection to active nodes if handshake is received
- ✅ Refactoring using CNN with torch instead of MLP
- ✅ Refactoring whole model aggregation and model fragmentation
- ✅ Improved logging, added aggregated and local accuracy to dashboard

- ✅ Real-time node statistics and visualization in the frontend
- ✅ Use persistent TCP connections (currently, each message uses a new socket)
- ✅ Add resend logic for lost packets

### Altin
- Enable and disable mixnet routing for experimental purposes
- Mixing strategies (delay, shuffle, batch, dummy)
- Add message hashes for payload verification and replay protection
- Frontend, clear log and old metrics when restarting

### Discarded
- Introduce random synonyms for models and fragments to improve unlinkability

## Notes
- write about small prototypes
- think about experiments



---

sudo snap remove --purge docker
https://docs.docker.com/engine/install/ubuntu/

uvicorn app:app  --host 0.0.0.0 --port 8000 --workers 1




# Experiments

## Time per scenario
- y: time per whole scenario
- x: delay in seconds

## CPU utilization per state (training, waiting, aggregating, broadcasting)
- y: Total CPU time per stage
- x:
  - number of batches
  - number of nodes
  - number of hops


## Memory utilization per state (training, waiting, aggregating, broadcasting)
- y: RTT
- x:
  - delay in seconds
  - number of hops
- compute data rate with same data

## Transmission size comparison between encrypted and raw payload
- y: size in bytes
- x:
  - number of hops

## Number of forwardings 
- y: number of forwardings
- x:
  - number of hops
  - number of nodes

## Aggregated Accuracy (show that framework works, fragment base FedAvg)
- y: accuracy
- x: dirichlet distribution


## Exit and joining nodes
- y: active nodes, number of resent packets, number of lost packets, number of dropped unacked message
- x: time
- show that mixnet is resilient to node exits and joins


