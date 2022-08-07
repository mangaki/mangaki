{ config, pkgs, lib, ... }:
with lib;
let
  cfg = config.services.mangaki;


  configSource = with generators; toINI
    {
      mkKeyValue = mkKeyValueDefault
        {
          # Not sure if this is a strict requirement but the default config come with true/false like this
          mkValueString = v:
            if true == v then "True"
            else if false == v then "False"
            else mkValueStringDefault { } v;
        } "=";
    }
    cfg.settings;
  configFile = pkgs.writeText "settings.ini" configSource;

  mangakiEnv = {
    MANGAKI_SETTINGS_PATH = toString configFile;
    DJANGO_SETTINGS_MODULE = "mangaki.settings";
  } // optionalAttrs (cfg.useLocalDatabase) {
    DATABASE_URL = "postgresql:///mangaki"; # Rely on trusted authentication.
  };
  srcPath = if isNull cfg.sourcePath then pkgs.mangaki.src else cfg.sourcePath;
  initialMigrationScript = ''
    # Initialize database
    if [ ! -f .initialized ]; then
      django-admin migrate
      django-admin loaddata ${srcPath}/fixtures/{partners,seed_data}.json

      touch .initialized
    fi
  '';
  mkOneShotShortTimer = service: {
    wantedBy = [ "timers.target" ];
    description = "Run ${service}.service every hours";
    timerConfig.OnUnitActiveSec = "1h";
  };
in
{
  imports = [ ];

  options.services.mangaki = {
    enable = mkEnableOption "the mangaki service";
    devMode = mkEnableOption "the development mode (non-production setup)";
    # TLS
    useTLS = mkEnableOption "TLS on the web server";
    useACME = mkEnableOption "Let's Encrypt for TLS certificates delivery (require a public domain name)";
    forceTLS = mkEnableOption "Redirect HTTP on HTTPS";
    sslCertificate = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "Path to server SSL certificate.";
    };
    sslCertificateKey = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "Path to server SSL certificate key.";
    };

    staticRoot = mkOption {
      type = types.package;
      default = pkgs.mangaki.static;
      description = ''
        In **production** mode, the package to use for static data, which will be used as static root.
        Note that, as its name indicates it, static data never change during the lifecycle of the service.
        As a result, static root is read-only.
        It can only be changed through changes in the static derivation.
      '';
    };
    sourcePath = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = ''
        In **production** mode, the package to use for source, is the mangaki package.
        As a result, the source is read-only.
        Though, in editable mode, a mutable path can be passed, e.g. /run/mangaki.
      '';
    };
    envPackage = mkOption {
      type = types.package;
      default = pkgs.mangaki.env;
      description = ''
        This is the Mangaki Python's environment: its dependencies.
      '';
    };
    appPackage = mkOption {
      type = types.package;
      default = pkgs.mangaki;
      description = ''
        This is the Mangaki Python's application for production deployment.
      '';
    };
    allowedHosts = mkOption {
      type = types.listOf types.str;
      default = [ "127.0.0.1" "localhost" ] ++ optionals (cfg.domainName != null) [ cfg.domainName ];
      example = [ "127.0.0.1" "steinsgate.dev" ];
      description = ''
        List of allowed hosts (Django parameter).
      '';
    };
    settings = mkOption {
      type = types.submodule {
        freeformType = with types; attrsOf attrs;
      };
      example = ''
        {
          debug = { DEBUG_VUE_JS = false; };
          sentry = { DSN = "<some dsn>"; };
        }
      '';
      description = ''
        The settings for Mangaki which will be turned into a settings.ini.
        Most of the public parameters can be configured directly from the service.

        It will be deep merged otherwise.
      '';
    };
    nginx = {
      enable = mkOption {
        type = types.bool;
        default = !cfg.devMode;
        description = ''
          This will use NGINX as a web server which will reverse proxy the uWSGI endpoint.

          Disable it if you want to put your own web server.
        '';
      };
    };
    backups = {
      enable = mkOption {
        type = types.bool;
        default = !cfg.devMode;
        description = ''
          This will create a systemd timer to backup periodically (by default, weekly) the database using pg_dump.
        '';
      };
      periodicity = mkOption {
        type = types.str;
        default = "weekly";
        description = "The periodicity to use to auto-backup the database. Refer to man 7 systemd.time for exact syntax.";
      };
      postBackupScript = mkOption {
        type = types.str;
        default = "";
        description = ''
          More than often, you will wish for a way to execute custom commands after a successful backup.
          Like, borg to encrypt & send the backups to multiple repositories.
          And remove the old backups in order to not clog up the disk space on the machine.
          Here, you can give a script to execute as a string.
        '';
      };
    };
    lifecycle = {
      performInitialMigrations = mkOption {
        type = types.bool;
        default = true;
        description = ''
          This will create a systemd oneshot for initial migration.
          This is 99 % of the case what you want.

          Though, you might want to handle migrations yourself (in case of already created DBs).
        '';
      };
      runTimersForRanking = mkOption {
        type = types.bool;
        default = true;
        description = ''
          This will create a systemd timer for ranking and tops.
        '';
      };
      runTimersForIndex = mkOption {
        type = types.bool;
        default = true;
        description = ''
          This will create a systemd timer for index.
        '';
      };
    };
    useLocalDatabase = mkOption {
      type = types.bool;
      default = true;
      description = ''
        Whether to let this service create automatically a sensible PostgreSQL database locally.

        You want this disabled whenever you have an external PostgreSQL database.
      '';
    };
    useLocalRedis = mkOption {
      type = types.bool;
      default = true;
      description = ''
        Whether to let this service create automatically a sensible Redis instance locally.

        You want this disabled whenever you have an external Redis instance.
      '';
    };
    redisConfig = mkOption {
      type = types.nullOr (types.submodule redisOptions);
      default = null;
      description = ''
        Submodule configuration for the Redis instance.
      '';
      example = ''
        {
          database = 1;
          host = "redis.mangaki.fr";
          port = 6379;
          password = "charaznableisredlikeredis"; # or null, for trusted authentication.
        }
      '';
    };
    domainName = mkOption {
      type = types.nullOr types.str;
      default = null;
      example = "mangaki.fr";
      description = ''
        The domain to use for the service in production mode.

        In development mode, this is not needed.
        If you really want, you can use some /etc/hosts to point to the VM IP.
        e.g. mangaki.dev → <VM IP>
        Useful to test production mode locally.
      '';
    };
  };

  config = mkIf cfg.enable {
    assertions = [
      {
        assertion = !cfg.useLocalDatabase -> (
          hasAttr "SECRET_FILE" cfg.settings.secrets || hasAttr "URL" (cfg.settings.database or {})
        );
        message = "If local database is not used, either a secret file with a database URI or the database URI must be set.";
      }
      {
        assertion = !cfg.useLocalRedis -> cfg.redisConfig != null;
        message = "If local Redis instance is not used, Redis instance configuration must be set.";
      }
      {
        assertion = cfg.useTLS -> (cfg.useACME || (cfg.sslCertificate != null && cfg.sslCertificateKey != null));
        message = "If TLS is enabled, either use Let's Encrypt or provide your own certificates.";
      }
      {
        assertion = cfg.useACME -> cfg.domainName != null;
        message = "If ACME is used, a domain name must be set, otherwise ACME will fail.";
      }
      {
        assertion = !cfg.devMode -> cfg.domainName != null;
        message = "If production mode is enabled, a domain name must be set, otherwise NGINX cannot be configured.";
      }
      {
        assertion = !cfg.devMode -> cfg.settings.secrets ? "SECRET_KEY" || cfg.settings.secrets ? "SECRET_FILE";
        message = "If production mode is enabled, either a secret file or a secret key must be set in secrets, otherwise Mangaki will not start.";
      }
      # {
      #   assertion = cfg.email.useSMTP -> cfg.email.host != null && cfg.email.password != null;
      #   message = "If SMTP is enabled, SMTP host and password must be set.";
      # }
    ];

  warnings = concatLists ([
     (optional (!cfg.lifecycle.performInitialMigrations)
     "You disabled initial migration setup, this can have unexpected effects.")
     ((optional (!cfg.devMode -> cfg.settings.secrets.SECRET_KEY == "CHANGE_ME" && !(cfg.settings.secrets ? "SECRET_FILE")))
     "You are deploying a production (${if isNull cfg.domainName then "no domain name set" else cfg.domainName}) instance with a default secret key. The server will be vulnerable.")
     (optional (!cfg.devMode -> (!(cfg.settings.secrets ? "SECRET_FILE") || cfg.settings.secrets.SECRET_FILE == null))
     "You are deploying a production (${if isNull cfg.domainName then "no domain name set" else cfg.domainName}) instance with no secret file. Some secrets may end up in the Nix store which is world-readable.")
   ]);

   services.mangaki.settings = {
     debug = {
        DEBUG = lib.mkDefault cfg.devMode;
        DEBUG_VUE_JS = lib.mkDefault cfg.devMode;
      };

      secrets = {};

      email =
        let
          consoleBackend = "django.core.mail.backends.console.EmailBackend";
          smtpBackend = "django.core.mail.backends.smtp.EmailBackend";
        in
        {
          EMAIL_BACKEND = lib.mkDefault (if cfg.devMode then consoleBackend else smtpBackend);
        };
    } // optionalAttrs (cfg.useLocalDatabase) {
      database.URL = lib.mkDefault "postgresql://";
    } // optionalAttrs (!cfg.devMode) {
      deployment = {
        MEDIA_ROOT = lib.mkDefault "/var/lib/mangaki/media";
        STATIC_ROOT = lib.mkDefault "${cfg.staticRoot}";
        DATA_ROOT = lib.mkDefault "/var/lib/mangaki/data";
      };

      hosts = {
        ALLOWED_HOSTS = lib.mkDefault (concatStringsSep "," cfg.allowedHosts);
      };
    };

    environment.systemPackages = [ cfg.envPackage ];
    environment.variables = {
      inherit (mangakiEnv) MANGAKI_SETTINGS_PATH DJANGO_SETTINGS_MODULE;
    };

    services.redis.enable = cfg.useLocalRedis; # Redis set.
    services.postgresql = mkIf cfg.useLocalDatabase {
      enable = cfg.useLocalDatabase; # PostgreSQL set.
      ensureUsers = [
        {
          name = "mangaki";
          ensurePermissions = {
            "DATABASE mangaki" = "ALL PRIVILEGES";
          };
        }
      ]; # Mangaki user set.
      initialScript = pkgs.writeText "mangaki-postgresql-init.sql" ''
        CREATE DATABASE mangaki;
        \c mangaki
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE EXTENSION IF NOT EXISTS unaccent;
      ''; # Extensions & Mangaki database set.
    };

    # systemd oneshot for initial migration.
    systemd.services.mangaki-init-db = {
      after = [ "postgresql.service" ];
      requires = [ "postgresql.service" ];
      before = mkIf (!cfg.devMode) [ "uwsgi.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Initialize Mangaki database for the first time";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        User = "mangaki";
        Group = "mangaki";

        StateDirectory = "mangaki";
        StateDirectoryMode = "0755";
        WorkingDirectory = "/var/lib/mangaki";
      };
      serviceConfig = {
        Type = "oneshot";
        StandardOutput = "journal+console";
      };
      script = initialMigrationScript;
    };

    systemd.services.mangaki-migrate-db = {
      after = [ "postgresql.service" "mangaki-init-db.service" ];
      requires = [ "postgresql.service" "mangaki-init-db.service" ];
      before = mkIf (!cfg.devMode) [ "uwsgi.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Migrate Mangaki database (idempotent)";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        User = "mangaki";
        Group = "mangaki";

        StateDirectory = "mangaki";
        StateDirectoryMode = "0755";
        WorkingDirectory = "/var/lib/mangaki";
      };
      serviceConfig = {
        Type = "oneshot";
        StandardOutput = "journal+console";
      };
      script = ''
        django-admin migrate
      '';
    };

    # Mangaki development server
    systemd.services.mangaki = mkIf (cfg.devMode) {
      after = [ "mangaki-init-db.service" "postgresql.service" ];
      requires = [ "mangaki-init-db.service" "postgresql.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Mangaki service";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        User = "mangaki";
        Group = "mangaki";

        StateDirectory = "mangaki";
        StateDirectoryMode = "0755";
        WorkingDirectory = "/var/lib/mangaki";
      };

      script = ''
        python ${srcPath}/mangaki/manage.py runserver
      '';
    };

    # systemd oneshot for fixture loading.
    # systemd timer for full text search index.
    systemd.timers."mangaki-index" = mkIf cfg.lifecycle.runTimersForIndex (mkOneShotShortTimer "mangaki-index");
    # systemd timers for ranking & top --all in production mode.
    systemd.timers."mangaki-ranking" = mkIf cfg.lifecycle.runTimersForRanking (mkOneShotShortTimer "mangaki-ranking");
    systemd.timers."mangaki-top" = mkIf cfg.lifecycle.runTimersForRanking (mkOneShotShortTimer "mangaki-top");
    # systemd timer for regular DB backups
    systemd.timers."mangaki-db-backup" = mkIf (cfg.backups.enable) {
      wantedBy = [ "timers.target" ];
      partOf = [ "mangaki-db-backup.service" ];
      timerConfig.OnCalendar = cfg.backups.periodicity;
      timerConfig.Persistent = true;
      description = "Run a backup of Mangaki database on ${cfg.backups.periodicity} periodicity";
    };

    systemd.services.mangaki-index = {
      after = [ "mangaki-init-db.service" "mangaki-migrate-db.service" ];
      requires = [ "mangaki-init-db.service" "mangaki-migrate-db.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Mangaki search index";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        Type = "oneshot";
        User = "mangaki";
        Group = "mangaki";
      };

      script = ''
        django-admin index
      '';
    };

    systemd.services.mangaki-ranking = {
      after = [ "mangaki-init-db.service" "mangaki-migrate-db.service" ];
      requires = [ "mangaki-init-db.service" "mangaki-migrate-db.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Mangaki daily ranking";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        Type = "oneshot";
        User = "mangaki";
        Group = "mangaki";
      };

      script = ''
        django-admin ranking
      '';
    };

    systemd.services.mangaki-top = {
      after = [ "mangaki-init-db.service" "mangaki-migrate-db.service" ];
      requires = [ "mangaki-init-db.service" "mangaki-migrate-db.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Mangaki daily top calculation";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        Type = "oneshot";
        User = "mangaki";
        Group = "mangaki";
      };

      script = ''
        django-admin top --all
      '';
    };

    # FIXME: repair it for external DBs.
    # Backup unit available only *not* in dev mode and with local database.
    systemd.services.mangaki-db-backup = mkIf (cfg.backups.enable && cfg.useLocalDatabase) {
      after = [ "postgresql.service" ];
      requires = [ "postgresql.service" ];

      serviceConfig.Type = "oneshot";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        User = "mangaki";
        Group = "mangaki";

        StateDirectory = "mangaki";
        StateDirectoryMode = "0755";
        WorkingDirectory = "/var/lib/mangaki";
      };

      script = ''
        mkdir -p backups
        today=$(date +"%Y%m%d")
        ${pkgs.postgresql}/bin/pg_dump \
          --format=c \
          mangaki > backups/mangaki.$today.dump
        # Custom post-backup script (if applicable)
        ${optionalString (cfg.backups.postBackupScript != "") "${cfg.backups.postBackupScript} backups/mangaki.$today.dump"}
      '';
    };

    # systemd service for Celery.
    systemd.services.mangaki-worker = let
      celeryApp = "mangaki.workers:app";
    in
    {
      after = [ "mangaki-init-db.service" "mangaki-migrate-db.service" "redis.service" ];
      requires = [ "mangaki-init-db.service" "mangaki-migrate-db.service" "redis.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Mangaki background tasks runner";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = let
        workerName = "maho";
      in
      {
        Type = "forking";
        User = "mangaki";
        Group = "mangaki";

        RuntimeDirectory = "celery";
        StateDirectoryMode = "0755";
        WorkingDirectory = "/var/lib/mangaki";

        ExecStop = "${cfg.envPackage}/bin/celery multi stopwait ${workerName} -B -A ${celeryApp} --pidfile=/run/celery/%n.pid --logfile=/run/celery/%n%I.log -l INFO";
        ExecReload = "${cfg.envPackage}/bin/celery multi restart ${workerName} -B -A ${celeryApp} --pidfile=/run/celery/%n.pid --logfile=/run/celery/%n%I.log -l INFO";
        ExecStart = "${cfg.envPackage}/bin/celery multi start ${workerName} -B -A ${celeryApp} --pidfile=/run/celery/%n.pid --logfile=/run/celery/%n%I.log -l INFO";
      };
    };

    # Set up NGINX.
    services.nginx = mkIf (!cfg.devMode) {
      enable = !cfg.devMode;
      recommendedOptimisation = !cfg.devMode;
      recommendedProxySettings = !cfg.devMode;
      recommendedGzipSettings = !cfg.devMode;
      recommendedTlsSettings = !cfg.devMode && cfg.useTLS;

      virtualHosts."${cfg.domainName}" = {
        enableACME = cfg.useTLS && cfg.useACME;
        sslCertificate = if cfg.useTLS && !cfg.useACME then cfg.sslCertificate else null;
        sslCertificateKey = if cfg.useTLS && !cfg.useACME then cfg.sslCertificateKey else null;
        forceSSL = cfg.useTLS && cfg.forceTLS;
        addSSL = cfg.useTLS && !cfg.forceTLS;
        locations."/static/" = {
          alias = "${cfg.staticRoot}/";
        };
        locations."/" = {
          extraConfig = ''
            uwsgi_pass unix:/var/lib/mangaki/uwsgi.sock;
            include ${config.services.nginx.package}/conf/uwsgi_params;
          '';
        };
      };
    };

    # Set up uWSGI
    services.uwsgi = mkIf (!cfg.devMode) {
      enable = !cfg.devMode;
      user = "root"; # For privilege dropping.
      group = "root";
      plugins = [ "python3" ];
      instance = {
        type = "emperor";
        vassals = {
          mangaki = {
            type = "normal";
            http = ":8000";
            socket = "/var/lib/mangaki/uwsgi.sock";
            pythonPackages = _: [ cfg.appPackage ];
            env = (mapAttrsToList (n: v: "${n}=${v}") mangakiEnv);
            module = "wsgi:application";
            chdir = "${srcPath}/mangaki/mangaki";
            pyhome = "${cfg.appPackage}";
            master = true;
            vacuum = true;
            processes = 2;
            harakiri = 20;
            max-requests = 5000;
            chmod-socket = 664; # 664 is already too weak…
            uid = "mangaki";
            gid = "nginx";
          };
        };
      };
    };

    users = {
      users.mangaki = {
        group = "mangaki";
        description = "Mangaki user";
        isSystemUser = true;
      };

      groups.mangaki = { };
    };
  };
}
