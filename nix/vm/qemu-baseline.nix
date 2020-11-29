{ config, pkgs, lib, ... }:
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
}
