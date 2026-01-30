# Ollama Setup

## Installation (Arch Linux)

```bash
# Install from AUR
yay -S ollama

# Enable and start the service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull a vision model
ollama pull llava           # Default, ~4GB
ollama pull llava:13b       # Larger/better, ~8GB

# Verify it works
ollama run llava "hello"
```

## GPU Support (NVIDIA)

```bash
yay -S cuda cudnn
```

Ollama automatically detects and uses the GPU.

## Model Storage

| OS              | Path                               |
|-----------------|------------------------------------|
| Linux           | `~/.ollama/models`                 |
| Linux (systemd) | `/usr/share/ollama/.ollama/models` |
| macOS           | `~/.ollama/models`                 |
| Windows         | `C:\Users\<user>\.ollama\models`   |

### Change Storage Location

```bash
# In ~/.bashrc or ~/.zshrc
export OLLAMA_MODELS="/path/to/custom/location"

# Or for systemd service
sudo systemctl edit ollama
# Add:
# [Service]
# Environment="OLLAMA_MODELS=/mnt/bigdrive/ollama/models"
```

### Check Models

```bash
ollama list              # List downloaded models
du -sh ~/.ollama/        # Check total size
```

## Open WebUI (Web Interface)

ChatGPT-like interface for Ollama.

### Docker Setup

```bash
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

Then visit `http://localhost:3000`

### How It Connects to Host Ollama

```
┌─────────────────────────────────────────┐
│ Docker Host (your machine)              │
│                                         │
│  ┌─────────────┐    ┌────────────────┐  │
│  │ Ollama      │◄───│ Open WebUI     │  │
│  │ :11434      │    │ (container)    │  │
│  └─────────────┘    └────────────────┘  │
│        ▲                    │           │
│        └────────────────────┘           │
│     host.docker.internal:11434          │
└─────────────────────────────────────────┘
```

The `--add-host=host.docker.internal:host-gateway` flag maps the hostname to the host IP, allowing the container to reach Ollama on the host.

### Verify Connectivity

```bash
# Check Ollama is listening
curl http://localhost:11434/api/tags

# From inside the container
docker exec open-webui curl http://host.docker.internal:11434/api/tags
```

### Troubleshooting

If Open WebUI can't connect to Ollama, ensure Ollama binds to all interfaces:

```bash
# Set in environment or systemd service
OLLAMA_HOST=0.0.0.0

# Or edit systemd service
sudo systemctl edit ollama
# Add:
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0"
```

By default Ollama only listens on `127.0.0.1`, which Docker containers can't reach without the host gateway mapping.

## Other Web UIs

| UI        | Install              |
|-----------|----------------------|
| Hollama   | `yay -S hollama-bin` |
| Chatbox   | `yay -S chatbox-bin` |
| Enchanted | macOS/iOS App Store  |

## Model Recommendations (8GB VRAM)

| Model        | VRAM    | Notes                |
|--------------|---------|----------------------|
| `llava` (7B) | ~4-5GB  | Best fit for 8GB GPU |
| `llava:13b`  | ~8-10GB | May offload to RAM   |
| `llava:34b`  | ~20GB   | Won't fit            |

## API Usage

Ollama exposes REST API at `http://localhost:11434`:

```bash
# List models
curl http://localhost:11434/api/tags

# Generate text
curl http://localhost:11434/api/generate -d '{
  "model": "llava",
  "prompt": "Hello"
}'
```
