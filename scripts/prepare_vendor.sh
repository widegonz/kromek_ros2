#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE="${1:-$HOME/SDK_linux.zip}"
DEST="$ROOT/vendor/dr_park"
[[ -f "$ARCHIVE" ]] || { echo "Missing Dr. Park archive: $ARCHIVE" >&2; exit 1; }
[[ ! -e "$DEST/source" ]] || { echo "Vendor SDK already present: $DEST/source; refusing overwrite" >&2; exit 1; }
mkdir -p "$DEST"
python3 - "$ARCHIVE" "$DEST" <<'PYCODE'
import hashlib,io,pathlib,sys,zipfile
archive=pathlib.Path(sys.argv[1]).resolve()
dest=pathlib.Path(sys.argv[2]).resolve()
with zipfile.ZipFile(archive) as outer:
    for name,sub in [('SDK_linux/SpectrometerPackage.zip','source'),('SDK_linux/linux_python_code.zip','reference')]:
        with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
            target=dest/sub;target.mkdir(parents=True,exist_ok=True)
            for item in inner.infolist():
                parts=pathlib.PurePosixPath(item.filename).parts
                if item.filename.startswith('/') or '..' in parts:
                    raise RuntimeError('Unsafe ZIP member: '+item.filename)
            inner.extractall(target)
    docs=dest/'docs';docs.mkdir(exist_ok=True)
    (docs/'Kromek_SIGMA50_Linux_Setup_and_Acquisition_Procedure.pdf').write_bytes(
        outer.read('SDK_linux/Kromek_SIGMA50_Linux_Setup_and_Acquisition_Procedure.pdf'))
(dest/'archive_sha256.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print('Vendor SDK imported into:',dest)
print('Original files preserved; no root privileges used.')
PYCODE
