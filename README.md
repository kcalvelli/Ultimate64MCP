# Commodore 64 Ultimate — MCP Server

<p align="center">
  <img src="https://img.shields.io/badge/Status-Alpha-orange.svg" alt="Alpha">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/MCP-1.0-green.svg" alt="MCP">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

> ⚠️ **Alpha Release**
> 
> This is an alpha release. It has been tested with my own Ultimate boards and home network setup, but I have not extensively tested all configuration combinations and API endpoints. Consider this a starting point to play and have fun with! Contributions, bug reports, and feedback are welcome.

A **Model Context Protocol (MCP)** server for the **Commodore 64 Ultimate** — the official modern Commodore 64 computer. This server enables AI assistants like Claude, ChatGPT, and Cursor to control your C64 via the Ultimate's REST API.

---

## 🎯 What is This?

### The Commodore 64 Ultimate

The **Commodore 64 Ultimate** is an official Commodore product — a brand new Commodore 64 for the modern era. Inside, it uses a revision of the **Ultimate 64** FPGA mainboard designed by [Gideon Zweijtzer](https://github.com/GideonZ) of [Gideon's Logic](https://ultimate64.com/). It's not an emulator — it *is* a real Commodore 64, cycle-accurate and built with modern technology.

The Commodore 64 Ultimate features USB storage, ethernet, HDMI output, and a powerful REST API for remote control. This MCP server leverages that REST API to let AI assistants interact with the C64 directly.

### Also Compatible With

This server also works with other products from [Gideon's Logic](https://ultimate64.com/):

| Device | Description |
|--------|-------------|
| **[Ultimate 64](https://ultimate64.com/Ultimate-64)** | The original FPGA-based Commodore 64 mainboard by Gideon's Logic. |
| **[Ultimate II+](https://ultimate64.com/Ultimate-II)** | A cartridge for your original Commodore 64 or C128, adding USB storage, ethernet, drive emulation, and more. |

All Ultimate devices expose the same REST API that this MCP server uses.

### What Does This MCP Server Do?

This MCP server acts as a **bridge** between AI assistants and your Commodore 64 Ultimate (or other Ultimate devices), translating natural language commands into API calls. With it, you can:

- Load and run C64 programs (PRG, SID, MOD files)
- Read/write C64 memory directly
- Mount and create disk images (D64, D71, D81)
- Control drive emulation
- Manage device configuration
- Stream audio/video (Ultimate 64 only)

---

## ✨ Features

- **37 Tools** covering all major Ultimate device functionality
- **Dual Transport Modes**: STDIO (local) and SSE (remote/hosted)
- **Docker Support**: Easy containerized deployment
- **Dynamic Connection**: Set C64 connection at runtime
- **Upload PRG via Base64/URL**: Run programs from anywhere
- **Secure by Default**: Non-root Docker container

---

## 📋 Available Tools

### Connection Management

| Tool | Description |
|------|-------------|
| `ultimate_set_connection` | Set the hostname and port of the Ultimate C64 device |
| `ultimate_get_connection` | Get the current connection details |
| `ultimate_version` | Get the REST API version |

### Program Execution

| Tool | Description |
|------|-------------|
| `ultimate_run_program` | Run a program already stored on the Ultimate's filesystem (USB/SD) |
| `ultimate_load_program` | Load a program into memory without running it |
| `ultimate_run_prg_binary` | **Upload and run a PRG from external sources** — accepts local file path, base64 data, or URL ([details](#-running-programs-remotely)) |
| `ultimate_run_cartridge` | Load and run a cartridge file (.crt) |

### Audio Playback

| Tool | Description |
|------|-------------|
| `ultimate_play_sid` | Play a SID music file (with optional song number) |
| `ultimate_play_mod` | Play an Amiga MOD music file |

### Memory Operations

| Tool | Description |
|------|-------------|
| `ultimate_read_memory` | Read up to 256 bytes from a C64 memory address |
| `ultimate_write_memory` | Write hex data to a C64 memory address |
| `ultimate_write_memory_binary` | Write binary file contents to memory |

### Drive & Disk Management

| Tool | Description |
|------|-------------|
| `ultimate_mount_disk` | Mount a disk image (D64/D71/D81) on drive A-D |
| `ultimate_unmount_disk` | Unmount a disk from a drive |
| `ultimate_turn_drive_on` | Turn on a virtual drive |
| `ultimate_turn_drive_off` | Turn off a virtual drive |
| `ultimate_set_drive_mode` | Set drive type: 1541, 1571, or 1581 |
| `ultimate_load_drive_rom` | Load a custom ROM into a drive |
| `ultimate_create_d64` | Create a new D64 disk image (35 or 40 tracks) |
| `ultimate_create_d71` | Create a new D71 disk image |
| `ultimate_create_d81` | Create a new D81 disk image |
| `ultimate_create_dnp` | Create a new DNP disk image |

### Machine Control

| Tool | Description |
|------|-------------|
| `ultimate_reset_machine` | Perform a C64 reset |
| `ultimate_soft_reset` | Soft reset (load empty program) |
| `ultimate_reboot_device` | Reboot the Ultimate device |
| `ultimate_power_off` | Power off the Ultimate device |
| `ultimate_get_machine_info` | Get machine information and status |
| `ultimate_get_machine_state` | Get current machine state |

### Configuration

| Tool | Description |
|------|-------------|
| `ultimate_get_config_categories` | List all configuration categories |
| `ultimate_get_config_category` | Get settings in a category |
| `ultimate_get_config_item` | Get a specific setting value |
| `ultimate_set_config_item` | Set a configuration value |
| `ultimate_bulk_config_update` | Update multiple settings at once |
| `ultimate_save_config` | Save configuration to flash |
| `ultimate_load_config` | Load configuration from flash |
| `ultimate_reset_config` | Reset to factory defaults |

### File Operations

| Tool | Description |
|------|-------------|
| `ultimate_get_file_info` | Get information about a file on the Ultimate |

### Streaming (Ultimate 64 Only)

| Tool | Description |
|------|-------------|
| `ultimate_start_stream` | Start video, audio, or debug streaming |
| `ultimate_stop_stream` | Stop an active stream |

---

## 📦 Running Programs Remotely

The `ultimate_run_prg_binary` tool is designed to run PRG files that are **not stored on the Ultimate device**. This is essential for hosted deployments where the AI assistant needs to upload and run programs from external sources.

### Three Input Methods

| Parameter | Use Case |
|-----------|----------|
| `prg_data_base64` | AI embeds the PRG as base64 in the request — ideal for small programs or AI-generated code |
| `url` | Server downloads PRG from any HTTP/HTTPS URL — great for hosted program archives |
| `file_path` | Reads from server's local filesystem — for server-side program storage |

**Only one parameter should be provided per call.**

### Example: Base64-Encoded PRG

The AI can encode a compiled PRG program as base64 and send it directly:

```json
{
  "name": "ultimate_run_prg_binary",
  "arguments": {
    "prg_data_base64": "AQgLCJ4ACJ4ACQoAHgoAoCAKgBQKgP8f..."
  }
}
```

This is particularly powerful for AI-generated demos — the AI can:
1. Write 6502 assembly code
2. Compile it (if tools available) or generate machine code directly
3. Encode the resulting PRG as base64
4. Send it to run on the actual C64 hardware

### Example: URL Download

Point to a PRG hosted anywhere on the internet:

```json
{
  "name": "ultimate_run_prg_binary",
  "arguments": {
    "url": "https://csdb.dk/getinternalfile.php/12345/game.prg"
  }
}
```

The MCP server downloads the file and uploads it to the Ultimate device.

### Example: Server-Local File

If the PRG is on the MCP server's filesystem:

```json
{
  "name": "ultimate_run_prg_binary",
  "arguments": {
    "file_path": "/workspace/demos/mydemo.prg"
  }
}
```

> **Note:** For files already on the Ultimate device's storage (USB, SD card), use `ultimate_run_program` instead.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A **Commodore 64 Ultimate** (or Ultimate 64/II+/II+L) on your network
- The Ultimate's REST API must be accessible (enabled by default)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ultimate64-mcp.git
cd ultimate64-mcp/mcp_hosted

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

#### Option 1: Environment Variable (Recommended)

```bash
# Set your Ultimate device's IP address
export C64_HOST="192.168.1.64"

# Start the server
python mcp_ultimate_server.py
```

#### Option 2: Command Line Argument

```bash
python mcp_ultimate_server.py http://192.168.1.64
```

#### Option 3: Dynamic Connection

Start without a configured host and set it later via the `ultimate_set_connection` tool:

```bash
python mcp_ultimate_server.py
# Server starts, then use ultimate_set_connection tool to connect
```

The server runs on `http://0.0.0.0:8000` by default.

---

## 🔌 Transport Modes

### SSE Mode (Default) — For Hosted/Remote Access

The default mode uses **Server-Sent Events (SSE)** for persistent HTTP connections. This is ideal for:

- Hosted deployments (cloud, VPS)
- Web-based AI assistants
- Multi-client scenarios

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sse` | GET | Establish SSE connection, returns session ID |
| `/messages?session_id={id}` | POST | Send JSON-RPC messages |
| `/upload-prg` | POST | Direct PRG upload endpoint (bypasses MCP for large files) |

**SSE Connection Flow:**

1. Client connects to `GET /sse`
2. Server sends initial event with `session_id` and endpoint URL
3. Client sends JSON-RPC requests to `POST /messages?session_id={id}`
4. Responses stream back via SSE

### STDIO Mode — For Local Use

For local MCP clients (like Cursor or Claude Desktop), use STDIO mode:

```bash
python mcp_ultimate_server.py --stdio
# Or with explicit host:
python mcp_ultimate_server.py http://192.168.1.64 --stdio
```

---

## 🐳 Docker Deployment

### Building the Image

```bash
cd mcp_hosted
docker build -t ultimate64-mcp .
```

### Running the Container

```bash
# With environment variable
docker run -p 8000:8000 -e C64_HOST=192.168.1.64 ultimate64-mcp

# With custom port to Ultimate device (in case C64 is behind NAT/port fowards)
docker run -p 8000:8000 -e C64_HOST=http://192.168.1.64:6464 ultimate64-mcp 

# Start without connection (configure later via tool)
docker run -p 8000:8000 ultimate64-mcp
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `C64_HOST` | IP address or URL of your Ultimate device | `192.168.1.64` or `http://myC64.domain.com:6464` |

---

## ⚙️ Client Configuration

### Cursor IDE

Add to your Cursor MCP settings (`.cursor/mcp.json`):

**For SSE (Remote) Mode:**

```json
{
  "mcpServers": {
    "ultimate64-mcp": {
      "transport": {
        "type": "sse",
        "url": "http://your-server-address:8000/sse"
      }
    }
  }
}
```

**For STDIO (Local) Mode:**

```json
{
  "mcpServers": {
    "ultimate64-mcp": {
      "command": "python",
      "args": ["/path/to/mcp_ultimate_server.py", "--stdio"],
      "env": {
        "C64_HOST": "192.168.1.64"
      }
    }
  }
}
```

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "ultimate64-mcp": {
      "command": "python",
      "args": ["/path/to/mcp_ultimate_server.py", "--stdio"],
      "env": {
        "C64_HOST": "192.168.1.64"
      }
    }
  }
}
```

---

## 📡 Direct PRG Upload Endpoint

In addition to the MCP `ultimate_run_prg_binary` tool, the server exposes a direct REST endpoint for uploading PRG files. This is useful for:

- **Large files** (>100KB) where MCP protocol overhead is undesirable
- **Non-MCP clients** that want to upload programs directly
- **Automation scripts** and CI/CD pipelines
- **Web applications** integrating with the Ultimate device

### Endpoint

```
POST /upload-prg
```

### Supported Content Types

**1. Multipart Form Upload** (`multipart/form-data`)

```bash
curl -X POST http://localhost:8000/upload-prg \
  -F "file=@myprogram.prg"
```

**2. Raw Binary Upload** (`application/octet-stream`)

```bash
curl -X POST http://localhost:8000/upload-prg \
  -H "Content-Type: application/octet-stream" \
  --data-binary @myprogram.prg
```

**3. Base64 JSON Upload** (`application/json`)

```bash
curl -X POST http://localhost:8000/upload-prg \
  -H "Content-Type: application/json" \
  -d '{"prg_data_base64": "AQgLCJ4A..."}'
```

### Response

```json
{
  "success": true,
  "message": "Running PRG (1234 bytes)",
  "size_bytes": 1234,
  "response": {"message": "Program started"}
}
```

---

## 🔧 Configuration File

The `config.json` file provides default settings:

```json
{
  "ultimate": {
    "base_url": "http://192.168.1.64:6464",
    "timeout": 30,
    "retry_attempts": 3
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

> Note: Environment variables and command-line arguments take precedence over `config.json`.

---

## 🛠️ API Reference

### JSON-RPC Protocol

The server implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) specification. All communication uses JSON-RPC 2.0.

**Example: List Tools**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Example: Call Tool**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "ultimate_play_sid",
    "arguments": {
      "file": "/Usb0/Music/Commando.sid",
      "song_number": 1
    }
  }
}
```

---

## 🔐 Security Considerations

- The Docker container runs as a non-root user
- Network access is required for the Ultimate device API
- Consider running behind a reverse proxy for public deployments
- Use environment variables for sensitive configuration

---

## 🐛 Troubleshooting

### Connection Issues

1. Verify your Commodore 64 Ultimate is powered on and connected to the network
2. Check the IP address in the Ultimate menu (F2 → Network settings)
3. Ensure the REST API is enabled (it is by default)
4. Test connectivity: `curl http://<C64_HOST>/v1/version`

### "No C64 host configured" Error

This means no connection is set. Either:
- Set the `C64_HOST` environment variable
- Pass the URL as a command-line argument
- Use the `ultimate_set_connection` tool after startup

### Large File Uploads

For PRG files larger than ~100KB, consider:
- Using the `/upload-prg` REST endpoint directly
- Using the `url` parameter in `ultimate_run_prg_binary` to have the server fetch the file

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **[Commodore](https://www.commodore.net)** — For bringing back the Commodore 64 with the official Commodore 64 Ultimate, particular Christian Simpson aka PeriFractic
- **[Gideon Zweijtzer](https://github.com/GideonZ) / [Gideon's Logic](https://ultimate64.com/)** — Creator of the Ultimate 64 mainboard, Ultimate II+, and the entire 1541 Ultimate project. His incredible FPGA engineering powers the Commodore 64 Ultimate and has given the C64 community hardware that bridges vintage computing with modern convenience.
- **[Anthropic](https://anthropic.com/)** — For the Model Context Protocol specification
- **The Commodore 64 community** — Keeping the platform alive since 1982

---

## 🔗 Links

- [Gideon's Logic / Ultimate64.com](https://ultimate64.com/) — Home of the Ultimate hardware
- [1541 Ultimate Project on GitHub](https://github.com/GideonZ/1541ultimate)
- [Ultimate REST API Documentation](https://github.com/GideonZ/1541ultimate/wiki/Ultimate-REST-API)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Commodore International Corporation](https://www.commodore.net)

---

<p align="center">
  <i>Have fun with your C64!</i>
</p>

**Martijn Bosschaart**  
📧 [martijn@runstoprestore.nl](mailto:martijn@runstoprestore.nl)
