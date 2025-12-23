#!/bin/bash

echo base name is $(basename)
# Check for arguments
if [ -z "$1" ]; then
  echo "Please provide a base directory path as the first argument."
  exit 1
fi

if [ -z "$2" ]; then
  echo "Please provide an output directory path as the second argument."
  exit 1
fi

BASE_DIR="$1"
OUT_DIR="$2"
DIR_NAME=$(basename "$BASE_DIR")
LOGFILE="$OUT_DIR/${DIR_NAME}_log.txt"

# Create output directory if it doesn't exist
mkdir -p "$OUT_DIR"

# Logging function
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOGFILE"
}

log "Script started with base directory: $BASE_DIR and output directory: $OUT_DIR"

# Check base directory exists
if [ ! -d "$BASE_DIR" ]; then
  log "❌ Error: The directory $BASE_DIR does not exist."
  exit 1
fi

# Find files
TABLES=$(find "$BASE_DIR" -type f -name "table*.qza")
TAXONOMIES=$(find "$BASE_DIR" -type f -name "taxonomy*.qza")

if [ -z "$TABLES" ]; then
  log "❌ Error: No table*.qza files found."
  exit 1
fi

if [ -z "$TAXONOMIES" ]; then
  log "❌ Error: No taxonomy*.qza files found."
  exit 1
fi

log "Found tables: $TABLES"
log "Found taxonomies: $TAXONOMIES"

TABLES_LIST=$(echo $TABLES | sed 's/,/ --i-tables /g')
TAXONOMIES_LIST=$(echo $TAXONOMIES | sed 's/,/ --i-data /g')

log "Merging tables..."
qiime feature-table merge \
  --i-tables $TABLES_LIST \
  --o-merged-table "$OUT_DIR/Merged_table.qza" \
  && log "✅ Merged_table.qza created in $OUT_DIR." \
  || log "❌ Failed to merge tables."

log "Merging taxonomies..."
qiime feature-table merge-taxa \
  --i-data $TAXONOMIES_LIST \
  --o-merged-data "$OUT_DIR/Merged_taxonomy.qza" \
  && log "✅ Merged_taxonomy.qza created in $OUT_DIR." \
  || log "❌ Failed to merge taxonomies."

log "Script finished."
