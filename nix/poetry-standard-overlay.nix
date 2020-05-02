{ pkgs, lib ? pkgs.lib, useWheels ? false }:
let
  justUseWheels = exceptions: super: overrides: ((lib.mapAttrs
    (name: value:
    if useWheels then super.${name}.override { preferWheel = true; } else value)
    (builtins.removeAttrs overrides exceptions)) // (lib.getAttrs exceptions overrides));
  exceptions = [
    "mccabe"
    "zipp"
  ];
in
self: super: (justUseWheels exceptions super {
  numpy = super.numpy.overridePythonAttrs (old:
      let
        blas = old.passthru.args.blas or pkgs.openblasCompat;
        blasImplementation = lib.nameFromURL blas.name "-";
        cfg = pkgs.writeTextFile {
          name = "site.cfg";
          text = (lib.generators.toINI { } {
            ${blasImplementation} = {
              include_dirs = "${blas}/include";
              library_dirs = "${blas}/lib";
            } // lib.optionalAttrs (blasImplementation == "mkl") {
              mkl_libs = "mkl_rt";
              lapack_libs = "";
            };
          });
        };
      in {
        nativeBuildInputs = old.nativeBuildInputs ++ [ pkgs.gfortran ];
        buildInputs = old.buildInputs ++ [ blas self.cython ];
        enableParallelBuilding = true;
        preBuild = ''
          ln -s ${cfg} site.cfg
        '';
        passthru = old.passthru // {
          blas = blas;
          inherit blasImplementation cfg;
        };
      });

  scipy = null;
  pandas = null;
  pyscopg2 = null;
  psycopg2-binary = null;
  lxml = null;

  mccabe = super.mccabe.overridePythonAttrs (old: {
    buildInputs = old.buildInputs ++ [ self.pytest-runner ];
    doCheck = false;
  });
  zipp = (if lib.versionAtLeast super.zipp.version "2.0.0" then
    (super.zipp.overridePythonAttrs (old: {
      prePatch = ''
        substituteInPlace setup.py --replace \
        'setuptools.setup()' \
        'setuptools.setup(version="${super.zipp.version}")'
      '';
    }))
  else
    super.zipp).overridePythonAttrs (old: {
      propagatedBuildInputs = old.propagatedBuildInputs ++ [ self.toml ];
    });
})
