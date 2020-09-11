{ pkgs, poetry2nix
, mangaki }:

let
  env = poetry2nix.mkPoetryEnv {
    projectDir = ./../../..; # so it can find pyproject.toml and poetry.lock
    overrides = poetry2nix.overrides.withoutDefaults
      (import ./overrides.nix { inherit pkgs; });
  };
in env.override (old:
  {
    extraLibs = (old.extraLibs or []) ++ [ (env.python.pkgs.toPythonModule mangaki) ];
  })
