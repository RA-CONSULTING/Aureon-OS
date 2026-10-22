
let
  config = import ../.idx/dev.nix { pkgs = import <nixpkgs> {}; };
in
{
  inherit (config) channel packages env idx;

  tests = {
    channelIsString = assert builtins.isString config.channel;
    packagesIsList = assert builtins.isList config.packages;
    envIsAttrs = assert builtins.isAttrs config.env;
    extensionsIsList = assert builtins.isList config.idx.extensions;
    previewsEnableIsBool = assert builtins.isBool config.idx.previews.enable;
    onCreateIsAttrs = assert builtins.isAttrs config.idx.workspace.onCreate;
    onStartIsAttrs = assert builtins.isAttrs config.idx.workspace.onStart;
  };
}
