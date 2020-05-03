{ useWheels ? true, pkgs ? import <nixpkgs> { }, lib ? pkgs.lib
, pythonSelector ? "python3", python ? pkgs.${pythonSelector} }:
let
  composeOverlays = overlays:
    lib.foldl' lib.composeExtensions (self: super: { }) overlays;
  gitOverrides = import ./nix/poetry-git-overlay.nix { inherit pkgs; };
  standardOverrides =
    import ./nix/poetry-standard-overlay.nix { inherit pkgs useWheels; };
  localOverrides = composeOverlays [ gitOverrides standardOverrides ];
  mkPoetryAppEnv = { projectDir ? null
    , pyproject ? projectDir + "/pyproject.toml"
    , poetrylock ? projectDir + "/poetry.lock", overrides, python ? python, ...
    }@attrs:
    let
      app =
        python.pkgs.toPythonModule (pkgs.poetry2nix.mkPoetryApplication attrs);
      env = pkgs.poetry2nix.mkPoetryEnv {
        inherit pyproject poetrylock overrides python;
      };
    in env.override (old: { extraLibs = (old.extraLibs or [ ]) ++ [ app ]; });

  finalOverrides = pkgs.poetry2nix.overrides.withoutDefaults localOverrides;
  mangakiNiceEnvHook = ''
    export DJANGO_SETTINGS_MODULE="mangaki.settings" # Cheap.
    export MANGAKI_SETTINGS_PATH="$(pwd)"/mangaki/settings.ini # Cheap too.
  '';
  filterNixFiles = with builtins; path: type: !lib.hasSuffix ".nix" path;
  mangakiSrc = lib.cleanSourceWith {
    filter = filterNixFiles;
    src = pkgs.poetry2nix.cleanPythonSources { src = ./.; };
  };
in rec {
  poetryShell = pkgs.mkShell {
    # Poetry for the venv.
    # Poetry2Nix.cli to update the Zero hashes.
    # nixfmt to reformat the *.nix files.
    buildInputs =
      [ pkgs.poetry pkgs.poetry2nix.cli python pkgs.nixfmt pkgs.mdl ];
    # We need to expose libstdc++ & friends in our shell.
    shellHook = ''
      ${mangakiNiceEnvHook}
       export LD_LIBRARY_PATH=${lib.makeLibraryPath [ pkgs.stdenv.cc.cc ]}
    '';
  };

  app = pkgs.poetry2nix.mkPoetryApplication {
    projectDir = ./.;
    src = mangakiSrc;
    overrides = finalOverrides;
    inherit python;
  };

  staticContents = pkgs.stdenvNoCC.mkDerivation {
    pname = "mangaki-static";
    version = app.version;
    buildInputs = [ app ];

    phases = [ "installPhase" ];

    installPhase = ''
      export DJANGO_SETTINGS_MODULE="mangaki.settings"
      mkdir -p $out
      cat <<EOF > settings.ini
      [secrets]
        SECRET_KEY = dontusethisorgetfired
      [deployment]
        STATIC_ROOT = $out
      EOF
      export MANGAKI_SETTINGS_PATH=./settings.ini
      django-admin collectstatic
    '';
  };

  shell = pkgs.mkShell {
    buildInputs = [
      pkgs.poetry
      pkgs.poetry2nix.cli
      (mkPoetryAppEnv {
        projectDir = ./.;
        src = mangakiSrc;
        overrides = finalOverrides;
        inherit python;
      })
    ];
    shellHook = ''
      ${mangakiNiceEnvHook}
    '';
  };
}
