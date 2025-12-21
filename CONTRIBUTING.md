# Contributing to Commodore 64 Ultimate MCP Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/ultimate64-mcp.git
   cd ultimate64-mcp/mcp_hosted
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Development

### Running Locally

```bash
# With your Ultimate device
export C64_HOST="192.168.1.64"
python mcp_ultimate_server.py

# In STDIO mode for testing with MCP clients
python mcp_ultimate_server.py --stdio
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write descriptive docstrings for public functions
- Keep functions focused and small

### Adding New Tools

To add a new tool:

1. Add the tool definition in `get_tools()` method of `UltimateHandler`
2. Add the tool handler in `call_tool()` method
3. Update the README.md with the new tool documentation
4. Add an entry to CHANGELOG.md

Example tool definition:

```python
Tool(
    name="ultimate_new_feature",
    description="Description of what the tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Parameter description"
            }
        },
        "required": ["param1"]
    }
)
```

## Pull Request Process

1. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes** and commit:
   ```bash
   git add .
   git commit -m "Add: description of your changes"
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/my-new-feature
   ```

4. **Open a Pull Request** on GitHub

### PR Guidelines

- Provide a clear description of what your PR does
- Reference any related issues
- Update documentation if needed
- Ensure the code runs without errors

## Reporting Bugs

When reporting bugs, please include:

- Your Python version (`python --version`)
- Your device type (Commodore 64 Ultimate, Ultimate 64, Ultimate II+, or Ultimate II+L)
- Firmware version of your Ultimate device
- Steps to reproduce the issue
- Expected vs actual behavior
- Any error messages or logs

## Feature Requests

Feature requests are welcome! Please:

- Check if the feature is already requested
- Describe the use case
- Explain how it would benefit users

## Questions?

Feel free to open an issue for questions or discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

