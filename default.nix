{ useMKL ? false, useWheels ? true, pkgs ? import <nixpkgs> {
  config.allowUnfree = useMKL;
  overlays = [ (import ./nix/nixpkgs-overlays.nix) ];
}, lib ? pkgs.lib, python ? pkgs.python3 }:
let
  composeOverlays = overlays: lib.foldl' lib.composeExtensions (self: super: {}) overlays;
  gitOverrides = import ./nix/poetry-git-overlay.nix { inherit pkgs; };
  standardOverrides = import ./nix/standard-poetry-overlay.nix { inherit pkgs; goForWheels = useWheels; };
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
  assert useWheels -> !useMKL;
  {
    poetryShell = pkgs.mkShell {
      # Poetry for the venv.
      # Poetry2Nix.cli to update the Zero hashes.
      # nixfmt to reformat the *.nix files.
      buildInputs = [ pkgs.poetry pkgs.poetry2nix.cli python pkgs.nixfmt pkgs.mdl ];
      # We need to expose libstdc++ & friends in our shell.
      shellHook = ''
         export PYTHONPATH=$PYTHONPATH:`pwd`/mangaki # We enforce this in order to not have to deal with this ugly shit of doing ./mangaki/manage.py ; django-admin is enough. Also, it fix something which I don't want to investigate.
         # TODO: investigate the interaction between django-bootstrap4 versioning mechanism (setuptools-scm) and our project structure (mangaki/mangaki).
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
