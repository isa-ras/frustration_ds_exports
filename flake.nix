{
  description = "Обработка и выгрузка данных с размеченной фрустрацией";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = {nixpkgs, ...}: let
    inherit (nixpkgs) lib;
    forAllSystems = lib.genAttrs lib.systems.flakeExposed;
  in {
    devShells = forAllSystems (
      system: let
        # pkgs = nixpkgs.legacyPackages.${system};
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in {
        default = pkgs.mkShell {
          packages = with pkgs; [
            python314
            uv
            ruff
            ty
            python314Packages.huggingface-hub
          ];

          env = lib.optionalAttrs pkgs.stdenv.isLinux {
            # Python libraries often load native shared objects using dlopen(3).
            # Setting LD_LIBRARY_PATH makes the dynamic library loader aware of libraries without using RPATH for lookup.
            LD_LIBRARY_PATH = lib.makeLibraryPath (pkgs.pythonManylinuxPackages.manylinux1);
          };

          nativeBuildInputs = [
            pkgs.autoPatchelfHook
          ];

          shellHook = ''
            unset PYTHONPATH
            uv sync
            . .venv/bin/activate
          '';
        };
      }
    );
    packages = forAllSystems (
      system: let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
        processDataSource = pkgs.linkFarm "process-data-source" [
          {
            name = "process_data.py";
            path = ./process_data.py;
          }
          {
            name = "datasets";
            path = ./datasets;
          }
        ];
      in {
        process_data = pkgs.writeShellApplication {
          name = "process_data";
          runtimeInputs = [pkgs.uv];
          text = ''
            exec uv run --script ${processDataSource}/process_data.py "$@"
          '';
        };
      }
    );
    formatter = forAllSystems (
      system:
        (import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        }).alejandra
    );
  };
}
