{ config, pkgs, lib, ... }:
with lib;
let
  cfg = config.services.mangaki-vm;
in
  {
    imports = [ ];

    options.services.mangaki-vm = {
      enable = mkEnableOption "the mangaki VM service";

      forwardedPort = mkOption {
        type = types.nullOr types.port;
        default = null;
        description = ''
          Forward port.
        '';
      };

      hostSourcePath = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = ''
          Host source path for editable mode.
        '';
      };

      editableMode = mkOption {
        type = types.bool;
        default = false;
        description = ''
          Enable editable mode.
        '';
      };
    };

    config = mkIf cfg.enable {
      assertions = [
        {
          assertion = cfg.editableMode -> cfg.hostSourcePath != null;
          message = "Editable mode cannot work without an host source path to mount through 9p";
        }
      ];

      warnings = mkMerge [
        (mkIf cfg.editableMode [ "Editable mode is currently broken, fileSystems are not properly mounted because of mkVMOverride. At your own risk." ])
      ];

      # we 9p-mount the host mangaki folder on the VM in
      # /run/mangaki for example
      # then, we reuse a systemd unit service
      # which takes the dependencies env of mangaki
      # and run the Django dev server
      # this way.
      # using the stat reloader, it should pick up changes.
      # (every second, it rescan the stuff. not really battery friendly.)
      # (note that we cannot use watchman-based reloading.)
      # (inotify is impossible to implement through virtualization.)

      # FIXME: figure out how to force fileSystem in NixOS-generated virtual machines.
      # Mount srctree on /run/mangaki.
      fileSystems."/run/mangaki" = mkIf cfg.editableMode (mkForce {
        device = "srctree";
        fsType = "9p";
        options = [ "trans=virtio" "version=9p2000.L" ];
        neededForBoot = true;
      });

      # Mangaki's source path systemd services are overriden in editable mode.
      # But, static paths stays still, because they are not relevant anyway.
      services.mangaki.sourcePath = mkIf cfg.editableMode (mkForce "/run/mangaki");

      virtualisation.qemu.options =
        let
          extPort = cfg.forwardedPort;
          intPort =
            if config.services.mangaki.useTLS then 443
            else 80;
        in
        mkMerge ([
          # Forward the ports.
          (mkIf (extPort != null) [ "-net user,hostfwd=tcp::${toString extPort}-:${toString intPort}" ])
          (mkIf cfg.editableMode [ "-virtfs local,path=\"${cfg.hostSourcePath}\",security_model=none,mount_tag=srctree" ])
        ]);

      # FIXME: is there a way to rebuild envPackage magically and restart the service?
      # or, shall we opt-out Nix for dependencies management?
    };
  }
