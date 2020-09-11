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

          mangaki = (callPackage ./nix/pkgs/mangaki { }).overrideAttrs(oldAttrs:
            {
              # Can't add anything to `passthru` from poetry2nix
              passthru = (oldAttrs.passthru or {}) // {

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
        in
        with pkgSet;
        mkShell {
          buildInputs = [
            poetry
            poetry2nix.cli
            mangaki.env
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
