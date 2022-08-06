{ pkgs, poetry2nix, lib ? pkgs.lib }:
let
  defaultParameters = rec {
    src = ./../../..; # prevents unnecessary sanitizing which causes problems
    projectDir = src; # so it can find pyproject.toml and poetry.lock
    overrides = [
      (import ./poetry-standard-overlay.nix)
      (import ./poetry-git-overlay.nix { inherit pkgs; })
      poetry2nix.defaultPoetryOverrides
    ];
  };
  drv = poetry2nix.mkPoetryApplication defaultParameters;
  isUsingWheel = pkg: (drv.passthru.python.pkgs.${pkg}.src.isWheel or false);
in
  assert isUsingWheel "numpy" && isUsingWheel "scipy" && isUsingWheel "pandas";
  drv
