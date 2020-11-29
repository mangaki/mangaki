{ useTLS ? false
, forwardedPort ? if useTLS then 8443 else 8000
, devMode ? true
, editableMode ? devMode # enable local changes on the host to be transferred to the VM through 9p mount.
, allowedHosts ? [ "127.0.0.1" ]
, domainName ? null
}:
{ config, pkgs, lib, ... }:
{
  imports = [
    ./qemu-baseline.nix # QEMU specific stuff.
    ../modules/mangaki.nix # Mangaki's module.
    ./mangaki-vm.nix # Mangaki's VM-specific additions.
  ];

  services.mangaki = {
    enable = true;
    inherit useTLS devMode allowedHosts domainName;
    staticRoot = pkgs.mangaki.static;
    envPackage = pkgs.mangaki.env;
  };

  services.mangaki-vm = {
    enable = true;
    inherit forwardedPort editableMode;
  };
}
