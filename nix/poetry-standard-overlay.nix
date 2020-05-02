{ pkgs, lib ? pkgs.lib, goForWheels ? false }:
self: super: {
  numpy = (if goForWheels then
    super.numpy.override { preferWheel = true; }
  else
    super.numpy.overridePythonAttrs (old:
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
      }));

  scipy =
    if goForWheels then super.scipy.override { preferWheel = true; } else null;
  pandas =
    if goForWheels then super.pandas.override { preferWheel = true; } else null;
  pyscopg2 = if goForWheels then
    super.pyscopg2.override { preferWheel = true; }
  else
    null;
  psycopg2-binary = if goForWheels then
    super.psycopg2-binary.override { preferWheel = true; }
  else
    null;
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
  lxml =
    if goForWheels then super.lxml.override { preferWheel = true; } else null;
}
