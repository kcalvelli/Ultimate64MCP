# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-alpha] - 2024-12-20

### Added

- Initial alpha release
- 37 tools for controlling the **Commodore 64 Ultimate** (official Commodore product)
- Also compatible with Gideon's Logic products:
  - Ultimate 64 (FPGA-based C64 mainboard)
  - Ultimate II+ (cartridge for original C64/C128)
  - Ultimate II+L (lite version)
- SSE (Server-Sent Events) transport for hosted deployments
- STDIO transport for local MCP clients (Cursor, Claude Desktop)
- Docker containerization with non-root user
- Dynamic connection management via `ultimate_set_connection` tool
- Direct PRG upload endpoint (`/upload-prg`)
- Support for PRG upload via base64 encoding or URL
- Environment variable configuration (`C64_HOST`)

### Tools

#### Connection
- `ultimate_set_connection` - Set device hostname/port
- `ultimate_get_connection` - Get current connection details
- `ultimate_version` - Get REST API version

#### Program Execution
- `ultimate_run_program` - Run program from device filesystem
- `ultimate_load_program` - Load program without running
- `ultimate_run_prg_binary` - Upload and run PRG via path/base64/URL
- `ultimate_run_cartridge` - Run cartridge files

#### Audio
- `ultimate_play_sid` - Play SID files with song selection
- `ultimate_play_mod` - Play Amiga MOD files

#### Memory
- `ultimate_read_memory` - Read C64 memory (up to 256 bytes)
- `ultimate_write_memory` - Write hex data to memory
- `ultimate_write_memory_binary` - Write binary file to memory

#### Drive Management
- `ultimate_mount_disk` - Mount D64/D71/D81 images
- `ultimate_unmount_disk` - Unmount disk from drive
- `ultimate_turn_drive_on` - Enable virtual drive
- `ultimate_turn_drive_off` - Disable virtual drive
- `ultimate_set_drive_mode` - Set drive type (1541/1571/1581)
- `ultimate_load_drive_rom` - Load custom drive ROM
- `ultimate_create_d64` - Create D64 disk image
- `ultimate_create_d71` - Create D71 disk image
- `ultimate_create_d81` - Create D81 disk image
- `ultimate_create_dnp` - Create DNP disk image

#### Machine Control
- `ultimate_reset_machine` - C64 reset
- `ultimate_soft_reset` - Soft reset
- `ultimate_reboot_device` - Reboot Ultimate device
- `ultimate_power_off` - Power off device
- `ultimate_get_machine_info` - Get machine info
- `ultimate_get_machine_state` - Get machine state

#### Configuration
- `ultimate_get_config_categories` - List config categories
- `ultimate_get_config_category` - Get category settings
- `ultimate_get_config_item` - Get specific setting
- `ultimate_set_config_item` - Set configuration value
- `ultimate_bulk_config_update` - Batch update settings
- `ultimate_save_config` - Save to flash
- `ultimate_load_config` - Load from flash
- `ultimate_reset_config` - Factory reset

#### Files
- `ultimate_get_file_info` - Get file information

#### Streaming (U64 only)
- `ultimate_start_stream` - Start video/audio/debug stream
- `ultimate_stop_stream` - Stop stream

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

