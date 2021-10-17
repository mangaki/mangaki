{ pkgs }:
self: super: {

  mangaki-zero = super.mangaki-zero.overridePythonAttrs (
    _: {
      src = pkgs.fetchgit {
        url = "https://github.com/mangaki/zero";
        rev = "9dc50747b2dee03ef76fcc8068620222d7bed9bf";
        sha256 = "0q8lznr0cc3h9f9smhd80d910vgbzfndsb2345n6f3i3q9a5d918";
      };
    }
  );

}
