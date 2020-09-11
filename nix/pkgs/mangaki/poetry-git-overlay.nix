{ pkgs }:
self: super: {

  mangaki-zero = super.mangaki-zero.overridePythonAttrs (old: {
    src = pkgs.fetchgit {
      url = "https://github.com/mangaki/zero";
      rev = "680e93c1ef1726e2a68b362f2cde1dd9e139f2f3";
      sha256 = "161rmiyvd3x7wcmwxfhnh8vngq7kcrvcmmnsqxyjyfi2msc232ac";
    };

    format = "pyproject";

    buildInputs = old.buildInputs ++ [ self.poetry ];
  });

}
