{ config, pkgs, lib, ... }:
let
  inherit (builtins) toString;
in
{
  fileSystems."/".device = "/dev/disk/by-label/nixos";
  boot.initrd.availableKernelModules = [ "xhci_pci" "ehci_pci" "ahci" "usbhid" "usb_storage" "sd_mod" "virtio_balloon" "virtio_blk" "virtio_pci" "virtio_ring" ];
  boot.loader = {
    grub = {
      version = 2;
      device = "/dev/vda";
    };
    timeout = 0;
  };

  services.openssh.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 80 443 ];

  users = {
    mutableUsers = true;
    users.root.initialPassword = "DamnTowerOfGodIsNice";
  };

  # To be on the safe line.
  virtualisation.memorySize = 1024;
  virtualisation.diskSize = 1024;
  virtualisation.graphics = true; # false after.

  # virtualisation.options =
  # let
  #   extPort = config.services.mangaki-vm.forwardedPort;
  #   intPort =
  #     if config.services.mangaki.useTLS then 443
  #     else 80;
  # in
  # # Forward the ports.
  # [ "-net user,hostfwd=tcp::${toString extPort}-:${toString intPort}" ];
}
