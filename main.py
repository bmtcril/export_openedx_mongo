"""
CLI tool to query Open edX course data directly from MongoDB.
"""

import json
import os
from datetime import datetime

import click
from bson import ObjectId
from click.exceptions import ClickException

from course_data import OpenEdxCourseDataQuery


def convert_to_json_serializable(obj):
    """
    Convert ObjectId and datetime objects to JSON serializable format.
    """
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _dump_course_data(query, org, course, run, branch, include_definitions, output):
    """
    Get course structure, output to stdout and optionally to a JSON file.
    """
    result = query.get_course_structure(
        org=org,
        course=course,
        run=run,
        branch=branch,
        include_definitions=include_definitions,
    )

    if result["success"]:
        click.echo(f"✓ Course found: {org}/{course}/{run}")
        click.echo(f"  Structure ID: {result['structure_id']}")
        click.echo(f"  Number of blocks: {len(result['structure']['blocks'])}")

        if include_definitions:
            # Count how many blocks have definitions
            blocks_with_defs = sum(
                1
                for block in result["structure"]["blocks"]
                if "definition_content" in block
            )
            click.echo(f"  Blocks with definitions: {blocks_with_defs}")

        # Get the root course block
        root_block_type, root_block_id = query.get_root_block(result["structure"])

        course_blocks = query.get_block_from_structure(
            result["structure"],
            block_type=root_block_type,
            block_id=root_block_id,
        )

        if course_blocks:
            course_block = course_blocks[0]
            display_name = course_block.get("fields", {}).get("display_name", "N/A")
            click.echo(f"  Display name: {display_name}")

        if output:
            with open(output, "w") as f:
                json.dump(result, f, indent=2, default=convert_to_json_serializable)
            click.echo(f"\n✓ Course data written to {output}")
    else:
        click.echo(f"✗ Error: {result['error']}", err=True)
        raise ClickException(f"✗ Error: {result['error']}")


@click.group()
@click.option("--host", default=None, help="MongoDB host (default: localhost)")
@click.option("--port", default=None, type=int, help="MongoDB port (default: 27017)")
@click.option("--database", default=None, help="Database name (default: openedx)")
@click.option("--user", default=None, help="MongoDB username")
@click.option("--password", default=None, help="MongoDB password")
@click.option(
    "--collection-prefix", default=None, help="Collection prefix (default: modulestore)"
)
@click.pass_context
def cli(ctx, host, port, database, user, password, collection_prefix):
    """
    Open edX Course Data Query Tool

    Query Open edX course authoring data directly from MongoDB.
    """
    # Store connection parameters in context
    ctx.ensure_object(dict)

    # Build kwargs, only including non-None values so defaults can take precedence
    kwargs = {}
    if host is not None:
        kwargs["host"] = host
    if port is not None:
        kwargs["port"] = port
    if database is not None:
        kwargs["database"] = database
    if user is not None:
        kwargs["user"] = user
    if password is not None:
        kwargs["password"] = password
    if collection_prefix is not None:
        kwargs["collection_prefix"] = collection_prefix

    ctx.obj["connection_kwargs"] = kwargs


@cli.command()
@click.option(
    "--org", default=None, help="Organization identifier (e.g., OpenedX) to filter to"
)
@click.option(
    "--branch",
    default="published",
    type=click.Choice(["published", "draft"]),
    help="Branch to query (default: published)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    help="Output JSON director, one json file per course will be created.",
)
@click.option(
    "--include-definitions",
    is_flag=True,
    help="Include definition content for each block",
)
@click.pass_context
def get_courses(ctx, org, branch, output, include_definitions):
    """
    Get published or draft version of course courses.

    - Retrieves the complete course structure for the specified branch of each course.
    - If org is not provided all courses will be retrieved.
    - Use --include-definitions to also fetch the content payload for each block.
    """

    if output:
        if not os.path.exists(output):
            os.makedirs(output, exist_ok=True)

    query = OpenEdxCourseDataQuery(**ctx.obj["connection_kwargs"])

    try:
        courses = query.list_all_courses(org)
        for course_doc in courses:
            # We need to use the org from the course document in case one wasn't
            # provided
            course_org = course_doc["org"]
            course = course_doc["course"]
            run = course_doc["run"]
            click.echo(
                f"  {course_doc['org']}/{course_doc['course']}/{course_doc['run']}"
            )
            file_output = (
                os.path.join(output, f"{course_org}-{course}-{run}.json")
                if output
                else None
            )

            _dump_course_data(
                query, course_org, course, run, branch, include_definitions, file_output
            )
    finally:
        query.close()


@cli.command()
@click.option("--org", default=None, help="Organization identifier (e.g., OpenedX)")
@click.option("--course", default=None, help="Course identifier (e.g., DemoX)")
@click.option("--run", default=None, help="Course run identifier (e.g., Demo_Course)")
@click.option(
    "--branch",
    default="published",
    type=click.Choice(["published", "draft"]),
    help="Branch to query (default: published)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    help="Output JSON director, one json file per course will be created.",
)
@click.option(
    "--include-definitions",
    is_flag=True,
    help="Include definition content for each block",
)
@click.pass_context
def get_course(ctx, org, course, run, branch, output, include_definitions):
    """
    Get published or draft version of a course.

    Retrieves the complete course structure for the specified branch.
    If org/course/run are not provided via options, this command will fail.
    Use --include-definitions to also fetch the content payload for each block.
    """

    if output:
        if not os.path.exists(output):
            os.makedirs(output, exist_ok=True)
        output = os.path.join(output, f"{org}-{course}-{run}.json")

    if not all([org, course, run]):
        click.echo(
            "Error: --org, --course, and --run are required for this command", err=True
        )
        ctx.exit(1)

    query = OpenEdxCourseDataQuery(**ctx.obj["connection_kwargs"])

    try:
        _dump_course_data(query, org, course, run, branch, include_definitions, output)
    finally:
        query.close()


@cli.command()
@click.option("--org", default=None, help="Organization identifier (e.g., OpenedX)")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file path")
@click.pass_context
def list_courses(ctx, org, output):
    """
    List all courses in the system, or in an organization.

    If the org option is provided, only courses from that specific organization
    will be listed. Otherwise, all courses in the database will be listed.
    """
    query = OpenEdxCourseDataQuery(**ctx.obj["connection_kwargs"])

    if output:
        if not os.path.exists(output):
            os.makedirs(output, exist_ok=True)
        output = os.path.join(output, "courses.json")

    courses = []

    try:
        courses = query.list_all_courses(org)

        click.echo(f"Found {len(courses)} course(s):\n")

        for course_doc in courses:
            click.echo(
                f"  {course_doc['org']}/{course_doc['course']}/{course_doc['run']}"
            )
            versions = course_doc.get("versions", {})

            draft_id = versions.get("draft-branch")
            published_id = versions.get("published-branch")

            if draft_id:
                click.echo(f"    Draft:     {draft_id}")
            if published_id:
                click.echo(f"    Published: {published_id}")

            click.echo()

        if output:
            with open(output, "w") as f:
                json.dump(courses, f, indent=2, default=convert_to_json_serializable)
            click.echo(f"✓ Course list written to {output}")
    finally:
        query.close()


if __name__ == "__main__":
    cli()
