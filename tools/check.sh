#!/usr/bin/env bash
# Check the repo layout and design files. Run before every commit.
# Prints FAIL and WARN lines; exits 1 if anything failed.
#
# Usage: tools/check.sh
set -uo pipefail
cd "$(dirname "$0")/.."

fails=0 warns=0
fail() { echo "FAIL: $*"; fails=$((fails + 1)); }
warn() { echo "WARN: $*"; warns=$((warns + 1)); }

# Every path outside .git, NUL separated so names with spaces are still reported.
all() { find . -path ./.git -prune -o "$@" -print0; }

[ -f LICENSE.md ] || fail "LICENSE.md: missing, every design without its own LICENSE.txt points to it"
[ -f PRINTING.md ] || fail "PRINTING.md: missing, every printable design points to it"

while IFS= read -r -d '' p; do
  fail "${p#./}: space in path"
done < <(all -name '* *')

while IFS= read -r -d '' f; do
  fail "${f#./}: ZIP archive, unpack it with tools/import-thing.sh and delete it"
done < <(all -type f -iname '*.zip')

check_stl() {
  local f=$1 size n
  size=$(wc -c <"$f")
  if [ "$size" -ge 84 ]; then
    # Binary STL: 80-byte header, uint32 triangle count, 50 bytes per triangle.
    n=$(od --endian=little -An -tu4 -j80 -N4 "$f" | tr -d ' ')
    [ "$size" -eq $((84 + 50 * n)) ] && return
  fi
  [ "$(head -c 5 "$f")" = solid ] && tail -c 256 "$f" | grep endsolid >/dev/null && return
  fail "$f: not a valid binary or ASCII STL"
}

while IFS= read -r -d '' f; do
  f=${f#./}
  size=$(wc -c <"$f")
  if [ "$size" -gt 104857600 ]; then
    fail "$f: over 100 MB, GitHub rejects it"
  elif [ "$size" -gt 52428800 ]; then
    warn "$f: over 50 MB, GitHub warns on push"
  fi
  case ${f,,} in *.stl) check_stl "$f" ;; esac
done < <(all -type f)

# Relative links and <img src> in Markdown must resolve.
while IFS= read -r -d '' md; do
  md=${md#./}
  dir=$(dirname "$md")
  while IFS= read -r link; do
    case $link in http://* | https://* | mailto:* | '#'*) continue ;; esac
    path=${link%%#*}
    case $path in /*) target=.$path ;; *) target=$dir/$path ;; esac
    [ -e "$target" ] || fail "$md: broken link $link"
  done < <(grep -oE '\]\([^)[:space:]]+\)|src="[^"]+"' "$md" | sed -E 's/^\]\(//; s/\)$//; s/^src="//; s/"$//')
done < <(all -type f -name '*.md')

for product in RB-*/; do
  product=${product%/}
  [ -f "$product/README.md" ] || fail "$product: missing README.md"

  for f in "$product"/*; do
    [ -f "$f" ] && [ "$(basename "$f")" != README.md ] && fail "$f: design files belong in a design folder"
  done

  for d in "$product"/*/; do
    [ -d "$d" ] || continue
    d=${d%/}
    name=$(basename "$d")
    [[ $name =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || fail "$d: folder name is not lowercase kebab-case"
    grep -qF "($d/)" README.md || fail "$d: not listed in README.md"
    grep -qF "($name/)" "$product/README.md" || fail "$d: not listed in $product/README.md"

    if [ ! -f "$d/README.md" ]; then
      fail "$d: missing README.md"
      continue
    fi

    for e in "$d"/*; do
      case $(basename "$e") in
        README.md | LICENSE.txt | files | images | kicad) ;;
        README.txt) fail "$e: Thingiverse export, move its content to README.md and delete it" ;;
        *) warn "$e: unexpected entry, use files/ or images/" ;;
      esac
    done

    id=$(sed -nE 's/^\| Thingiverse \| \[thing:([0-9]+)\].*/\1/p' "$d/README.md")
    if [ -n "$id" ]; then
      [[ $name == *-"$id" ]] || fail "$d: Thingiverse design folder must end in -$id"
      grep -q 'TODO: Thingiverse drops line breaks' "$d/README.md" && warn "$d/README.md: description not reformatted yet"
    fi
    if compgen -G "$d/files/*.[sS][tT][lL]" >/dev/null; then
      grep -qF 'PRINTING.md' "$d/README.md" || fail "$d/README.md: printable design must link PRINTING.md"
    fi
    # A design's own LICENSE.txt (third-party authors) wins over the repo LICENSE.md.
    if [ -f "$d/LICENSE.txt" ]; then
      grep -q '^| License |.*(LICENSE.txt)' "$d/README.md" || fail "$d/README.md: License row must link LICENSE.txt"
    elif [ -d "$d/files" ]; then
      grep -q '^| License |.*LICENSE.md' "$d/README.md" || fail "$d/README.md: License row must link LICENSE.md"
    fi

    # KiCad templates: one complete project per folder, linked from the README.
    for k in "$d"/kicad/*/; do
      [ -d "$k" ] || continue
      p=$(basename "$k")
      for ext in kicad_pro kicad_pcb kicad_sch; do
        [ -f "$k$p.$ext" ] || fail "$k: missing $p.$ext"
      done
      [ -f "${k}meta/info.html" ] || fail "$k: missing meta/info.html"
      grep -qF "kicad/$p/$p.kicad_pro" "$d/README.md" || fail "$d/README.md: does not link kicad/$p/$p.kicad_pro"
    done

    # Every part and image should be reachable from the design README.
    for f in "$d"/files/* "$d"/images/*; do
      [ -f "$f" ] || continue
      rel=${f#"$d"/}
      grep -qF "$rel" "$d/README.md" || warn "$f: not referenced from $d/README.md"
    done
  done
done

echo "check: $fails failure(s), $warns warning(s)"
[ "$fails" -eq 0 ]
