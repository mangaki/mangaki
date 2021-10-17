{ pkgs ? import <nixpkgs> {} }:
pkgs.poetry2nix.mkPoetryApplication rec {
  src = ./../../..; # prevents unnecessary sanitizing which causes problems
  projectDir = src; # so it can find pyproject.toml and poetry.lock
  overrides = [
    pkgs.poetry2nix.defaultPoetryOverrides
    (import ./poetry-standard-overlay.nix)
    (import ./poetry-git-overlay.nix { inherit pkgs; })
  ];
}
