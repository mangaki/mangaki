self: super: {
  lapack = super.lapack.override {
    lapackProvider = self.mkl;
  };
  blas = super.blas.override {
    blasProvider = self.mkl;
  };
}
