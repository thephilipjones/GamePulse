#!/bin/bash
# Export team colors and aliases from local database as SQL UPDATE statements
# Usage: ./team_colors_export.sh [output_file]
#
# Then copy the output file to production and run:
#   cat team_colors_export-*.sql | docker compose exec -T db psql -U postgres -d app

set -e

DATETIME=$(date +%Y-%m-%d-%H%M%S)
OUTPUT_FILE="${1:-team_colors_export-${DATETIME}.sql}"

echo "Exporting team colors from local database..."

docker compose exec -T db psql -U postgres -d app -t -A -c "
SELECT format(
  'UPDATE dim_team SET primary_color=%L, secondary_color=%L, aliases=%L WHERE team_id=%L;',
  primary_color, secondary_color, aliases, team_id
)
FROM dim_team
WHERE sport='ncaam' AND primary_color IS NOT NULL;
" > "$OUTPUT_FILE"

COUNT=$(wc -l < "$OUTPUT_FILE")
echo "Exported $COUNT team(s) to $OUTPUT_FILE"
echo ""
echo "To apply on target database:"
# echo "  cat $OUTPUT_FILE | docker compose exec -T db psql -U postgres -d app"
echo "  cat $OUTPUT_FILE | docker compose exec -T db psql -U gamepulse -d gamepulse"
