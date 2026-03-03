#!/bin/bash
# Backup script for Colony skill and data
# Creates timestamped backups and keeps the last 5

set -e  # Exit on error

BACKUP_DIR="$HOME/colony-backup"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="colony-$DATE"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Colony Backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# What to backup
BACKUP_ITEMS=(
    "$HOME/.claude/skills/colony"      # Skill symlink (will be followed)
    "$HOME/.colony"                    # Colony data
)

# Build list of existing items to backup
BACKUP_LIST=()
for item in "${BACKUP_ITEMS[@]}"; do
    if [ -e "$item" ]; then
        BACKUP_LIST+=("$item")
    fi
done

# Check if there's anything to backup
if [ ${#BACKUP_LIST[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No Colony files found to backup${NC}"
    echo "Expected: ~/.claude/skills/colony or ~/.colony/"
    exit 0
fi

echo -e "${YELLOW}📦 Creating backup: $BACKUP_NAME${NC}"
echo "Items to backup:"
for item in "${BACKUP_LIST[@]}"; do
    echo "  - $item"
done
echo ""

# Create the backup
# Note: -h follows symlinks, -z compresses
tar -czhf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -h "${BACKUP_LIST[@]}" 2>/dev/null

if [ $? -eq 0 ]; then
    # Get backup size
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)
    echo -e "${GREEN}✅ Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz ($BACKUP_SIZE)${NC}"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Clean up old backups (keep last 5)
echo ""
echo -e "${YELLOW}🧹 Cleaning up old backups (keeping last 5)...${NC}"
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/colony-*.tar.gz 2>/dev/null | wc -l)

if [ $BACKUP_COUNT -gt 5 ]; then
    ls -1t "$BACKUP_DIR"/colony-*.tar.gz | tail -n +6 | xargs rm -f 2>/dev/null
    echo -e "${GREEN}✅ Removed $((BACKUP_COUNT - 5)) old backup(s)${NC}"
else
    echo -e "${YELLOW}No cleanup needed (have $BACKUP_COUNT, keep 5)${NC}"
fi

# List all backups
echo ""
echo -e "${BLUE}Current backups:${NC}"
ls -lh "$BACKUP_DIR"/colony-*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Backup complete!${NC}"
echo -e "${BLUE}========================================${NC}"

# Optional: Show restore instructions
echo ""
echo -e "${YELLOW}To restore from backup:${NC}"
echo "  tar -xzf $BACKUP_DIR/$BACKUP_NAME.tar.gz -C /"
