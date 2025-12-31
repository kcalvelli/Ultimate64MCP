{
  description = "MCP server for Commodore 64 Ultimate control";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Override pydantic-extra-types to skip tests (failing on 2025-12-31 due to date-sensitive test)
        python311 = pkgs.python311.override {
          packageOverrides = self: super: {
            pydantic-extra-types = super.pydantic-extra-types.overridePythonAttrs (old: {
              doCheck = false;
            });
          };
        };

        # Build the MCP Python SDK from PyPI
        # This package is not in nixpkgs yet, so we build it here
        # Use wheel format to avoid build dependencies
        python-mcp = python311.pkgs.buildPythonPackage rec {
          pname = "mcp";
          version = "1.25.0";
          format = "wheel";

          src = python311.pkgs.fetchPypi {
            inherit pname version format;
            dist = "py3";
            python = "py3";
            hash = "sha256-s3w4FEpmat0IYmFMx57Cdul9cqqMom1iKBjU4ni5cho=";
          };

          propagatedBuildInputs = with python311.pkgs; [
            anyio
            httpx
            httpx-sse
            jsonschema
            pydantic
            pydantic-settings
            pyjwt
            python-multipart
            sse-starlette
            starlette
            typing-extensions
            typing-inspection
            uvicorn
          ];

          # Skip tests as they may require network access
          doCheck = false;

          meta = with pkgs.lib; {
            description = "Python implementation of the Model Context Protocol (MCP)";
            homepage = "https://github.com/modelcontextprotocol/python-sdk";
            license = licenses.mit;
          };
        };

        ultimate64-mcp = python311.pkgs.buildPythonApplication {
          pname = "ultimate64-mcp";
          version = "1.0.0";

          src = ./.;

          format = "other";

          propagatedBuildInputs = with python311.pkgs; [
            python-mcp
            aiohttp
            uvicorn
            starlette
            sse-starlette
            anyio
          ];

          nativeBuildInputs = [ pkgs.makeWrapper ];

          buildPhase = ''
            # No build needed for pure Python
          '';

          installPhase = ''
            mkdir -p $out/bin $out/lib/ultimate64-mcp
            cp mcp_ultimate_server.py $out/lib/ultimate64-mcp/

            makeWrapper ${python311.withPackages (ps: [
              python-mcp
              ps.aiohttp
              ps.uvicorn
              ps.starlette
              ps.sse-starlette
              ps.anyio
              ps.httpx-sse
              ps.pydantic-settings
            ])}/bin/python3 $out/bin/mcp-ultimate \
              --add-flags "$out/lib/ultimate64-mcp/mcp_ultimate_server.py"
          '';

          doCheck = false;

          meta = with pkgs.lib; {
            description = "MCP server for Commodore 64 Ultimate control";
            homepage = "https://github.com/Martijn-DevRev/Ultimate64MCP";
            license = licenses.mit;
            maintainers = [ ];
            platforms = platforms.all;
          };
        };

      in {
        packages = {
          default = ultimate64-mcp;
          ultimate64-mcp = ultimate64-mcp;
        };

        apps = {
          default = {
            type = "app";
            program = "${ultimate64-mcp}/bin/mcp-ultimate";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            (python311.withPackages (ps: [
              python-mcp
              ps.aiohttp
              ps.uvicorn
              ps.starlette
              ps.sse-starlette
              ps.anyio
              ps.httpx-sse
              ps.pydantic-settings
              ps.python-lsp-server
            ]))
          ];

          shellHook = ''
            echo "Ultimate 64 MCP Server Development Environment"
            echo "Python: $(python3 --version)"
            echo ""
            echo "Commands:"
            echo "  python3 mcp_ultimate_server.py --help"
            echo "  python3 mcp_ultimate_server.py --stdio"
          '';
        };
      }
    );
}
