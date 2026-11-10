#!/bin/sh
# Apply pending migrations, then run the server (API + crawler) in the foreground.
set -e
python -m dijitalvatan.migrate
exec python -m dijitalvatan.main
