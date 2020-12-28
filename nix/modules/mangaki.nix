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

    secrets = {
      SECRET_KEY = "CHANGE_ME";
    }
      // (optionalAttrs (!cfg.useLocalDatabase && cfg.databaseConfig.password != null) {
        DB_PASSWORD = cfg.databaseConfig.password;
      })
      # // (optionalAttrs cfg.mal.enable {
      #   MAL_PASS = cfg.mal.password;
      # })
      ;
  }
    // optionalAttrs (!cfg.devMode) {
      deployment = {
        MEDIA_ROOT = "/srv/mangaki/media";
        STATIC_ROOT = "${cfg.staticRoot}";
        DATA_ROOT = "/srv/mangaki/data";
      };

      hosts = {
        ALLOWED_HOSTS = concatStringsSep "," cfg.allowedHosts;
      };
    }
    # // optionalAttrs (cfg.mal.user != "" && cfg.mal.userAgent != "") {
    #   mal = {
    #     MAL_USER = cfg.mal.user;
    #     MAL_USER_AGENT = cfg.mal.userAgent;
    #   };
    # }
    # // optionalAttrs (cfg.anidb.client != "" && cfg.anidb.version != "") {
    #   anidb = {
    #     ANIDB_CLIENT = cfg.anidb.client;
    #     ANIDB_VERSION = cfg.anidb.version;
    #   };
    # }
    // optionalAttrs (!cfg.useLocalDatabase) {
      pgsql = {
        DB_HOST = cfg.databaseConfig.host;
        DB_NAME = cfg.databaseConfig.name;
        DB_USER = cfg.databasConfig.user;
      };
    }
    #// optionalAttrs (!cfg.devMode && cfg.sentry.dsn != null) {
    #  sentry = {
    #    DSN = cfg.sentry.dsn;
    #  };
    #}
    # // optionalAttrs (cfg.email.useSMTP) {
    #   EMAIL_HOST = cfg.email.host;
    #   EMAIL_HOST_PASSWORD = cfg.email.password;
    #   EMAIL_HOST_USER = cfg.email.user;
    #   EMAIL_PORT = cfg.email.port;
    #   EMAIL_SSL_CERTFILE = cfg.email.sslCertFile;
    #   EMAIL_SSL_KEYFILE = cfg.email.sslKeyFile;
    #   EMAIL_TIMEOUT = cfg.email.timeout;
    #   EMAIL_USE_SSL = cfg.email.useSSL;
    #   EMAIL_USE_TLS = cfg.email.useTLS;
    # }
    ;

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
      type = types.attrs;
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
        description = "The periodicity to use to auto-backup the database.";
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
    };
    useLocalDatabase = mkOption {
      type = types.bool;
      default = true;
      description = ''
        Whether to let this service create automatically a sensible PostgreSQL database locally.

        You want this disabled whenever you have an external PostgreSQL database.
      '';
    };
    databaseConfig = mkOption {
      type = types.nullOr (types.submodule dbOptions);
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
        assertion = !cfg.useLocalDatabase -> cfg.databaseConfig != null;
        message = "If local database is not used, database configuration must be set.";
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
      # {
      #   assertion = cfg.email.useSMTP -> cfg.email.host != null && cfg.email.password != null;
      #   message = "If SMTP is enabled, SMTP host and password must be set.";
      # }
    ];

    warnings = [ ]
      ++ (optional (!cfg.lifecycle.performInitialMigrations) [ "You disabled initial migration setup, this can have unexpected effects. " ]);

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

    # User activation script for directory initialization.
    # systemd oneshot for initial migration.
    systemd.services.mangaki = mkIf (cfg.devMode) {
      after = [ "postgresql.service" ];
      requires = [ "postgresql.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Mangaki service";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        User = "mangaki";
        Group = "mangaki";

        StateDirectory = "mangaki";
        StateDirectoryMode = "0750";
        WorkingDirectory = "/var/lib/mangaki";
      };

      preStart = initialMigrationScript;
     
      script = ''
        python ${srcPath}/mangaki/manage.py runserver
      '';
    };
    # systemd oneshot for fixture loading.
    # systemd timers for ranking & top --all in production mode.
    systemd.timers = genAttrs
      [ "mangaki-ranking" "mangaki-top" ]
      (service: {
        wantedBy = [ "timers.target" ];
        description = "Run ${service}.service every hours";
        timerConfig.OnUnitActiveSec = "1h";
      });

    systemd.services.mangaki-ranking = {
      after = [ "mangaki.service" ];
      requires = [ "mangaki.service" ];
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
      after = [ "mangaki.service" ];
      requires = [ "mangaki.service" ];
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
    # TODO: systemd timers for backup of PGSQL.

    # systemd service for Celery.
    systemd.services.mangaki-worker = {
      after = [ "mangaki.service" ];
      requires = [ "mangaki.service" ];
      wantedBy = [ "multi-user.target" ];

      description = "Mangaki background tasks runner";
      path = [ cfg.envPackage ];
      environment = mangakiEnv;

      serviceConfig = {
        Type = "forking";
        User = "mangaki";
        Group = "mangaki";
        ExecStop = "celery -B -A mangaki:celery_app --pidfile=/run/celery/%n.pid stopwait -l INFO";
        ExecStart = "celery -B -A mangaki:celery_app --pidfile=/run/celery/%n.pid worker -l INFO";
      };
    };

    # FIXME: write down a systemd oneshot for initial migrations.

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
        root = cfg.staticRoot;
        locations."/".extraConfig = ''
          uwsgi_pass localhost:8000;
          include ${config.services.nginx.package}/conf/uwsgi_params;
        '';
      };
    };

    # Set up uWSGI
    services.uwsgi = mkIf (!cfg.devMode) {
      enable = !cfg.devMode;
      plugins = [ "python3" ];
      instance = {
        type = "emperor";
        vassals = {
          mangaki = {
            type = "normal";
            http = ":8000";
            socket = "${config.services.uwsgi.runDir}/mangaki.sock"; # FIXME(Ryan): make this work with NGINX but permissions are not okay.
            pythonPackages = _: [ cfg.appPackage ];
            env = (mapAttrsToList (n: v: "${n}=${v}") mangakiEnv);
            module = "wsgi:application";
            chdir = "${srcPath}/mangaki/mangaki";
            pyhome = "${cfg.appPackage}";
            master = true;
            vacuum = true;
            harakiri = 20;
            max-requests = 5000;
            chmod-socket = 664; # 664 is already too weak…
          };
        };
      };
    };

    users = {
      users.mangaki = {
        group = "mangaki";
        description = "Mangaki user";
      };

      groups.mangaki = { };
    };
  };
}
