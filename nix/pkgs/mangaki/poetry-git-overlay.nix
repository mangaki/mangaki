{ pkgs }:
self: super: {

  mangaki-zero = super.mangaki-zero.overridePythonAttrs (
    old: {
      src = pkgs.fetchgit {
        url = "https://github.com/mangaki/zero";
        rev = "e39bffbb29e00067120d70ee91959f1717cdb0d2";
        sha256 = "0i8vv402vi5biihs2zcxqszk58sv7hqyxfqlfrm0zhcql804nz9c";
      };

      buildInputs = (old.buildInputs or [ ]) ++ [ self.poetry ];
    }
  );

}
