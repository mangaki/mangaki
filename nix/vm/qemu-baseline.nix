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

  services.getty.autologinUser = "root";
  services.getty.helpLine = 
  ''
    The "root" account has 'test' password initially.
    You can change it.
  '';

  users = {
    mutableUsers = true;
    users.root.initialPassword = "test"; # Nicer password for QWERTY/AZERTY layout.
  };

  # To be on the safe line.
  virtualisation.memorySize = 1024;
  virtualisation.diskSize = 1024;
  virtualisation.graphics = false;
}
