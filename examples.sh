#!/bin/bash
# Example usage commands for the Open edX Course Data Query Tool

echo "=========================================="
echo "Open edX Course Data Query Tool Examples"
echo "=========================================="
echo ""

# Set your MongoDB connection details here
MONGO_HOST="localhost"
MONGO_PORT="27017"
MONGO_DATABASE="openedx"
# Uncomment and set if authentication is required
# MONGO_USER="edxapp"
# MONGO_PASSWORD="password"

# Set your course details here
ORG="OpenedX"
COURSE="DemoX"
RUN="DemoCourse"

# Build base command with connection parameters
BASE_CMD="uv run main.py --host $MONGO_HOST --port $MONGO_PORT --database $MONGO_DATABASE"

# Add authentication if needed
if [ ! -z "$MONGO_USER" ] && [ ! -z "$MONGO_PASSWORD" ]; then
    BASE_CMD="$BASE_CMD --user $MONGO_USER --password $MONGO_PASSWORD"
fi

echo "=== Example 1: List all courses ==="
echo "Command: $BASE_CMD list-courses"
echo ""
$BASE_CMD list-courses
echo ""
echo ""

echo "=== Example 2: List all courses and save to JSON ==="
echo "Command: $BASE_CMD list-courses --output courses.json"
echo ""
$BASE_CMD list-courses --output .
echo ""
echo ""

echo "=== Example 3: Get published version of a specific course ==="
echo "Command: $BASE_CMD get-course --org $ORG --course $COURSE --run"
echo ""
$BASE_CMD get-course --org $ORG --course $COURSE --run $RUN
echo ""
echo ""

echo "=== Example 4: Get draft version of a specific course ==="
echo "Command: $BASE_CMD get-course --org $ORG --course $COURSE --run --branch draft"
echo ""
$BASE_CMD get-course --org $ORG --course $COURSE --run --branch draft
echo ""
echo ""

echo "=== Example 5: Export course structure to JSON ==="
echo "Command: $BASE_CMD get-course --org $ORG --course $COURSE --run --output ."
echo ""
$BASE_CMD get-course --org $ORG --course $COURSE --run $RUN --output .
echo ""
echo ""

echo "=== Example 5b: Get course with definition content ==="
echo "Command: $BASE_CMD get-course --org $ORG --course $COURSE --run $RUN --include-definitions"
echo ""
$BASE_CMD get-course --org $ORG --course $COURSE --run $RUN --include-definitions
echo ""
echo ""

echo "=== Example 5c: Export course with definition content to JSON ==="
echo "Command: $BASE_CMD get-course --org $ORG --course $COURSE --run $RUN --include-definitions --output ."
echo ""
$BASE_CMD get-course --org $ORG --course $COURSE --run $RUN --include-definitions --output .
echo ""
echo ""

echo "=== Example 6: Export all course structures to JSON ==="
echo "Command: $BASE_CMD get-courses --output ."
echo ""
$BASE_CMD get-courses --output .
echo ""
echo ""

echo "=== Example 6b: Export all courses in an org ==="
echo "Command: $BASE_CMD get-courses --org $ORG"
echo ""
$BASE_CMD get-courses --org $ORG
echo ""
echo ""

echo "=== Example 6c: Export all courses in an org to JSON ==="
echo "Command: $BASE_CMD get-courses --org $ORG --include-definitions"
echo ""
$BASE_CMD get-courses --org $ORG --include-definitions
echo ""
echo ""

echo "=== Example 6d: Get draft version of all courses ==="
echo "Command: $BASE_CMD get-courses --branch draft"
echo ""
$BASE_CMD get-courses --branch draft
echo ""
echo ""


echo "=========================================="
echo "Examples completed!"
echo "=========================================="
echo ""
echo "Generated files (if created):"
ls -lh *.json 2>/dev/null || echo "No JSON files generated"
