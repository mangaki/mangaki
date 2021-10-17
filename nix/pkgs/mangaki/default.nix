{ pkgs }:
pkgs.poetry2nix.mkPoetryApplication rec {
  src = ./../../..; # prevents unnecessary sanitizing which causes problems
  projectDir = src; # so it can find pyproject.toml and poetry.lock
  overrides = pkgs.poetry2nix.overrides.withDefaults
  (import ./overrides.nix { inherit pkgs; });
}
