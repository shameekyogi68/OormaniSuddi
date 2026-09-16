#!/usr/bin/env bash
# Real-ESRGAN general x4v3 weights (BSD-3-Clause, xinntao/Real-ESRGAN v0.2.5.0), ~4.9 MB each.
set -euo pipefail
cd "$(dirname "$0")/../models"
base=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0
fetch() {
  local name=$1 sha=$2
  if [ -f "$name" ] && [ "$(shasum -a 256 "$name" | cut -d' ' -f1)" = "$sha" ]; then echo "ok  $name"; return; fi
  curl -sL "$base/$name" -o "$name.part"
  [ "$(shasum -a 256 "$name.part" | cut -d' ' -f1)" = "$sha" ] || { echo "checksum mismatch: $name"; rm -f "$name.part"; exit 1; }
  mv "$name.part" "$name"; echo "got $name"
}
fetch realesr-general-x4v3.pth 8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292
fetch realesr-general-wdn-x4v3.pth 1641f8c4464b9f097c9fdda5589273713f67cf59f3d909e0bd688f0cee269dca
