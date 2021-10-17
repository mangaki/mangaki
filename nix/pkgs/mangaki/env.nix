{ pkgs
, mangaki
}:
let
  env = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./../../..; # so it can find pyproject.toml and poetry.lock
    overrides = pkgs.poetry2nix.overrides.withDefaults
      (import ./overrides.nix { inherit pkgs; });
  };
in
env.override (old:
  {
    extraLibs = (old.extraLibs or [ ]) ++ [ (env.python.pkgs.toPythonModule mangaki) ];
  })
