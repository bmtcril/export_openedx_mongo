# OpenOpenedX Course Data Query Tool

A standalone CLI tool to query OpenOpenedX course authoring data directly from MongoDB without anyOpenedX-platform dependencies.

## Features

- Query course data directly from MongoDB using PyMongo
- NoOpenedX-platform installation required
- Support for both draft and published branches
- Export course data to JSON files
- Operate on single courses or all courses in the database

## Quick Links

- **[Example Scripts](examples.sh)** - Ready-to-run examples
- **[Block definitions](DEFINITIONS_FEATURE.md)** - Information about working with block contents


## Installation

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (this will build and install the package)
uv sync

# Run the CLI
uv run uv run main.py --help

# Or use the installed command
uv run openedx-course-query --help
```

## Requirements

- Python 3.12+
- PyMongo 4.x
- Click 8.x

## Quick Start

```bash
# List all courses
uv run main.py list-courses

# Get a high level information on a specific course
uv run main.py get-course --org OpenedX --course DemoX --run DemoCourse 

# Dump all course and block data for an org to JSON files in the tmp dir
uv run main.py get-courses --org $ORG --include-definitions --output /tmp/
```

For more examples, see the [examples.sh](examples.sh).

## Usage

The CLI tool provides three main subcommands:

### Global Options

These options can be used with any subcommand:

```bash
--host TEXT              MongoDB host (default: localhost)
--port INTEGER           MongoDB port (default: 27017)
--database TEXT          Database name (default: openedx)
--user TEXT              MongoDB username
--password TEXT          MongoDB password
--collection-prefix TEXT Collection prefix (default: modulestore)
```

### Subcommands

#### 1. `get-course` - Get Course Structure

Retrieves the complete course structure for a single specific course and branch.

**Required options:** `--org`, `--course`, `--run` (either as global options or environment)

```bash
# Get published version of a course
uv run main.py get-course --org OpenedX --course DemoX --run DemoCourse 

# Get draft version
uv run main.py get-course --org OpenedX --course DemoX --run DemoCourse --branch draft

# Include definition content for each block
uv run main.py get-course --org OpenedX --course DemoX --run DemoCourse --include-definitions

# Export to JSON file
uv run main.py get-course --org OpenedX --course DemoX --run DemoCourse --output /tmp/

# Get course with block definitions and export
uv run main.py get-course --org OpenedX --course DemoX --run DemoCourse \
    --include-definitions --output /tmp/

# With MongoDB authentication
uv run main.py --host mongodb.example.com --userOpenedXapp --password secret \
    get-course --org OpenedX --course DemoX --run DemoCourse
```

**Options:**
- `--branch [published|draft]` - Branch to query (default: published)
- `--include-definitions` - Include definition content (actual content payloads) for each block
- `--output, -o PATH` - Output JSON directory, files are created as org-course-run.json

#### 1. `get-courses` - Get Course Structure for many courses

Retrieves the complete course structure for all courses or courses in a specific org, 
filtered by branch.

**Required options:** None

```bash
# Get published version of all courses
uv run main.py get-courses

# Get draft version
uv run main.py get-courses --branch draft

# Include definition content for each block in every course in an org
uv run main.py get-courses --org OpenedX --include-definitions

# Export to JSON files, one for each course named {org}-{course}-{run}.json
uv run main.py get-courses --output /tmp/

# Get all courses with block definitions and export
uv run main.py get-courses --include-definitions --output /tmp/

# With MongoDB authentication
uv run main.py --host mongodb.example.com --user app --password secret \
    get-courses --org OpenedX 
```

**Options:**
- `--branch [published|draft]` - Branch to query (default: published)
- `--include-definitions` - Include definition content (actual content payloads) for each block
- `--output, -o PATH` - Output JSON directory, files are created as {org}-{course}-{run}.json


#### 3. `list-courses` - List All Courses

Lists all courses in the database or a specific org if org is provided. Optionally
writes the list out to a single output file named courses.json in the given --output dir.

```bash
# List all courses
uv run main.py list-courses

# List courses for a specific org
uv run main.py list-courses --org OpenedX 

# Export to JSON
uv run main.py list-courses --output /tmp/

# With custom database
uv run main.py --database OpenedX list-courses
```

**Options:**
- `--output, -o PATH` - Output JSON directory, output file is `courses.json`


## MongoDB Connection

### Default Connection

By default, the tool connects to:
- Host: `localhost`
- Port: `27017`
- Database: `openedx`
- Collections: `modulestore.active_versions`, `modulestore.structures`, `modulestore.definitions`

### Custom Connection

You can override any connection parameter:

```bash
uv run main.py \
    --host mongodb.example.com \
    --port 27018 \
    --database my_openedx_db \
    --user admin \
    --password secret123 \
    --collection-prefix courseware \
    list-courses
```

### Environment Variables

You can also use environment variables for sensitive data:

```bash
export MONGO_USER=edxapp
export MONGO_PASSWORD=secret

# Then reference in your script or use a wrapper
uv run main.py --user $MONGO_USER --password $MONGO_PASSWORD list-courses
```

## MongoDB Data Structure

### Collections

The tool queries three main MongoDB collections:

1. **`modulestore.active_versions`** - Course index mapping courses to structure versions
2. **`modulestore.structures`** - Course structure data containing all XBlocks (block metadata, settings, and children)
3. **`modulestore.definitions`** - Content definitions (actual content payloads like HTML, problem text, video URLs, etc.)

**Note:** The definitions collection is only queried when using the `--include-definitions` flag with the `get-course` command.

### Course Identification

Courses are identified by a three-part key:
- `org` - Organization (e.g., "OpenedX", "MIT", "Harvard")
- `course` - Course ID (e.g., "DemoX", "CS50")
- `run` - Course run (e.g., "DemoCourse", "2024_Fall")

### Branches

OpenOpenedX Split MongoDB stores two branches per course:
- **`published-branch`** - The live, student-facing version
- **`draft-branch`** - The authoring/editing version

### Structure Format

**Important:** The `root` field in structure documents is stored as a list:
```python
"root": ["block_type", "block_id"]  # e.g., ["course", "course"]
```

The `OpenEdxCourseDataQuery` class provides a `get_root_block(structure)` helper method that handles this format and returns `(block_type, block_id)` as a tuple.

### Block Definitions

Each block in a structure has a `definition` field (ObjectId) that references a document in the `definitions` collection containing the actual content:

- **Without `--include-definitions`**: Blocks include only the definition ObjectId reference
- **With `--include-definitions`**: Blocks include a `definition_content` field with the full definition document

**Example definition content:**
- HTML blocks: `{"data": "<p>HTML content here</p>"}`
- Video blocks: `{"data": {"youtube_id_1_0": "abc123", "youtube": "1.00:abc123"}}`
- Problem blocks: `{"data": "<problem>...problem XML...</problem>"}`

## Output Format

### JSON Export Structure

When using `--output`, the tool exports data in JSON format with automatic type conversion:
- **ObjectIds** are converted to strings (e.g., `ObjectId("507f...")` → `"507f..."`)
- **datetime objects** are converted to ISO 8601 format (e.g., `datetime(2024, 1, 15, 10, 30)` → `"2024-01-15T10:30:00"`)

#### Course Structure Export (`get-course`)

```json
{
  "success": true,
  "course_index": {
    "_id": "507f1f77bcf86cd799439011",
    "org": "edX",
    "course": "DemoX",
    "run": "Demo_Course",
    "edited_on": "2024-01-15T10:30:00",
    "last_update": "2024-01-20T14:45:30",
    "versions": {
      "draft-branch": "507f191e810c19729de860ea",
      "published-branch": "507f1f77bcf86cd799439011"
    }
  },
  "structure": {
    "_id": "507f1f77bcf86cd799439011",
    "blocks": [
      {
        "block_type": "html",
        "block_id": "abc123",
        "definition": "507f...",
        "fields": {...},
        "definition_content": {  // Only present with --include-definitions
          "_id": "507f...",
          "block_type": "html",
          "fields": {
            "data": "<p>Actual HTML content</p>"
          }
        }
      }
    ],
    "root": ["course", "course"]
  },
  "structure_id": "507f1f77bcf86cd799439011"
}
```

## Programmatic Usage

You can also use the `OpenEdxCourseDataQuery` class directly in your Python code:

```python
from course_data import OpenEdxCourseDataQuery

# Initialize connection
query = OpenEdxCourseDataQuery(
    host='localhost',
    port=27017,
    database='openedx',
    user='edxapp',
    password='password'
)

# Get course structure
result = query.get_course_structure(
    org='edX',
    course='DemoX',
    run='Demo_Course',
    branch='published'
)

# Get course structure with definitions
result_with_defs = query.get_course_structure(
    org='edX',
    course='DemoX',
    run='Demo_Course',
    branch='published',
    include_definitions=True
)

if result['success']:
    print(f"Found {len(result['structure']['blocks'])} blocks")
    
    # Access definition content if included
    if 'definition_content' in result['structure']['blocks'][0]:
        print("Definitions are included!")

# Always close the connection
query.close()
```

## Troubleshooting

### Course Not Found

```
✗ Course not found:OpenedX/DemoX/Demo_Course
```

**Solution:** 
- Verify the org, course, and run identifiers are correct (case-sensitive)
- Check that the course exists in the database
- Ensure you're connecting to the correct database

### No Published Branch

```
✗ Error: No published branch found for course
```

**Solution:** The course may only have a draft version. Try querying the draft branch:

```bash
uv run main.py get-course --org OpenedX --course DemoX --run DemoCourse -branch draft
```

### JSON Serialization Issues

**Issue:** When working with the exported JSON data, you may notice datetime and ObjectId formats.

**Note:** All MongoDB-specific types are automatically converted for JSON compatibility:
- **ObjectIds** are converted to strings (e.g., `"507f1f77bcf86cd799439011"`)
- **datetime objects** are converted to ISO 8601 format (e.g., `"2024-01-15T10:30:00"`)

This makes the exported JSON compatible with standard JSON parsers and other tools.

## License

See [License](LICENSE)
