"""
Classes for working with Open edX course data directly from MongoDB.
"""

from bson import ObjectId
from pymongo import MongoClient


class OpenEdxCourseDataQuery:
    """
    Query Open edX course authoring data directly from MongoDB.
    """

    def __init__(
        self,
        host="localhost",
        port=27017,
        database="openedx",
        user=None,
        password=None,
        collection_prefix="modulestore",
    ):
        """
        Initialize MongoDB connection.

        Args:
            host: MongoDB host (default: 'localhost')
            port: MongoDB port (default: 27017)
            database: Database name (default: 'openedx')
            user: MongoDB username (optional)
            password: MongoDB password (optional)
            collection_prefix: Collection prefix (default: 'modulestore')
        """
        # Build connection string
        if user and password:
            connection_string = f"mongodb://{user}:{password}@{host}:{port}/{database}"
        else:
            connection_string = f"mongodb://{host}:{port}/{database}"

        # Connect to MongoDB
        self.client = MongoClient(connection_string)
        self.db = self.client[database]

        # Get collection references
        self.course_index = self.db[f"{collection_prefix}.active_versions"]
        self.structures = self.db[f"{collection_prefix}.structures"]
        self.definitions = self.db[f"{collection_prefix}.definitions"]

    def get_course_index(self, org, course, run):
        """
        Get the course index entry for a specific course.

        Args:
            org: Organization identifier (e.g., 'OpenedX')
            course: Course identifier (e.g., 'DemoX')
            run: Course run identifier (e.g., 'DemoCourse')

        Returns:
            dict: Course index document or None if not found
        """
        return self.course_index.find_one({"org": org, "course": course, "run": run})

    def get_structure(self, structure_id):
        """
        Get a structure document by its ObjectId.

        Args:
            structure_id: ObjectId or string representation

        Returns:
            dict: Structure document or None if not found
        """
        if isinstance(structure_id, str):
            structure_id = ObjectId(structure_id)

        return self.structures.find_one({"_id": structure_id})

    def get_course_structure(
        self, org, course, run, branch="published", include_definitions=False
    ):
        """
        Get the full course structure for a specific branch.

        Args:
            org: Organization identifier
            course: Course identifier
            run: Course run identifier
            branch: 'published' or 'draft' (default: 'published')
            include_definitions: If True, fetch and include definition content for
                each block (default: False)

        Returns:
            dict: Complete course data including index and structure
        """
        # Get course index
        course_index = self.get_course_index(org, course, run)

        if not course_index:
            return {
                "success": False,
                "error": f"Course not found: {org}/{course}/{run}",
                "course_index": None,
                "structure": None,
            }

        # Get structure ID for the specified branch
        branch_key = f"{branch}-branch"
        structure_id = course_index.get("versions", {}).get(branch_key)

        if not structure_id:
            return {
                "success": False,
                "error": f"No {branch} branch found for course",
                "course_index": course_index,
                "structure": None,
            }

        # Get the structure
        structure = self.get_structure(structure_id)

        # Optionally enrich with definitions
        if include_definitions and structure:
            structure = self.enrich_structure_with_definitions(structure)

        return {
            "success": True,
            "course_index": course_index,
            "structure": structure,
            "structure_id": structure_id,
        }

    def get_both_branches(self, org, course, run):
        """
        Get both draft and published structures for a course.

        Args:
            org: Organization identifier
            course: Course identifier
            run: Course run identifier

        Returns:
            dict: Course data with both draft and published structures
        """
        course_index = self.get_course_index(org, course, run)

        if not course_index:
            return {
                "success": False,
                "error": f"Course not found: {org}/{course}/{run}",
            }

        versions = course_index.get("versions", {})

        result = {
            "success": True,
            "course_index": course_index,
            "draft": None,
            "published": None,
        }

        # Get draft structure
        draft_id = versions.get("draft-branch")
        if draft_id:
            result["draft"] = {
                "structure_id": draft_id,
                "structure": self.get_structure(draft_id),
            }

        # Get published structure
        published_id = versions.get("published-branch")
        if published_id:
            result["published"] = {
                "structure_id": published_id,
                "structure": self.get_structure(published_id),
            }

        return result

    def get_definition(self, definition_id):
        """
        Get a definition document (content payload) by its ObjectId.

        Args:
            definition_id: ObjectId or string representation

        Returns:
            dict: Definition document or None if not found
        """
        if isinstance(definition_id, str):
            definition_id = ObjectId(definition_id)

        return self.definitions.find_one({"_id": definition_id})

    def get_definitions_bulk(self, definition_ids):
        """
        Get multiple definition documents at once.

        Args:
            definition_ids: List of ObjectId or string representations

        Returns:
            dict: Dictionary mapping definition_id to definition document
        """
        # Convert strings to ObjectIds
        object_ids = []
        for def_id in definition_ids:
            if isinstance(def_id, str):
                object_ids.append(ObjectId(def_id))
            else:
                object_ids.append(def_id)

        # Fetch all definitions in one query
        definitions = self.definitions.find({"_id": {"$in": object_ids}})

        # Create a mapping of id -> definition
        return {str(defn["_id"]): defn for defn in definitions}

    def enrich_structure_with_definitions(self, structure):
        """
        Enrich a structure by adding definition content to each block.

        Args:
            structure: Structure document

        Returns:
            dict: Structure with definitions added to each block
        """
        if not structure or "blocks" not in structure:
            return structure

        # Collect all unique definition IDs
        definition_ids = set()
        for block in structure["blocks"]:
            if "definition" in block and block["definition"]:
                definition_ids.add(block["definition"])

        if not definition_ids:
            return structure

        # Fetch all definitions at once
        definitions_map = self.get_definitions_bulk(list(definition_ids))

        # Enrich each block with its definition
        enriched_structure = structure.copy()
        enriched_structure["blocks"] = []

        for block in structure["blocks"]:
            enriched_block = block.copy()
            if "definition" in block and block["definition"]:
                def_id = str(block["definition"])
                if def_id in definitions_map:
                    enriched_block["definition_content"] = definitions_map[def_id]
            enriched_structure["blocks"].append(enriched_block)

        return enriched_structure

    def list_all_courses(self, org=None):
        """
        List all courses in the system, or in an organization.

        Args:
            org (str, optional): Organization identifier

        Returns:
            list: List of course index documents
        """
        if org:
            return list(
                self.course_index.find(
                    {"org": org},
                    {"org": 1, "course": 1, "run": 1, "versions": 1, "edited_on": 1},
                )
            )

        return list(
            self.course_index.find(
                {}, {"org": 1, "course": 1, "run": 1, "versions": 1, "edited_on": 1}
            )
        )

    def get_root_block(self, structure):
        """
        Get the root block from a structure.

        Args:
            structure: Structure document

        Returns:
            tuple: (block_type, block_id) or (None, None) if not found
        """
        if not structure or "root" not in structure:
            return None, None

        root = structure["root"]

        # root can be stored as a list [block_type, block_id] or dict
        if isinstance(root, list):
            return root[0], root[1] if len(root) >= 2 else None
        elif isinstance(root, dict):
            return root.get("block_type"), root.get("block_id")
        else:
            return None, None

    def get_block_from_structure(self, structure, block_type=None, block_id=None):
        """
        Extract specific blocks from a structure.

        Args:
            structure: Structure document
            block_type: Filter by block type (e.g., 'course', 'chapter', 'sequential')
            block_id: Filter by specific block_id

        Returns:
            list: Matching blocks
        """
        if not structure or "blocks" not in structure:
            return []

        blocks = structure["blocks"]
        results = []

        for block in blocks:
            if block_type and block.get("block_type") != block_type:
                continue
            if block_id and block.get("block_id") != block_id:
                continue
            results.append(block)

        return results

    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
