{ pkgs, lib ? pkgs.lib }:
let
  composeOverlays = overlays:
    lib.foldl' lib.composeExtensions (self: super: { }) overlays;
  gitOverrides = import ./poetry-git-overlay.nix { inherit pkgs; };
  standardOverrides =
    import ./poetry-standard-overlay.nix;
  localOverrides = composeOverlays [ gitOverrides standardOverrides ];
in
localOverrides
