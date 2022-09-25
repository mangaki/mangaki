self: super:
{
  numpy = super.numpy.override ({ preferWheel = true; });
  scipy = super.scipy.override ({ preferWheel = true; });
  pandas = super.pandas.override ({ preferWheel = true; });
  scikit-learn = super.scikit-learn.override ({ preferWheel = true; });
  click-didyoumean = super.click-didyoumean.overridePythonAttrs (
    old: {
      buildInputs = (old.buildInputs or [ ]) ++ [ self.poetry ];
    }
  );
  termcolor = super.termcolor.overridePythonAttrs (
    old: {
      buildInputs = (old.buildInputs or [ ]) ++ [ self.hatchling self.hatch-vcs ];
    }
  );
  contourpy = super.contourpy.overridePythonAttrs (
    old: {
      buildInputs = (old.buildInputs or [ ]) ++ [ self.pybind11 ];
    }
  );
}
