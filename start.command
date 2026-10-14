#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
./scripts/start.sh
read -r -p 'Palvelin pysähtyi. Sulje ikkuna Enterillä.'
