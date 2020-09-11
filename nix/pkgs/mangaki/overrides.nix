{ pkgs, lib ? pkgs.lib, useWheels ? true }:

let
  composeOverlays = overlays:
    lib.foldl' lib.composeExtensions (self: super: { }) overlays;
  gitOverrides = import ./poetry-git-overlay.nix { inherit pkgs; };
  standardOverrides =
    import ./poetry-standard-overlay.nix { inherit pkgs useWheels; };
  localOverrides = composeOverlays [ gitOverrides standardOverrides ];
in localOverrides
