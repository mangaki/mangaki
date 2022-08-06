{
  description = "Mangaki";

  # Nixpkgs / NixOS version to use.
  inputs.nixpkgs = { type = "github"; owner = "NixOS"; repo = "nixpkgs"; ref = "22.05"; };

  # Poetry2nix version to use
  inputs.poetry2nix = { type = "github"; owner = "nix-community"; repo = "poetry2nix"; ref = "1.31.0"; };

  # Flake compatability shim
  inputs.flake-compat = { type = "github"; owner = "edolstra"; repo = "flake-compat"; flake = false; };

  outputs = { self, nixpkgs, poetry2nix, ... }@inputs:
    let
      # System types to support.
      supportedSystems = [ "x86_64-linux" ];

      # Helper function to generate an attrset '{ x86_64-linux = f "x86_64-linux"; ... }'.
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems (system: f system);

      # Nixpkgs instantiated for supported system types.
      nixpkgsFor = forAllSystems (system: import nixpkgs { inherit system; overlays = [ self.overlay ]; });

    in
    {

      # A Nixpkgs overlay.
      overlay = final: prev:
        with final;
        (poetry2nix.overlay final prev) //
        {

          lapack = prev.lapack.override { lapackProvider = final.mkl; };
          blas = prev.blas.override { blasProvider = final.mkl; };

          mangaki = (callPackage ./nix/pkgs/mangaki { }).overrideAttrs (oldAttrs:
            {
              # Can't add anything to `passthru` from poetry2nix
              passthru = (oldAttrs.passthru or { }) // {

                env = callPackage ./nix/pkgs/mangaki/env.nix { };

                static = stdenvNoCC.mkDerivation {
                  pname = "mangaki-static";
                  inherit (oldAttrs) version;
                  phases = [ "installPhase" ];

                  nativeBuildInputs = [ mangaki ];

                  installPhase = ''
                    export DJANGO_SETTINGS_MODULE="mangaki.settings"
                    mkdir -p $out
                    cat <<EOF > settings.ini
                    [secrets]
                      SECRET_KEY = dontusethisorgetfired
                    [deployment]
                      STATIC_ROOT = $out
                    EOF
                    export MANGAKI_SETTINGS_PATH=./settings.ini
                    django-admin collectstatic
                  '';
                };

              };
            });

        };

      # Provide some binary packages for selected system types.
      packages = forAllSystems (system:
        {
          inherit (nixpkgsFor.${system})
            mangaki;
        });

      # The default package for 'nix build'. This makes sense if the
      # flake provides only one package or there is a clear "main"
      # package.
      defaultPackage = forAllSystems (system: self.packages.${system}.mangaki);

      # Development environment
      devShell = forAllSystems (system:
        let
          pkgSet = nixpkgsFor.${system};
          poetry2nix-cli = poetry2nix.packages.${system}.poetry2nix;
        in
        with pkgSet;
        mkShell {
          buildInputs = [
            poetry
            poetry2nix-cli
            mangaki.env
            nixpkgs-fmt
          ];

          DJANGO_SETTINGS_MODULE = "mangaki.settings";

          shellHook = ''
            export MANGAKI_SETTINGS_PATH="$(pwd)"/mangaki/settings.ini # Cheap too.
          '';
        });

      # NixOS system configuration, if applicable
      nixosConfigurations.dev = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux"; # Hardcoded
        modules = [
          ({ modulesPath, pkgs, ... }: {
            imports = [ (modulesPath + "/virtualisation/qemu-vm.nix") ];
            virtualisation.qemu.options = [ "-vga virtio" ];

            # environment.systemPackages = with pkgs; [ st unzip ripgrep chromium ];
            # networking.networkmanager.enable = true;

            # services.xserver.enable = true;
            # services.xserver.layout = "us";
            # services.xserver.windowManager.i3.enable = true;
            # services.xserver.displayManager.lightdm.enable = true;
          })

          # Flake specific support
          ({ ... }: {
            nixpkgs.overlays = [ self.overlay ];
          })

          # Mangaki configuration
          ({ ... }: {
            imports =
              [
                (import ./nix/vm/standalone-configuration.nix {
                  useTLS = false;
                  devMode = true;
                  domainName = "mangaki.dev";
                  editableMode = false;
                })
              ];
          })
        ];
      };

      # A NixOS module, if applicable (e.g. if the package provides a system service).
      nixosModules.mangaki = import ./nix/modules/mangaki.nix;

      # Tests run by 'nix flake check' and by Hydra.
      checks = forAllSystems (system: self.packages.${system} // {
        mangaki-prod-test =
          with import ("${nixpkgs}/nixos/lib/testing-python.nix") { inherit system; };
          makeTest {
            name = "prod-test";
            machine = { ... }: {
              imports = [ self.nixosModules.mangaki ];
              nixpkgs.overlays = [ self.overlay ];
              virtualisation.memorySize = 2048;
              virtualisation.cores = 2;
              services.mangaki = {
                enable = true;
                devMode = false;
                useTLS = false;
                domainName = "mangaki.test";
              };
            };
            testScript = ''
              start_all()

              machine.wait_for_unit("uwsgi.service")
              machine.wait_for_unit("nginx.service")
              machine.wait_for_open_port(80)
              machine.succeed("curl -H 'Host: mangaki.test' http://localhost")

              machine.shutdown()
            '';
          };
        # VM test on website availability.
        mangaki-host-test =
          with import (nixpkgs + "/nixos/lib/testing-python.nix")
          { inherit system; };

          makeTest {
            name = "web-test";
            machine = { ... }: {
              imports = [ self.nixosModules.mangaki ];
              nixpkgs.overlays = [ self.overlay ];
              virtualisation.memorySize = 2048;
              virtualisation.cores = 2;
              services.mangaki = {
                enable = true;
                devMode = true;
              };
            };

            testScript = ''
              start_all()

              machine.wait_for_unit("postgresql.service")
              machine.wait_for_unit("mangaki.service")
              machine.wait_for_unit("mangaki-worker.service")
              machine.wait_for_open_port(8000)
              machine.succeed("curl http://localhost:8000")

              machine.shutdown()
            '';
          };
      });
    };
}
