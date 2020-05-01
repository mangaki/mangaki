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
      buildInputs = [ pkgs.poetry pkgs.poetry2nix.cli python pkgs.nixfmt ];
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
