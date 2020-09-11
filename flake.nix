{
  description = "Mangaki";

  # Nixpkgs / NixOS version to use.
  inputs.nixpkgs = { type = "github"; owner = "NixOS"; repo = "nixpkgs"; ref = "nixos-20.03"; };

  outputs = { self, nixpkgs }@inputs:
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
        {

          lapack = prev.lapack.override { lapackProvider = final.mkl; };
          blas = prev.blas.override { blasProvider = final.mkl; };

          mangaki = callPackage ./nix/pkgs/mangaki { };
          mangaki-env = callPackage ./nix/pkgs/mangaki/env.nix { };

        };

      # Provide some binary packages for selected system types.
      packages = forAllSystems (system:
        {
          inherit (nixpkgsFor.${system})
            mangaki mangaki-env;
        });

      # The default package for 'nix build'. This makes sense if the
      # flake provides only one package or there is a clear "main"
      # package.
      defaultPackage = forAllSystems (system: self.packages.${system}.mangaki);

      # Development environment
      devShell = forAllSystems (system:
        let
          pkgSet = nixpkgsFor.${system};
        in
        with pkgSet;
        mkShell {
          buildInputs = [
            poetry
            poetry2nix.cli
            mangaki-env
          ];

          shellHook = ''
            export DJANGO_SETTINGS_MODULE="mangaki.settings" # Cheap.
            export MANGAKI_SETTINGS_PATH="$(pwd)"/mangaki/settings.ini # Cheap too.
          '';
        });

      # A NixOS module, if applicable (e.g. if the package provides a system service).
      nixosModules.mangaki = import ./nix/modules/mangaki.nix;

      # Tests run by 'nix flake check' and by Hydra.
      checks = forAllSystems (system: self.packages.${system});
    };
}
