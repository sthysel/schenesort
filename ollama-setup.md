# Ollama Setup

## Installation (Arch Linux)

```bash
# Install from AUR
yay -S ollama

# For NVIDIA GPU support, also install the CUDA library:
yay -S ollama-cuda

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

On Arch Linux, you need **both** packages for GPU acceleration:

```bash
yay -S ollama ollama-cuda
```

The `ollama-cuda` package provides `/usr/lib/ollama/libggml-cuda.so` which the base `ollama` package loads at runtime. After installing, restart the service:

```bash
sudo systemctl restart ollama
```

Verify GPU is being used:

```bash
ollama ps
# Should show "100% GPU" not "100% CPU"
```

If still showing CPU, check the CUDA library exists:

```bash
ls -la /usr/lib/ollama/libggml-cuda.so
```

## Troubleshooting GPU/Timeout Issues

### "Timed out waiting for llama runner to start"

If you see this error in the logs (`journalctl -u ollama -f`), the model is loading to GPU but the runner times out before starting.

**Increase timeout and reduce parallelism:**

```bash
sudo systemctl edit ollama
```

Add:
```ini
[Service]
Environment="OLLAMA_KEEP_ALIVE=10m"
Environment="OLLAMA_NUM_PARALLEL=1"
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Debug Mode

Run Ollama manually to see real-time errors:

```bash
sudo systemctl stop ollama
OLLAMA_DEBUG=1 ollama serve
```

In another terminal:
```bash
ollama run llava "test"
```

### Enable NVIDIA Persistence Mode

Prevents GPU from entering low-power state that can cause slow initialization:

```bash
sudo nvidia-smi -pm 1
```

### Test with a Smaller Model

If llava (~4GB) is close to your available VRAM, try a smaller model first:

```bash
ollama pull gemma:2b
ollama run gemma:2b "hello"
ollama ps  # Verify GPU usage
```

### Check VRAM Usage

```bash
nvidia-smi
# Look at "Memory-Usage" - you need enough free VRAM for the model
```

### CUDA API Image Processing Bug

There's a known issue where CUDA mode crashes when processing images via the API, while interactive mode (`/image` command) works fine. Symptoms:

- `ollama run llava "hello"` works (text-only on GPU)
- `/image` in interactive mode works
- API calls with images crash: "model runner has unexpectedly stopped"

**Workaround Option 1 - Prefix commands (temporary):**

```bash
CUDA_VISIBLE_DEVICES="" schenesort describe ~/wallpapers
CUDA_VISIBLE_DEVICES="" schenesort metadata generate ~/wallpapers
```

This forces CPU mode for just that command while leaving Ollama's GPU enabled for other uses.

**Workaround Option 2 - Run Ollama in CPU mode (permanent):**

```bash
sudo systemctl edit ollama
```

Add:
```ini
[Service]
Environment="CUDA_VISIBLE_DEVICES="
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

This disables GPU acceleration globally but allows the API to work reliably. Remove these lines once the bug is fixed upstream.

To re-enable GPU later, delete the override:
```bash
sudo rm /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

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
