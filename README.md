# Automaton - Autonomous Multi-Agent AI System

An autonomous, self-healing multi-agent AI system designed for Linux. It utilizes the NVIDIA NIM API to spawn a cluster of "Worker AIs", managed by a "Chef AI". The workers are capable of executing bash commands, searching the web, and making Ethereum transactions to generate and transfer ETH.

## Architecture

- **Chef AI (`chef.py`)**: The orchestrator. It manages the pool of workers, evaluates their progress, and replaces unviable or underperforming agents with new ones initialized with fresh strategies.
- **Worker AI (`worker.py`)**: An isolated agent running a continuous ReAct loop. It connects to the NVIDIA NIM API and leverages available tools.
- **Shared Skills (`shared_skills/`)**: A directory of tools accessible to the workers (Bash Execution, Web Search, ETH Transfer).

## Requirements

- **Linux OS** (Ubuntu/Debian recommended)
- **Python 3.10+**
- NVIDIA API Keys (From [build.nvidia.com](https://build.nvidia.com))

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Conway-Research/automaton.git
cd automaton

# 2. Install Dependencies
pip install -r requirements.txt
```

## Setup & Execution

You can run and configure the system using either the **Web GUI** or the **Command Line Interface (CLI)**.

### Option 1: Web GUI (Recommended)

The Web GUI provides a simple interface to manage the environment and start/stop the system.

```bash
python web_gui.py
```

1. Open your browser and navigate to `http://localhost:5000` (or your server's IP).
2. Enter your `NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2`, `RPC_URL`, and `PRIVATE_KEY`.
3. Click **Save Configuration**.
4. Click **Start System**. The Chef process will launch in the background.

### Option 2: CLI Interface

If you prefer terminal management, use the provided `cli.py` tool.

First, create a `.env` file in the root directory:
```bash
echo "NVIDIA_API_KEY_1=your_key_here" >> .env
echo "NVIDIA_API_KEY_2=your_key_here" >> .env
echo "RPC_URL=https://mainnet.infura.io/v3/..." >> .env
echo "PRIVATE_KEY=your_private_key" >> .env
```

Manage the system using the CLI:
```bash
# Start the system (runs in the background)
python cli.py start

# Check if the system is running
python cli.py status

# Stop the system
python cli.py stop
```

*Logs are written to `chef.log` and worker outputs are tracked within their individual `workspaces/<id>/status.txt` files.*

## Safety Warning

**WARNING:** This system has `shell=True` bash execution enabled by design, meaning the AI agents have complete control over the system they run on. It is highly recommended to run this in a restricted VM, container, or disposable cloud instance. Do NOT run this on your personal machine without virtualization.
