# Definitions Feature Documentation

## Overview

The `--include-definitions` flag is a powerful feature that allows you to fetch the actual content payloads for all blocks in a course structure. This is essential when you need the complete course data including HTML content, problem definitions, video metadata, and other learning materials.

## What Are Definitions?

In Open edX's Split MongoDB architecture, course data is separated into two main components:

1. **Structure** (`modulestore.structures`) - Contains:
   - Block metadata (type, ID, display names)
   - Block relationships (parent-child hierarchy)
   - Block settings (fields like due dates, grading settings)
   - References to definitions (ObjectIds)

2. **Definitions** (`modulestore.definitions`) - Contains:
   - Actual content payloads
   - HTML content for HTML blocks
   - Problem XML for problem blocks
   - Video metadata (YouTube IDs, transcripts)
   - Other content-specific data

## Output Comparison

### Without `--include-definitions` (Default)

```json
{
  "success": true,
  "structure": {
    "blocks": [
      {
        "block_type": "html",
        "block_id": "abc123",
        "definition": "507f1f77bcf86cd799439011",
        "fields": {
          "display_name": "Introduction"
        }
      }
    ]
  }
}
```

### With `--include-definitions`

All MongoDB types are automatically converted for JSON compatibility:
- **ObjectIds** → strings (e.g., `"507f1f77bcf86cd799439011"`)
- **datetime** → ISO 8601 strings (e.g., `"2024-01-15T10:30:00"`)

```json
{
  "success": true,
  "structure": {
    "blocks": [
      {
        "block_type": "html",
        "block_id": "abc123",
        "definition": "507f1f77bcf86cd799439011",
        "fields": {
          "display_name": "Introduction"
        },
        "definition_content": {
          "_id": "507f1f77bcf86cd799439011",
          "block_type": "html",
          "fields": {
            "data": "<p>Welcome to the course!</p><h2>Getting Started</h2>"
          },
          "edit_info": {
            "edited_by": 10,
            "edited_on": "2024-01-15T10:30:00"
          }
        }
      }
    ]
  }
}
```

## Definition Content by Block Type

Different block types store different content in their definitions:

### HTML Blocks
```json
{
  "definition_content": {
    "block_type": "html",
    "fields": {
      "data": "<p>HTML content here</p>"
    }
  }
}
```

### Video Blocks
```json
{
  "definition_content": {
    "block_type": "video",
    "fields": {
      "youtube_id_1_0": "dQw4w9WgXcQ",
      "youtube": "1.00:dQw4w9WgXcQ",
      "html5_sources": ["https://..."],
      "transcripts": {"en": "..."}
    }
  }
}
```

### Problem Blocks
```json
{
  "definition_content": {
    "block_type": "problem",
    "fields": {
      "data": "<problem>...OLX problem definition...</problem>"
    }
  }
}
```

### Discussion Blocks
```json
{
  "definition_content": {
    "block_type": "discussion",
    "fields": {
      "discussion_id": "unique_discussion_id",
      "discussion_category": "General",
      "discussion_target": "Course Discussion"
    }
  }
}
```

## Performance Considerations

### Without Definitions (Default)
- **Queries:** 2 database queries (course_index + structure)
- **Speed:** Very fast (~10-50ms)
- **Data Size:** Small (typically 100KB-2MB)
- **Use Case:** Course structure analysis, navigation, metadata

### With Definitions
- **Queries:** 3 database queries (course_index + structure + bulk definitions)
- **Speed:** Moderate (~100-500ms depending on course size)
- **Data Size:** Large (typically 5MB-50MB+ some courses are much larger)
- **Use Case:** Data mining course data

### Optimization

The implementation uses **bulk fetching** to minimize database queries:

1. Collect all unique definition IDs from all blocks
2. Fetch ALL definitions in a single MongoDB query using `$in` operator
3. Map definitions to blocks in memory

This is much more efficient than fetching definitions one-by-one per block.

## Programmatic Usage

```python
from course_data import OpenEdxCourseDataQuery

query = OpenEdxCourseDataQuery(
    host='localhost',
    port=27017,
    database='openedx'
)

# Get course with definitions
result = query.get_course_structure(
    org='edX',
    course='DemoX',
    run='Demo_Course',
    branch='published',
    include_definitions=True  # Enable definitions fetching
)

if result['success']:
    for block in result['structure']['blocks']:
        print(f"Block: {block['block_type']} - {block.get('block_id')}")
        
        # Check if definition content is included
        if 'definition_content' in block:
            def_content = block['definition_content']
            print(f"  Has definition content: {def_content.get('block_type')}")
            
            # Access the actual content
            if 'fields' in def_content and 'data' in def_content['fields']:
                content = def_content['fields']['data']
                print(f"  Content preview: {content[:100]}...")

query.close()
```


### 1. Content Analysis
Analyze course content (e.g., find all videos, count problems):

```python
result = query.get_course_structure(..., include_definitions=True)

# Count block types with content
video_count = sum(1 for b in result['structure']['blocks'] 
                  if b['block_type'] == 'video')

# Extract all HTML content
html_content = [
    b['definition_content']['fields']['data']
    for b in result['structure']['blocks']
    if b['block_type'] == 'html' and 'definition_content' in b
]
```

### 2. Content Search
Search across all course content:

```python
result = query.get_course_structure(..., include_definitions=True)

search_term = "machine learning"
matches = []

for block in result['structure']['blocks']:
    if 'definition_content' in block:
        content = str(block['definition_content'].get('fields', {}))
        if search_term.lower() in content.lower():
            matches.append({
                'block_type': block['block_type'],
                'block_id': block['block_id'],
                'display_name': block.get('fields', {}).get('display_name', 'N/A')
            })
```

## API Methods

### High-Level Method

```python
query.get_course_structure(org, course, run, branch='published', include_definitions=False)
```

Returns structure with optional definition content.

### Low-Level Methods

```python
# Get single definition
definition = query.get_definition(definition_id)

# Get multiple definitions efficiently (bulk)
definitions_map = query.get_definitions_bulk([id1, id2, id3, ...])

# Enrich existing structure with definitions
enriched = query.enrich_structure_with_definitions(structure)
```

## Troubleshooting

### Large Export Files

**Problem:** Export files are very large (>100MB)

**Solution:** 
- Only use `--include-definitions` when you need the content
- Consider exporting structure first, then selectively fetch definitions
- Use compression: `gzip course_full.json`

### Slow Queries

**Problem:** Query takes a long time

**Solution:**
- Ensure MongoDB has indexes on `_id` fields (should be automatic)
- Use `--include-definitions` only for courses you're actively working with
- Consider course size (1000+ blocks will be slower)

### Missing Definitions

**Problem:** Some blocks don't have `definition_content` even with flag

**Solution:**
- This is normal! Not all blocks have definitions
- Container blocks (chapter, sequential, vertical) often don't have content definitions
- Use `blocks_with_defs` count from output to verify

## Best Practices

1. **Default to without definitions** - Only use `--include-definitions` when you need the actual content

2. **Use for specific courses** - Avoid bulk exports with definitions for all courses unless necessary

3. **Combine with output flag** - Always export to JSON when using `--include-definitions` for later processing

4. **Check file sizes** - Monitor output file sizes, especially for large courses

5. **Process incrementally** - For very large courses, consider processing blocks incrementally rather than loading entire JSON
