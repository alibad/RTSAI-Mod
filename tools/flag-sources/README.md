# Native flag sources

`korea.svg`, `cuba.svg`, `libya.svg` and `iraq.svg` are byte-for-byte copies of the approved browser flags in `RTSAI-WebGame/web/public/flags`. They use flag-icons under the adjacent MIT licence. `lebanon.svg` is the previously approved flag-icons national flag documented in `docs/art-provenance.md`.

Import the four formerly abbreviated native flags, preserving every other atlas pixel:

```sh
python companion/scripts/build-levant-flags.py
```

Imports require Pillow and `rsvg-convert`. Local verification only requires Pillow:

```sh
python companion/scripts/build-levant-flags.py --check
python tools/test-faction-flags.py
python companion/scripts/build-levant-flags.py --check --installed-app "/path/to/RTS AI.app" --receipt /tmp/native-flags.json
```

`native-imports.json` seals the sixteen native faction regions at all three densities, source SVG hashes and all pixels outside the four imported regions. Changed, blank and old abbreviation tiles fail the check. The importer retains the existing atlas dimensions and the Lebanon flag.
