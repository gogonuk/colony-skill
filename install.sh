#!/bin/bash
# Installation script for Colony skill
# This script creates a symlink from ~/.claude/skills/colony to this repository

set -e  # Exit on error

SKILL_NAME="colony"
INSTALL_DIR="$HOME/.claude/skills"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Colony Skill Installation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if SOURCE_DIR contains the skill
if [ ! -d "$SOURCE_DIR/$SKILL_NAME" ]; then
    echo -e "${RED}❌ Error: $SKILL_NAME directory not found in $SOURCE_DIR${NC}"
    echo "Expected: $SOURCE_DIR/$SKILL_NAME/"
    exit 1
fi

# Check if SKILL.md exists
if [ ! -f "$SOURCE_DIR/$SKILL_NAME/SKILL.md" ]; then
    echo -e "${RED}❌ Error: SKILL.md not found${NC}"
    echo "Expected: $SOURCE_DIR/$SKILL_NAME/SKILL.md"
    exit 1
fi

# Create install directory if it doesn't exist
echo -e "${YELLOW}📁 Creating install directory...${NC}"
mkdir -p "$INSTALL_DIR"

# Remove existing installation (if any)
if [ -L "$INSTALL_DIR/$SKILL_NAME" ]; then
    echo -e "${YELLOW}🔗 Removing existing symlink...${NC}"
    rm "$INSTALL_DIR/$SKILL_NAME"
elif [ -d "$INSTALL_DIR/$SKILL_NAME" ]; then
    echo -e "${YELLOW}📦 Backing up existing directory...${NC}"
    BACKUP_DIR="$INSTALL_DIR/${SKILL_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
    mv "$INSTALL_DIR/$SKILL_NAME" "$BACKUP_DIR"
    echo -e "${GREEN}✅ Backed up to: $BACKUP_DIR${NC}"
fi

# Create symlink
echo -e "${YELLOW}🔗 Creating symlink...${NC}"
ln -s "$SOURCE_DIR/$SKILL_NAME" "$INSTALL_DIR/$SKILL_NAME"

# Create Colony data directory
echo -e "${YELLOW}📁 Creating Colony data directory...${NC}"
mkdir -p "$HOME/.colony"/{reputation,patterns,memory}

# Verify installation
echo ""
echo -e "${YELLOW}🔍 Verifying installation...${NC}"
if [ -L "$INSTALL_DIR/$SKILL_NAME" ] && [ -f "$INSTALL_DIR/$SKILL_NAME/SKILL.md" ]; then
    echo -e "${GREEN}✅ Installation successful!${NC}"
    echo ""
    echo -e "${BLUE}Colony Skill Details:${NC}"
    echo "  Source:    $SOURCE_DIR/$SKILL_NAME"
    echo "  Installed: $INSTALL_DIR/$SKILL_NAME"
    echo "  Data:      $HOME/.colony/"
    echo ""
    echo -e "${BLUE}Data directories created:${NC}"
    echo "  ~/.colony/reputation/  - Agent reputation data"
    echo "  ~/.colony/patterns/    - Pattern library"
    echo "  ~/.colony/memory/      - Chunked conversations"
    echo ""
    echo -e "${GREEN}🚀 Colony is ready! Use it with:${NC}"
    echo "  /colony status"
    echo "  /colony deploy --team code-review --task \"Review code\""
    echo ""
else
    echo -e "${RED}❌ Installation failed${NC}"
    echo "Symlink was not created correctly"
    exit 1
fi

# Check for RLM skill (optional dependency)
echo -e "${YELLOW}🔍 Checking for RLM skill (optional)...${NC}"
if [ -d "$HOME/.claude/skills/rlm" ]; then
    echo -e "${GREEN}✅ RLM skill found - memory chunking will use RLM${NC}"
else
    echo -e "${YELLOW}⚠️  RLM skill not found - memory will use fallback chunking${NC}"
    echo "   Install RLM for enhanced memory: https://github.com/anthropics/rlm"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${BLUE}========================================${NC}"
