{ pkgs
, mangaki
, poetry2nix
}:
let
  env = poetry2nix.mkPoetryEnv {
    projectDir = ./../../..; # so it can find pyproject.toml and poetry.lock
    overrides = [
      (import ./poetry-standard-overlay.nix)
      (import ./poetry-git-overlay.nix { inherit pkgs; })
      poetry2nix.defaultPoetryOverrides
    ];
  };
in
env.override (old:
  {
    extraLibs = (old.extraLibs or [ ]) ++ [ (env.python.pkgs.toPythonModule mangaki) ];
  })
