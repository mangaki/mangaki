{
  useTLS ? false
  , forwardedPort ? if useTLS then 8443 else 8000
  , devMode ? true
  , editableMode ? devMode # enable local changes on the host to be transfered to the VM through 9p mount.
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

  # TODO: figure out how to realize the editable mode
  # we 9p-mount the host mangaki folder on the VM in
  # /run/mangaki for example
  # then, we run a systemd unit user service
  # which takes the dependencies env of mangaki
  # and run the Django dev server
  # this way.
  # using the stat reloader, it should pick up changes.
  # (every second, it rescan the stuff.)
  # (note that we cannot use watchman-based reloading.)
  # (inotify is impossible to implement through virtualization.)
  services.mangaki = {
    enable = true;
    inherit useTLS devMode allowedHosts domainName;
    staticRoot = pkgs.mangakiPackages.static;
    package = pkgs.mangakiPackages.env;
  };

  services.mangaki-vm = {
    enable = true;
    inherit forwardedPort editableMode;
  };
}
