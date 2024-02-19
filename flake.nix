{
  outputs = { self, nixpkgs, ... }@inputs:
  let
    inherit (nixpkgs) lib;

    eachSystem = f:
      lib.genAttrs
        lib.systems.flakeExposed
        (system: f system inputs.nixpkgs.legacyPackages.${system});
  in
  {
    packages = eachSystem (system: pkgs: {
      default = pkgs.python3Packages.mutagen.overrideAttrs {
        src = ./.;
      };
    });

    devShells = eachSystem (system: pkgs: {
      default = pkgs.mkShell {
        inputsFrom = [
          self.packages.${system}.default
        ];

        nativeBuildInputs = with pkgs; [
          pypy3
        ] ++ (with pkgs.python3Packages; [
          exceptiongroup
          python-lsp-server
        ]);
      };
    });
  };
}
