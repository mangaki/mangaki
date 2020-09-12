{ pkgs }:
self: super: {

  mangaki-zero = super.mangaki-zero.overridePythonAttrs (old: {
    src = pkgs.fetchFromGitHub {
      owner = "mangaki";
      repo = "zero";
      rev = "v1.0.1";
      sha256 = "03c7vz4cilpa6c72n22zfppy0xfppqphcc7nyniinkdwig1wb260";
    };

    format = "pyproject";

    buildInputs = old.buildInputs ++ [ self.poetry ];
  });

}
