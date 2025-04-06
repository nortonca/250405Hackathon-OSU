{pkgs}: {
  deps = [
    pkgs.portaudio
    pkgs.libGLU
    pkgs.libGL
    pkgs.postgresql
    pkgs.openssl
    pkgs.iana-etc
  ];
}
