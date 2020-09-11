{ pkgs, poetry2nix }:

poetry2nix.mkPoetryApplication rec {
  src = ./../../..; # prevents unnecessary sanitizing which causes problems
  projectDir = src; # so it can find pyproject.toml and poetry.lock
  overrides = poetry2nix.overrides.withoutDefaults
    (import ./overrides.nix { inherit pkgs; });
}
