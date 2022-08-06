{ config, pkgs, lib, ... }:
with lib;
# FIXME: move from password to passwordFile.
let
  cfg = config.services.mangaki;
  defaultSettings = {
    debug = {
      DEBUG = cfg.devMode;
      DEBUG_VUE_JS = cfg.devMode;
    };
    email =
      let
        consoleBackend = "django.core.mail.backends.console.EmailBackend";
        smtpBackend = "django.core.mail.backends.smtp.EmailBackend";
      in
      {
        EMAIL_BACKEND = if cfg.devMode then consoleBackend else smtpBackend;
      };
    secrets = (optionalAttrs (!cfg.useLocalDatabase && cfg.databaseConfig.password != null) {
      DB_PASSWORD = cfg.databaseConfig.password;
    })
    // (optionalAttrs cfg.mal.enable {
      MAL_PASS = cfg.mal.password;
    });
    deployment = optionalAttrs !cfg.devMode {
      MEDIA_ROOT = "/srv/mangaki/media";
      DATA_ROOT = "/srv/mangaki/data";
      STATIC_ROOT = cfg.staticRoot;
    };
    hosts = optionalAttrs !cfg.devMode {
      ALLOWED_HOSTS = cfg.allowedHosts;
    };
    mal = {
      MAL_USER = cfg.mal.user;
      MAL_USER_AGENT = cfg.mal.userAgent;
    };
    anidb = {
      ANIDB_CLIENT = cfg.anidb.client;
      ANIDB_VERSION = cfg.anidb.version;
    };
    pgsql = {
      DB_HOST = if cfg.useLocalDatabase then "127.0.0.1" else cfg.databaseConfig.host;
      DB_NAME = if cfg.useLocalDatabase then "mangaki" else cfg.databaseConfig.name;
      DB_USER = if cfg.useLocalDatabase then "mangaki" else cfg.databasConfig.user;
    };
    # It's preferable to let users configure explicitly the DSN in development mode.
    sentry = (optionalAttrs (!cfg.devMode && cfg.sentry.dsn != null) {
      DSN = cfg.sentry.dsn;
    });
    smtp = (optionalAttrs cfg.email.useSMTP {
      EMAIL_HOST = cfg.email.host;
      EMAIL_HOST_PASSWORD = cfg.email.password;
      EMAIL_HOST_USER = cfg.email.user;
      EMAIL_PORT = cfg.email.port;
      EMAIL_SSL_CERTFILE = cfg.email.sslCertFile;
      EMAIL_SSL_KEYFILE = cfg.email.sslKeyFile;
      EMAIL_TIMEOUT = cfg.email.timeout;
      EMAIL_USE_SSL = cfg.email.useSSL;
      EMAIL_USE_TLS = cfg.email.useTLS;
    });
  };
in
{
  imports = [];

  options.services.mangaki = {
    enable = mkEnableOption "the mangaki service";
    devMode = mkEnableOption "the development mode (non-production setup)";
    useTLS = mkEnableOption "TLS on the web server";
    staticRoot = mkOption {
      example = "mangakiPackages.static";
      description = ''
        In **production** mode, the package to use for static data, which will be used as static root.
        Note that, as its name indicates it, static data never change during the lifecycle of the service.
        As a result, static root is read-only.
        It can only be changed through changes in the static derivation.
      '';
      type = types.str;
    };
    allowedHosts = mkOption {
      example = ''
        [ "127.0.0.1" "steinsgate.dev" ]
      '';
      default = [ "127.0.0.1" ];
      type = types.listOf types.str;
      description = ''
        List of allowed hosts (Django parameter).
      '';
    };
    settings = mkOption {
      default = defaultSettings;
      example = ''
        {
          debug = { DEBUG_VUE_JS = false; };
          sentry = { dsn = "<some dsn>"; };
        }
      '';
      description = ''
        The settings for Mangaki which will be turned into a settings.ini.
        Most of the public parameters can be configured directly from the service.

        It will be deep merged otherwise.
      '';
      type = types.attrs;
    };
    nginx = {
      enable = mkOption {
        default = !cfg.devMode;
        description = ''
          This will use NGINX as a web server which will reverse proxy the uWSGI endpoint.

          Disable it if you want to put your own web server.
        '';
      };
    };
    backups = {
      enable = mkOption {
        default = !cfg.devMode;
        description = ''
          This will create a systemd timer to backup periodically (by default, weekly) the database using pg_dump.
        '';
        type = types.bool;
      };
      periodicity = mkOption {
        default = "weekly";
        description = "The periodicity to use to auto-backup the database.";
      };
      postBackupScript = mkOption {
        default = "";
        description = ''
          More than often, you will wish for a way to execute custom commands after a successful backup.
          Like, borg to encrypt & send the backups to multiple repositories.
          And remove the old backups in order to not clog up the disk space on the machine.
          Here, you can give a script to execute as a string.
        '';
        type = types.str;
      };
    };
    lifecycle = {
      performInitialMigration = mkOption {
        default = true;
        description = ''
          This will create a systemd oneshot for initial migration.
          This is 99 % of the case what you want.

          Though, you might want to handle migrations yourself (in case of already created DBs).
        '';
        type = types.bool;
      };
      runTimersForRanking = mkOption {
        default = true;
        description = ''
          This will create a systemd timer for ranking and tops.
        '';
        type = types.bool;
      };
    };
    useLocalDatabase = mkOption {
      default = true;
      description = ''
        Whether to let this service create automatically a sensible PostgreSQL database locally.

        You want this disabled whenever you have an external PostgreSQL database.
      '';
      type = types.bool;
    };
    databaseConfig = mkOption {
      default = null;
      description = ''
        Submodule configuration for the PostgreSQL database.
      '';
      example = ''
        {
          user = "mangaki";
          host = "db.mangaki.fr";
          port = 5432;
          password = "ararararararagi"; # or null, for trusted auth.
        }
      '';
      type = types.nullOr (types.submodule dbOptions);
    };
    useLocalRedis = mkOption {
      default = true;
      description = ''
        Whether to let this service create automatically a sensible Redis instance locally.

        You want this disabled whenever you have an external Redis instance.
      '';
      type = types.bool;
    };
    redisConfig = mkOption {
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
      type = types.nullOr (types.submodule redisOptions);
    };
    domainName = mkOption {
      default = null;
      example = "mangaki.fr";
      description = ''
        The domain to use for the service in production mode.

        In development mode, this is not needed.
        If you really want, you can use some /etc/hosts to point to the VM IP.
        e.g. mangaki.dev → <VM IP>
        Useful to test production mode locally.
      '';
      type = types.nullOr types.str;
    };
  };

  config = {
    assertions = [
      {
        assertion = !cfg.useLocalDatabase -> cfg.databaseConfig != null;
        message = "If local database is not used, database configuration must be set.";
      }
      {
        assertion = !cfg.useLocalRedis -> cfg.redisConfig != null;
        message = "If local Redis instance is not used, Redis instance configuration must be set.";
      }
      {
        assertion = cfg.email.useSMTP -> cfg.email.host != null && cfg.email.password != null;
        message = "If SMTP is enabled, SMTP host and password must be set.";
      }
    ];

    warnings = []
    ++ (optional !cfg.lifecycle.performInitialMigrations [ "You disabled initial migration setup, this can have unexpected effects. "]);

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
      initialScript = ''
        CREATE DATABASE mangaki;
        \c mangaki
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE EXTENSION IF NOT EXISTS unaccent;
      ''; # Extensions & Mangaki database set.
    };

    # User activation script for directory initialization.
    # systemd oneshot for initial migration.
    # systemd oneshot for fixture loading.
    # systemd timers for ranking & top --all in production mode. 
    # systemd timers for backup of PGSQL.

    # systemd service for Celery.

    # Set up NGINX.
    services.nginx = mkIf !cfg.devMode {
      enable = !cfg.devMode;
    };

    # Set up Gunicorn/uWSGI (?)
    services.uwsgi = mkIf !cfg.devMode {
      enable = !cfg.devMode;
      instance = {
        type = "normal";
      };
    };
    # Set up systemd unit for Django development server.

    # Throw some Let's Encrypt or snakeoil.
  };
}
