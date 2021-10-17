self: super:
{
  numpy = super.numpy.override ({ preferWheel = true; });
  scipy = super.scipy.override ({ preferWheel = true; });
  pandas = super.pandas.override ({ preferWheel = true; });
  scikit-learn = super.scikit-learn.override ({ preferWheel = true; });

  lazy-object-proxy = super.lazy-object-proxy.overridePythonAttrs (
    old: {
      # disable the removal of pyproject.toml, required because of setuptools_scm
      dontPreferSetupPy = true;
    }
  );
  astroid = super.astroid.overridePythonAttrs (
    old: rec {
      buildInputs = (old.buildInputs or [ ]) ++ [ self.pytest-runner self.typing-extensions ];
      doCheck = false;
    }
  );
  pylint = super.pylint.overridePythonAttrs (
    old: rec {
      buildInputs = (old.buildInputs or [ ]) ++ [ self.pytest-runner self.typing-extensions ];
      doCheck = false;
      postPatch = ''
        substituteInPlace setup.cfg --replace 'platformdirs>=2.2.0' 'platformdirs'
      '';
    }
  );
}
