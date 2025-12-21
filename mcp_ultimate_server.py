#!/usr/bin/env python3
"""
Commodore 64 Ultimate — MCP Server
==================================

A Model Context Protocol (MCP) server for the Commodore 64 Ultimate — the 
official modern Commodore 64 computer.

Primary device:
- Commodore 64 Ultimate: Official Commodore product using Ultimate 64 mainboard

Also compatible with Gideon's Logic products:
- Ultimate 64: The original FPGA-based C64 mainboard
- Ultimate II+: Cartridge for original C64/C128
- Ultimate II+L: Lite version of Ultimate II+

The Ultimate mainboard is designed by Gideon Zweijtzer (https://github.com/GideonZ).

This server provides tools to interact with the Ultimate's REST API,
enabling AI assistants to control the Commodore 64.

Hosted version with SSE (Server-Sent Events) support for remote access.

https://ultimate64.com/
"""

import argparse
import asyncio
import base64
import binascii
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin
import aiohttp
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_c64_host_from_env() -> Optional[str]:
    """Get C64 host URL from environment variable, returns None if not set"""
    host = os.environ.get("C64_HOST")
    if host:
        if not host.startswith("http"):
            host = f"http://{host}"
        return host
    return None  # No default - connection must be set explicitly

class UltimateHandler:
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the Ultimate Handler (Client)
        
        Args:
            base_url: Base URL of the Ultimate device. If None, reads from C64_HOST
                     environment variable. If not set, starts without a connection.
        """
        if base_url is None:
            base_url = get_c64_host_from_env()
        
        self.base_url: Optional[str] = None
        self.api_base: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
        if base_url:
            self.set_base_url(base_url)
        else:
            logger.info("No C64 host configured. Use 'ultimate_set_connection' tool to set connection.")
        
    def set_base_url(self, base_url: str):
        """Update the base URL for the Ultimate device"""
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}"
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/v1"
        logger.info(f"Ultimate device URL set to: {self.base_url}")

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                          data: Optional[Union[Dict, bytes]] = None) -> Dict[str, Any]:
        """Make HTTP request to Ultimate API"""
        if not self.api_base:
            return {"errors": ["No C64 host configured. Use 'ultimate_set_connection' tool to set connection."]}
        url = f"{self.api_base}/{endpoint}"
        
        try:
            # Create a fresh session for each request to avoid connection issues
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, params=params, json=data) as response:
                    if response.status == 204:
                        return {"ok": True}
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if "application/json" in content_type:
                            return await response.json()
                        raw = await response.read()
                        try:
                            return {"data": raw.hex()}
                        except Exception:
                            return {"data": raw.decode(errors="replace")}
                    body = await response.text()
                    return {"errors": [f"HTTP {response.status}: {body}"]}
        except Exception as e:
            return {
                "errors": [f"Request failed: {str(e)}"]
            }
    
    async def get_tools(self) -> list[Tool]:
        """List available tools"""
        tools = [
            Tool(
                name="ultimate_set_connection",
                description="Set the hostname and port of the Ultimate C64 device",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hostname": {
                            "type": "string",
                            "description": "Hostname or IP address (e.g., 192.168.1.64)"
                        },
                        "port": {
                            "type": "integer",
                            "description": "Port number (optional, defaults to 80)"
                        }
                    },
                    "required": ["hostname"]
                }
            ),
            Tool(
                name="ultimate_get_connection",
                description="Get the current connection details for the Ultimate C64 device",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_version",
                description="Get the current version of the Ultimate's REST API",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_play_sid",
                description="Play a SID file on the Ultimate",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "Path to the SID file on the Ultimate"
                        },
                        "song_number": {
                            "type": "integer",
                            "description": "Optional song number to play (default: first song)",
                            "minimum": 1
                        }
                    },
                    "required": ["file"]
                }
            ),
            Tool(
                name="ultimate_play_mod",
                description="Play an Amiga MOD file on the Ultimate",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "Path to the MOD file on the Ultimate"
                        }
                    },
                    "required": ["file"]
                }
            ),
            Tool(
                name="ultimate_load_program",
                description="Load a program into C64 memory (does not run it)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "Path to the program file on the Ultimate"
                        }
                    },
                    "required": ["file"]
                }
            ),
            Tool(
                name="ultimate_run_program",
                description="Load and run a program on the C64",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "Path to the program file on the Ultimate"
                        }
                    },
                    "required": ["file"]
                }
            ),
            Tool(
                name="ultimate_run_prg_binary",
                description="Upload and run a PRG file. Accepts file path, base64-encoded binary data, or URL to download the PRG file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the PRG file to upload and run (if file is on server filesystem)"
                        },
                        "prg_data_base64": {
                            "type": "string",
                            "description": "Base64-encoded PRG file binary data. Use this for large files or when file_path is not accessible."
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to download the PRG file from (HTTP/HTTPS). Useful when the file is hosted remotely."
                        }
                    },
                    "required": []
                }
            ),
            Tool(
                name="ultimate_run_cartridge",
                description="Load and run a cartridge file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "Path to the cartridge file on the Ultimate"
                        }
                    },
                    "required": ["file"]
                }
            ),
            Tool(
                name="ultimate_get_config_categories",
                description="Get all configuration categories",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_get_config_category",
                description="Get configuration items in a specific category",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Configuration category name (supports wildcards)"
                        }
                    },
                    "required": ["category"]
                }
            ),
            Tool(
                name="ultimate_get_config_item",
                description="Get specific configuration item details",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Configuration category name"
                        },
                        "item": {
                            "type": "string",
                            "description": "Configuration item name (supports wildcards)"
                        }
                    },
                    "required": ["category", "item"]
                }
            ),
            Tool(
                name="ultimate_set_config_item",
                description="Set a configuration item value",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Configuration category name"
                        },
                        "item": {
                            "type": "string",
                            "description": "Configuration item name"
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to set"
                        }
                    },
                    "required": ["category", "item", "value"]
                }
            ),
            Tool(
                name="ultimate_mount_disk",
                description="Mount a disk image on a drive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drive": {
                            "type": "string",
                            "description": "Drive identifier (A, B, etc.)",
                            "enum": ["A", "B", "C", "D"]
                        },
                        "file": {
                            "type": "string",
                            "description": "Path to the disk image file"
                        }
                    },
                    "required": ["drive", "file"]
                }
            ),
            Tool(
                name="ultimate_unmount_disk",
                description="Unmount a disk from a drive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drive": {
                            "type": "string",
                            "description": "Drive identifier (A, B, etc.)",
                            "enum": ["A", "B", "C", "D"]
                        }
                    },
                    "required": ["drive"]
                }
            ),
            Tool(
                name="ultimate_turn_drive_on",
                description="Turn on a drive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drive": {
                            "type": "string",
                            "description": "Drive identifier (A, B, etc.)",
                            "enum": ["A", "B", "C", "D"]
                        }
                    },
                    "required": ["drive"]
                }
            ),
            Tool(
                name="ultimate_turn_drive_off",
                description="Turn off a drive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drive": {
                            "type": "string",
                            "description": "Drive identifier (A, B, etc.)",
                            "enum": ["A", "B", "C", "D"]
                        }
                    },
                    "required": ["drive"]
                }
            ),
            Tool(
                name="ultimate_create_d64",
                description="Create a D64 disk image",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path where to create the D64 file"
                        },
                        "tracks": {
                            "type": "integer",
                            "description": "Number of tracks (35 or 40)",
                            "enum": [35, 40]
                        },
                        "diskname": {
                            "type": "string",
                            "description": "Optional disk name for the header"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="ultimate_create_d71",
                description="Create a D71 disk image",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path where to create the D71 file"
                        },
                        "diskname": {
                            "type": "string",
                            "description": "Optional disk name for the header"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="ultimate_create_d81",
                description="Create a D81 disk image",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path where to create the D81 file"
                        },
                        "diskname": {
                            "type": "string",
                            "description": "Optional disk name for the header"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="ultimate_save_config",
                description="Save current configuration to flash memory",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_load_config",
                description="Load configuration from flash memory",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_reset_config",
                description="Reset configuration to factory defaults",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_read_memory",
                description="Read memory from a specific address on the C64",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "Memory address in hexadecimal format (e.g., 'C000', 'D020')"
                        },
                        "length": {
                            "type": "integer",
                            "description": "Number of bytes to read (default: 256, max: 256)",
                            "minimum": 1,
                            "maximum": 256
                        }
                    },
                    "required": ["address"]
                }
            ),
            Tool(
                name="ultimate_write_memory",
                description="Write data to a specific memory address on the C64 using hex string (PUT method)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "Memory address in hexadecimal format (e.g., 'C000', 'D020')"
                        },
                        "data": {
                            "type": "string",
                            "description": "Data to write in hexadecimal format (e.g., '05' for single byte, '0504' for two bytes)"
                        }
                    },
                    "required": ["address", "data"]
                }
            ),
            Tool(
                name="ultimate_write_memory_binary",
                description="Write binary data from a file to a specific memory address on the C64 (POST method with binary body)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "address": {
                            "type": "string",
                            "description": "Memory address in hexadecimal format (e.g., 'C000', 'D020')"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to the binary file to write to memory"
                        }
                    },
                    "required": ["address", "file_path"]
                }
            ),
            Tool(
                name="ultimate_reset_machine",
                description="Reset the C64 machine (soft reset)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_power_off",
                description="Power off the Ultimate device (hardware power off)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_get_machine_info",
                description="Get machine information and status",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_get_machine_state",
                description="Get current machine state",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_soft_reset",
                description="Perform a soft reset (load empty program)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_reboot_device",
                description="Reboot the Ultimate device",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="ultimate_set_drive_mode",
                description="Set drive mode (1541, 1571, 1581)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drive": {
                            "type": "string",
                            "description": "Drive identifier (A, B, etc.)",
                            "enum": ["A", "B", "C", "D"]
                        },
                        "mode": {
                            "type": "string",
                            "description": "Drive mode",
                            "enum": ["1541", "1571", "1581"]
                        }
                    },
                    "required": ["drive", "mode"]
                }
            ),
            Tool(
                name="ultimate_load_drive_rom",
                description="Load a custom ROM into a drive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drive": {
                            "type": "string",
                            "description": "Drive identifier (A, B, etc.)",
                            "enum": ["A", "B", "C", "D"]
                        },
                        "file": {
                            "type": "string",
                            "description": "Path to the ROM file on the Ultimate"
                        }
                    },
                    "required": ["drive", "file"]
                }
            ),
            Tool(
                name="ultimate_get_file_info",
                description="Get information about a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file on the Ultimate"
                        }
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="ultimate_create_dnp",
                description="Create a DNP disk image",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path where to create the DNP file"
                        },
                        "tracks": {
                            "type": "integer",
                            "description": "Number of tracks (required, max 255)",
                            "minimum": 1,
                            "maximum": 255
                        },
                        "diskname": {
                            "type": "string",
                            "description": "Optional disk name for the header"
                        }
                    },
                    "required": ["path", "tracks"]
                }
            ),
            Tool(
                name="ultimate_start_stream",
                description="Start a data stream (U64 only: video, audio, debug)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stream": {
                            "type": "string",
                            "description": "Stream type",
                            "enum": ["video", "audio", "debug"]
                        },
                        "ip": {
                            "type": "string",
                            "description": "IP address to send stream to (with optional port, e.g., '192.168.1.100:6789')"
                        }
                    },
                    "required": ["stream", "ip"]
                }
            ),
            Tool(
                name="ultimate_stop_stream",
                description="Stop a data stream (U64 only)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stream": {
                            "type": "string",
                            "description": "Stream type",
                            "enum": ["video", "audio", "debug"]
                        }
                    },
                    "required": ["stream"]
                }
            ),
            Tool(
                name="ultimate_bulk_config_update",
                description="Update multiple configuration settings at once",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "config": {
                            "type": "object",
                            "description": "Configuration object with categories and settings"
                        }
                    },
                    "required": ["config"]
                }
            ),
        ]
        return tools
    
    async def call_tool(self, tool_name: str, arguments: dict) -> CallToolResult:
        """Handle tool calls"""
        try:
            if tool_name == "ultimate_set_connection":
                hostname = arguments["hostname"]
                port = arguments.get("port")
                if port:
                    url = f"http://{hostname}:{port}"
                else:
                    url = f"http://{hostname}"
                self.set_base_url(url)
                result = {"ok": True, "message": f"Connection set to {self.base_url}"}
                content = json.dumps(result, indent=2)
                return CallToolResult(content=[TextContent(type="text", text=content)])
                
            elif tool_name == "ultimate_get_connection":
                result = {"base_url": self.base_url}
                content = json.dumps(result, indent=2)
                return CallToolResult(content=[TextContent(type="text", text=content)])

            elif tool_name == "ultimate_version":
                result = await self.make_request("GET", "version")
                
            elif tool_name == "ultimate_play_sid":
                file_path = arguments["file"]
                song_number = arguments.get("song_number")
                
                # If a local file exists, upload and play via POST binary
                try:
                    import os
                    mapped_path = file_path
                    if os.path.exists('/workspace'):
                        if mapped_path.startswith('/Users/martijn/UltimateMCP'):
                            mapped_path = mapped_path.replace('/Users/martijn/UltimateMCP', '/workspace')
                        elif not mapped_path.startswith('/'):
                            mapped_path = os.path.join('/workspace', mapped_path)
                    if os.path.exists(mapped_path):
                        url = f"{self.api_base}/runners:sidplay"
                        params = {}
                        if song_number:
                            params["songnr"] = song_number
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url,
                                                    params=params,
                                                    data=open(mapped_path, 'rb'),
                                                    headers={'Content-Type': 'application/octet-stream'}) as response:
                                if response.status in (200, 204):
                                    try:
                                        result = await response.json()
                                    except:
                                        result = {"ok": True}
                                else:
                                    body = await response.text()
                                    result = {"errors": [f"HTTP {response.status}: {body}"]}
                    else:
                        # Fall back to device-side path
                        params = {"file": file_path}
                        if song_number:
                            params["songnr"] = song_number
                        result = await self.make_request("PUT", "runners:sidplay", params=params)
                except Exception as e:
                    result = {"errors": [f"Failed to play SID: {str(e)}"]}
                
            elif tool_name == "ultimate_play_mod":
                file_path = arguments["file"]
                result = await self.make_request("PUT", "runners:modplay", params={"file": file_path})
                
            elif tool_name == "ultimate_load_program":
                file_path = arguments["file"]
                result = await self.make_request("PUT", "runners:load_prg", params={"file": file_path})
                
            elif tool_name == "ultimate_run_program":
                file_path = arguments["file"]
                result = await self.make_request("PUT", "runners:run_prg", params={"file": file_path})
                
            elif tool_name == "ultimate_run_prg_binary":
                prg_data = None
                source_info = ""
                
                try:
                    import os
                    import urllib.parse
                    
                    # Priority 1: Check if binary data is provided as base64
                    if "prg_data_base64" in arguments and arguments["prg_data_base64"]:
                        base64_str = arguments["prg_data_base64"]
                        logger.info(f"Received PRG data as base64: {len(base64_str)} characters")
                        
                        # Handle base64 string - strip whitespace and validate
                        base64_str = base64_str.strip()
                        if not base64_str:
                            result = {"errors": ["Base64 data is empty"]}
                            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                        
                        try:
                            # Decode base64 data
                            prg_data = base64.b64decode(base64_str, validate=True)
                            source_info = f"base64 data ({len(prg_data)} bytes)"
                            logger.info(f"Successfully decoded base64: {len(prg_data)} bytes")
                        except binascii.Error as e:
                            result = {"errors": [f"Invalid base64 data: {str(e)}. Make sure the base64 string is complete and properly encoded."]}
                            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                        except Exception as e:
                            result = {"errors": [f"Failed to decode base64 data: {str(e)}"]}
                            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                    
                    # Priority 2: Check if a URL is provided to download the PRG file
                    elif "url" in arguments and arguments["url"]:
                        download_url = arguments["url"]
                        logger.info(f"Downloading PRG file from URL: {download_url}")
                        
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                                    if response.status == 200:
                                        prg_data = await response.read()
                                        source_info = f"URL {download_url} ({len(prg_data)} bytes)"
                                        logger.info(f"Successfully downloaded PRG file: {len(prg_data)} bytes")
                                    else:
                                        result = {"errors": [f"Failed to download PRG file from URL: HTTP {response.status}"]}
                                        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                        except aiohttp.ClientError as e:
                            result = {"errors": [f"Failed to download PRG file from URL: {str(e)}"]}
                            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                        except Exception as e:
                            result = {"errors": [f"Error downloading PRG file: {str(e)}"]}
                            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                    
                    # Priority 3: Try to read from file path
                    elif "file_path" in arguments and arguments["file_path"]:
                        file_path = arguments["file_path"]
                        original_path = file_path
                        
                        # Try multiple possible mount points for Docker containers
                        possible_mounts = ['/workspace', '/app', '/mnt', '/data']
                        mapped_paths = [file_path]  # Try original path first
                        
                        # If it's a host path, try to map it to container paths
                        if file_path.startswith('/Users/'):
                            for mount in possible_mounts:
                                if os.path.exists(mount):
                                    # Try mapping the path
                                    if '/Users/martijn/UltimateMCP' in file_path:
                                        mapped = file_path.replace('/Users/martijn/UltimateMCP', mount)
                                        mapped_paths.append(mapped)
                                    # Also try just appending the relative part
                                    rel_path = os.path.basename(file_path)
                                    mapped_paths.append(os.path.join(mount, rel_path))
                        
                        # Also try relative paths in common locations
                        if not file_path.startswith('/'):
                            for mount in possible_mounts:
                                if os.path.exists(mount):
                                    mapped_paths.append(os.path.join(mount, file_path))
                        
                        # Try each possible path until one works
                        prg_data = None
                        for try_path in mapped_paths:
                            logger.info(f"Trying to open file: {try_path}")
                            if os.path.exists(try_path):
                                try:
                                    with open(try_path, 'rb') as f:
                                        prg_data = f.read()
                                    source_info = f"file {try_path} ({len(prg_data)} bytes)"
                                    logger.info(f"Successfully read file from: {try_path}")
                                    break
                                except Exception as e:
                                    logger.warning(f"Failed to read {try_path}: {e}")
                                    continue
                        
                        if prg_data is None:
                            error_msg = f"File not found: {original_path}. Tried paths: {', '.join(mapped_paths[:5])}"
                            error_msg += ". Consider using 'prg_data_base64' or 'url' parameter instead."
                            result = {"errors": [error_msg]}
                            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                    else:
                        result = {"errors": ["One of 'file_path', 'prg_data_base64', or 'url' must be provided"]}
                        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                    
                    # Validate PRG data
                    if prg_data is None or len(prg_data) == 0:
                        result = {"errors": ["No PRG data provided or data is empty"]}
                        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                    
                    # Validate minimum PRG file size (should have at least load address)
                    if len(prg_data) < 2:
                        result = {"errors": ["PRG file is too small (must be at least 2 bytes for load address)"]}
                        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])
                    
                    logger.info(f"Uploading PRG file to Ultimate: {len(prg_data)} bytes")
                    
                    # Upload and run the PRG file
                    url = f"{self.api_base}/runners:run_prg"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url, 
                            data=prg_data, 
                            headers={'Content-Type': 'application/octet-stream'},
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            if response.status == 200:
                                try:
                                    response_data = await response.json()
                                except:
                                    response_data = {"message": "Program started"}
                                result = {
                                    "success": True,
                                    "message": f"Running PRG from {source_info}",
                                    "size_bytes": len(prg_data),
                                    "response": response_data
                                }
                            else:
                                body = await response.text()
                                result = {"errors": [f"Failed to run PRG: HTTP {response.status}: {body}"]}
                except binascii.Error as e:
                    result = {"errors": [f"Invalid base64 data: {str(e)}"]}
                except Exception as e:
                    result = {"errors": [f"Failed to process PRG file: {str(e)}"]}
                    logger.error(f"Error in ultimate_run_prg_binary: {e}", exc_info=True)
                
            elif tool_name == "ultimate_run_cartridge":
                file_path = arguments["file"]
                result = await self.make_request("PUT", "runners:run_crt", params={"file": file_path})
                
            elif tool_name == "ultimate_get_config_categories":
                result = await self.make_request("GET", "configs")
                
            elif tool_name == "ultimate_get_config_category":
                category = arguments["category"]
                result = await self.make_request("GET", f"configs/{category}")
                
            elif tool_name == "ultimate_get_config_item":
                category = arguments["category"]
                item = arguments["item"]
                result = await self.make_request("GET", f"configs/{category}/{item}")
                
            elif tool_name == "ultimate_set_config_item":
                category = arguments["category"]
                item = arguments["item"]
                value = arguments["value"]
                result = await self.make_request("PUT", f"configs/{category}/{item}", params={"value": value})
                
            elif tool_name == "ultimate_mount_disk":
                drive = arguments["drive"]
                file_path = arguments["file"]
                result = await self.make_request("PUT", f"drives/{drive}:mount", params={"image": file_path})
                
            elif tool_name == "ultimate_unmount_disk":
                drive = arguments["drive"]
                result = await self.make_request("PUT", f"drives/{drive}:remove")
                
            elif tool_name == "ultimate_turn_drive_on":
                drive = arguments["drive"]
                result = await self.make_request("PUT", f"drives/{drive}:on")
                
            elif tool_name == "ultimate_turn_drive_off":
                drive = arguments["drive"]
                result = await self.make_request("PUT", f"drives/{drive}:off")
                
            elif tool_name == "ultimate_create_d64":
                path = arguments["path"]
                params = {}
                if "tracks" in arguments:
                    params["tracks"] = arguments["tracks"]
                if "diskname" in arguments:
                    params["diskname"] = arguments["diskname"]
                result = await self.make_request("PUT", f"files/{path}:create_d64", params=params)
                
            elif tool_name == "ultimate_create_d71":
                path = arguments["path"]
                params = {}
                if "diskname" in arguments:
                    params["diskname"] = arguments["diskname"]
                result = await self.make_request("PUT", f"files/{path}:create_d71", params=params)
                
            elif tool_name == "ultimate_create_d81":
                path = arguments["path"]
                params = {}
                if "diskname" in arguments:
                    params["diskname"] = arguments["diskname"]
                result = await self.make_request("PUT", f"files/{path}:create_d81", params=params)
                
            elif tool_name == "ultimate_save_config":
                result = await self.make_request("PUT", "configs:save_to_flash")
                
            elif tool_name == "ultimate_load_config":
                result = await self.make_request("PUT", "configs:load_from_flash")
                
            elif tool_name == "ultimate_reset_config":
                result = await self.make_request("PUT", "configs:reset_to_default")
                
            elif tool_name == "ultimate_read_memory":
                address = arguments["address"]
                length = arguments.get("length", 256)
                result = await self.make_request("GET", "machine:readmem", params={
                    "address": address,
                    "length": length
                })
                
            elif tool_name == "ultimate_write_memory":
                address = arguments["address"]
                data = arguments["data"]
                result = await self.make_request("PUT", "machine:writemem", params={
                    "address": address,
                    "data": data
                })
                
            elif tool_name == "ultimate_write_memory_binary":
                address = arguments["address"]
                file_path = arguments["file_path"]
                try:
                    import os
                    if os.path.exists('/workspace'):
                        if file_path.startswith('/Users/martijn/UltimateMCP'):
                            file_path = file_path.replace('/Users/martijn/UltimateMCP', '/workspace')
                        elif not file_path.startswith('/'):
                            file_path = os.path.join('/workspace', file_path)
                    with open(file_path, 'rb') as f:
                        binary_data = f.read()
                    url = f"{self.api_base}/machine:writemem"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, 
                                              params={"address": address},
                                              data=binary_data,
                                              headers={'Content-Type': 'application/octet-stream'}) as response:
                            if response.status == 204:
                                result = {"ok": True, "message": f"Successfully wrote {len(binary_data)} bytes to address ${address}"}
                            elif response.status == 200:
                                try:
                                    result = await response.json()
                                    result["message"] = f"Successfully wrote {len(binary_data)} bytes to address ${address}"
                                except:
                                    result = {"ok": True, "message": f"Successfully wrote {len(binary_data)} bytes to address ${address}"}
                            else:
                                body = await response.text()
                                result = {"errors": [f"HTTP {response.status}: {body}"]}
                except Exception as e:
                    result = {"errors": [f"Failed to write binary data from {file_path}: {str(e)}"]}
                
            elif tool_name == "ultimate_reset_machine":
                result = await self.make_request("PUT", "machine:reset")
                
            elif tool_name == "ultimate_power_off":
                result = await self.make_request("PUT", "machine:poweroff")
                
            elif tool_name == "ultimate_get_machine_info":
                result = await self.make_request("GET", "machine:info")
                
            elif tool_name == "ultimate_get_machine_state":
                result = await self.make_request("GET", "machine:state")
                
            elif tool_name == "ultimate_soft_reset":
                result = await self.make_request("PUT", "runners:load_prg", params={"file": ""})
                
            elif tool_name == "ultimate_reboot_device":
                result = await self.make_request("PUT", "machine:reboot")
                
            elif tool_name == "ultimate_set_drive_mode":
                drive = arguments["drive"]
                mode = arguments["mode"]
                result = await self.make_request("PUT", f"drives/{drive}:set_mode", params={"mode": mode})
                
            elif tool_name == "ultimate_load_drive_rom":
                drive = arguments["drive"]
                file_path = arguments["file"]
                result = await self.make_request("PUT", f"drives/{drive}:load_rom", params={"file": file_path})
                
            elif tool_name == "ultimate_get_file_info":
                path = arguments["path"]
                result = await self.make_request("GET", f"files/{path}:info")
                
            elif tool_name == "ultimate_create_dnp":
                path = arguments["path"]
                tracks = arguments["tracks"]
                params = {"tracks": tracks}
                if "diskname" in arguments:
                    params["diskname"] = arguments["diskname"]
                result = await self.make_request("PUT", f"files/{path}:create_dnp", params=params)
                
            elif tool_name == "ultimate_start_stream":
                stream = arguments["stream"]
                ip = arguments["ip"]
                result = await self.make_request("PUT", f"streams/{stream}:start", params={"ip": ip})
                
            elif tool_name == "ultimate_stop_stream":
                stream = arguments["stream"]
                result = await self.make_request("PUT", f"streams/{stream}:stop")
                
            elif tool_name == "ultimate_bulk_config_update":
                config = arguments["config"]
                result = await self.make_request("POST", "configs", data=config)
                
            else:
                result = {"errors": [f"Unknown tool: {tool_name}"]}
            
            if "errors" in result and result["errors"]:
                content = f"Errors: {', '.join(result['errors'])}"
            else:
                result_copy = {k: v for k, v in result.items() if k != "errors"}
                content = json.dumps(result_copy, indent=2)
            
            return CallToolResult(
                content=[TextContent(type="text", text=content)]
            )
            
        except Exception as e:
            logger.error(f"Error in tool {tool_name}: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")]
            )
    
def create_mcp_server(handler: UltimateHandler) -> Server:
    """Create a new MCP server instance using the shared handler"""
    server = Server("ultimate64-mcp")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return await handler.get_tools()

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
        from mcp.types import CallToolRequest, CallToolRequestParams
        # Note: We don't actually need to construct the request object if we just call the handler method directly
        # but keeping consistency
        return (await handler.call_tool(name, arguments)).content

    return server

# --- SSE Support ---

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
import anyio
from mcp.server.sse import SseServerTransport

class WebServer:
    def __init__(self, handler: UltimateHandler):
        self.handler = handler
        self.sessions: Dict[str, Any] = {}

    async def handle_sse(self, request):
        """Handle SSE connection"""
        import uuid
        
        session_id = request.query_params.get("session_id", str(uuid.uuid4()))
        logger.info(f"New SSE connection: {session_id}")
        
        # Create a fresh server instance for this session
        server_instance = create_mcp_server(self.handler)
        
        # Use MCP's SSE transport if available, otherwise create custom transport
        try:
            # Try using MCP's built-in SSE support if available
            from mcp.server.sse import sse_handler
            return await sse_handler(server_instance, request)
        except ImportError:
            # Fallback to manual SSE implementation
            pass
        
        # Manual SSE implementation
        read_stream_send, read_stream_recv = anyio.create_memory_object_stream[str](100)
        write_stream_send, write_stream_recv = anyio.create_memory_object_stream[str](100)
        
        self.sessions[session_id] = {
            'read_send': read_stream_send,
            'write_recv': write_stream_recv,
            'server': server_instance
        }

        async def process_messages():
            """Process incoming messages from the read stream"""
            # Get client IP address from request (available via closure)
            client_ip = request.client.host if hasattr(request, 'client') else "unknown"
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            
            try:
                async for message_line in read_stream_recv:
                    if not message_line or not message_line.strip():
                        continue
                    
                    try:
                        # Parse JSON-RPC message
                        message_data = json.loads(message_line.strip())
                        
                        # Handle different message types
                        method = message_data.get("method")
                        msg_id = message_data.get("id")
                        
                        # Log incoming message
                        if method:
                            logger.info(f"Message from {client_ip}: method={method}, id={msg_id}")
                            if method == "tools/call":
                                params = message_data.get("params", {})
                                tool_name = params.get("name", "unknown")
                                arguments = params.get("arguments", {})
                                logger.info(f"Tool call from {client_ip}: {tool_name}")
                                # Log payload (truncate if too large)
                                payload_str = json.dumps(arguments, indent=2)
                                if len(payload_str) > 1000:
                                    logger.info(f"Tool call payload (truncated): {payload_str[:1000]}...")
                                else:
                                    logger.info(f"Tool call payload: {payload_str}")
                        
                        if method == "initialize":
                            # Send initialize response
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "result": {
                                    "protocolVersion": "2024-11-05",
                                    "capabilities": {
                           "tools": {}
                                    },
                                    "serverInfo": {
                                        "name": "ultimate64-mcp-sse",
                                        "version": "1.0.0"
                                    }
                                }
                            }
                            await write_stream_send.send(json.dumps(response) + '\n')
                            
                        elif method == "tools/list":
                            # Get tools from handler
                            tools = await self.handler.get_tools()
                            # Convert tools to dict format
                            tools_dict = []
                            for tool in tools:
                                tools_dict.append({
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": tool.inputSchema
                                })
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "result": {
                                    "tools": tools_dict
                                }
                            }
                            await write_stream_send.send(json.dumps(response) + '\n')
                            
                        elif method == "tools/call":
                            # Handle tool call
                            params = message_data.get("params", {})
                            tool_name = params.get("name")
                            arguments = params.get("arguments", {})
                            
                            # Logging already done in process_messages above
                            try:
                                result = await self.handler.call_tool(tool_name, arguments)
                                # Convert result to response format
                                content = []
                                for item in result.content:
                                    if hasattr(item, "text"):
                                        content.append({"type": "text", "text": item.text})
                                    else:
                                        content.append({"type": "text", "text": str(item)})
                                
                                response = {
                                    "jsonrpc": "2.0",
                                    "id": msg_id,
                                    "result": {
                                        "content": content
                                    }
                                }
                            except Exception as e:
                                response = {
                                    "jsonrpc": "2.0",
                                    "id": msg_id,
                                    "error": {
                                        "code": -32603,
                                        "message": f"Internal error: {str(e)}"
                                    }
                                }
                            
                            await write_stream_send.send(json.dumps(response) + '\n')
                            
                        elif method and method.startswith("notifications/"):
                            # Handle notifications (no response needed)
                            pass
                            
                        else:
                            # Unknown method
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "error": {
                                    "code": -32601,
                                    "message": f"Method not found: {method}"
                                }
                            }
                            await write_stream_send.send(json.dumps(response) + '\n')
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                import traceback
                logger.error(traceback.format_exc())
            finally:
                logger.info(f"Message processing ended for session: {session_id}")
                if session_id in self.sessions:
                    del self.sessions[session_id]

        async def sse_generator():
            yield {"event": "endpoint", "data": f"/messages?session_id={session_id}"}
            
            async with anyio.create_task_group() as tg:
                tg.start_soon(process_messages)
                
                async for message in write_stream_recv:
                    # Messages are JSON strings
                    if isinstance(message, str):
                        # Remove trailing newline if present
                        data = message.rstrip('\n')
                    else:
                        data = json.dumps(message)
                    yield {"event": "message", "data": data}

        return EventSourceResponse(sse_generator())

    async def handle_messages(self, request):
        """Handle incoming messages"""
        session_id = request.query_params.get("session_id")
        if not session_id:
            return JSONResponse({"error": "Missing session_id query parameter"}, status_code=400)
            
        if session_id not in self.sessions:
            return JSONResponse({"error": "Session not found or closed"}, status_code=404)
            
        try:
            message_data = await request.json()
            
            # Validate it's a valid JSON-RPC message structure
            if not isinstance(message_data, dict):
                return JSONResponse({"error": "Message must be a JSON object"}, status_code=400)
            
            if "jsonrpc" not in message_data:
                return JSONResponse({"error": "Missing jsonrpc field"}, status_code=400)
            
            # Send the raw message data as JSON string to the stream
            # The MCP server expects newline-terminated JSON strings (like stdin/stdout)
            message_json = json.dumps(message_data) + '\n'
            await self.sessions[session_id]['read_send'].send(message_json)
            return JSONResponse({"status": "accepted"})
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return JSONResponse({"error": str(e)}, status_code=500)

    async def handle_upload_prg(self, request):
        """Handle direct PRG file upload - bypasses MCP protocol for large files"""
        try:
            # Get client IP address
            client_ip = request.client.host if hasattr(request, 'client') else "unknown"
            # Check for forwarded IP (if behind proxy)
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            
            # Accept either multipart/form-data or raw binary
            content_type = request.headers.get("content-type", "")
            
            logger.info(f"PRG upload request from {client_ip}, Content-Type: {content_type}")
            
            if "multipart/form-data" in content_type:
                form = await request.form()
                if "file" not in form:
                    return JSONResponse({"error": "Missing 'file' field"}, status_code=400)
                file_item = form["file"]
                prg_data = await file_item.read()
            elif "application/octet-stream" in content_type or "application/x-binary" in content_type:
                prg_data = await request.body()
            elif "application/json" in content_type:
                # Accept base64 in JSON
                data = await request.json()
                if "prg_data_base64" in data:
                    prg_data = base64.b64decode(data["prg_data_base64"])
                else:
                    return JSONResponse({"error": "Missing 'prg_data_base64' field"}, status_code=400)
            else:
                return JSONResponse({"error": "Unsupported content type. Use multipart/form-data, application/octet-stream, or application/json with base64"}, status_code=400)
            
            if not prg_data or len(prg_data) == 0:
                return JSONResponse({"error": "No PRG data provided"}, status_code=400)
            
            # Log payload info (first few bytes for binary, or full data for small JSON)
            load_addr = prg_data[0] | (prg_data[1] << 8) if len(prg_data) >= 2 else 0
            logger.info(f"PRG upload payload from {client_ip}: {len(prg_data)} bytes, load address: 0x{load_addr:04X}")
            if len(prg_data) <= 1000:  # Log full payload if small
                logger.debug(f"Full payload (hex): {prg_data.hex()[:200]}...")
            
            # Check if connection is configured
            if not self.handler.api_base:
                return JSONResponse({
                    "success": False,
                    "error": "No C64 host configured. Use 'ultimate_set_connection' tool to set connection."
                }, status_code=400)
            
            # Upload and run the PRG file directly
            url = f"{self.handler.api_base}/runners:run_prg"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=prg_data, headers={'Content-Type': 'application/octet-stream'}) as response:
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                        except:
                            response_data = {"message": "Program started"}
                        return JSONResponse({
                            "success": True,
                            "message": f"Running PRG ({len(prg_data)} bytes)",
                            "size_bytes": len(prg_data),
                            "response": response_data
                        })
                    else:
                        body = await response.text()
                        return JSONResponse({
                            "success": False,
                            "error": f"Failed to run PRG: HTTP {response.status}",
                            "details": body
                        }, status_code=response.status)
                        
        except base64.binascii.Error as e:
            return JSONResponse({"error": f"Invalid base64 data: {str(e)}"}, status_code=400)
        except Exception as e:
            logger.error(f"Error in handle_upload_prg: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

def create_app():
    """Create Starlette application"""
    # UltimateHandler will read from environment variable automatically
    handler = UltimateHandler()
    web_server = WebServer(handler)
    
    routes = [
        Route("/sse", endpoint=web_server.handle_sse, methods=["GET"]),
        Route("/messages", endpoint=web_server.handle_messages, methods=["POST"]),
        Route("/upload-prg", endpoint=web_server.handle_upload_prg, methods=["POST"])
    ]
    
    return Starlette(routes=routes)

if __name__ == "__main__":
    # Get default URL from environment variable (may be None)
    default_url = get_c64_host_from_env()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", help="Ultimate device URL (overrides C64_HOST env var)", default=default_url)
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (default is web)")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    parser.add_argument("--host", default="0.0.0.0", help="Web server host")
    
    args = parser.parse_args()
    
    if args.stdio:
        handler = UltimateHandler(args.url)
        server = create_mcp_server(handler)
        
        async def run_stdio():
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream, 
                    write_stream, 
                    InitializationOptions(
                        server_name="ultimate64-mcp",
                        server_version="1.0.0",
                        capabilities={"tools": {}}
                    )
                )
        asyncio.run(run_stdio())
    else:
        # If URL is provided via command line, set it in environment for create_app to use
        if args.url and args.url != default_url:
            os.environ["C64_HOST"] = args.url
        elif args.url and not default_url:
            # URL provided but no env var was set
            os.environ["C64_HOST"] = args.url
        uvicorn.run(create_app, host=args.host, port=args.port, factory=True)
