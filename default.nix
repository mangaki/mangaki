{ useWheels ? true
, pkgs ? import <nixpkgs> {}
, lib ? pkgs.lib
, pythonSelector ? "python3"
, python ? pkgs.${pythonPackageName}
}:
let
  composeOverlays = overlays: lib.foldl' lib.composeExtensions (self: super: {}) overlays;
  gitOverrides = import ./nix/poetry-git-overlay.nix { inherit pkgs; };
  standardOverrides = import ./nix/poetry-standard-overlay.nix { inherit pkgs useWheels; };
  localOverrides = composeOverlays [ gitOverrides standardOverrides ];
  mkPoetryAppEnv =
    { projectDir ? null
    , pyproject ? projectDir + "/pyproject.toml"
    , poetrylock ? projectDir + "/poetry.lock"
    , overrides
    , python ? python
    , ...
  }@attrs:
  let
    app = python.pkgs.toPythonModule (pkgs.poetry2nix.mkPoetryApplication attrs);
    env = pkgs.poetry2nix.mkPoetryEnv {
      inherit pyproject poetrylock overrides python;
    };
  in
  env.override
  (old: {
    extraLibs = (old.extraLibs or []) ++ [ app ];
  });

  finalOverrides = pkgs.poetry2nix.overrides.withoutDefaults localOverrides;
in
  {
    poetryShell = pkgs.mkShell {
      # Poetry for the venv.
      # Poetry2Nix.cli to update the Zero hashes.
      # nixfmt to reformat the *.nix files.
      buildInputs = [ pkgs.poetry pkgs.poetry2nix.cli python pkgs.nixfmt pkgs.mdl ];
      # We need to expose libstdc++ & friends in our shell.
      shellHook = ''
         export DJANGO_SETTINGS_MODULE="mangaki.settings" # Cheap.
         export LD_LIBRARY_PATH=${lib.makeLibraryPath [pkgs.stdenv.cc.cc]}
      '';
    };

    app = pkgs.poetry2nix.mkPoetryApplication {
      projectDir = ./.;
      overrides = finalOverrides;
      inherit python;
    };

    shell = pkgs.mkShell {
      buildInputs = [
        pkgs.poetry
        pkgs.poetry2nix.cli
        (mkPoetryAppEnv {
        projectDir = ./.;
        overrides = finalOverrides;
        inherit python;
      })
      ];
    };
  }
