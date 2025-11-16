"""
CLI command for enriching team data with colors and aliases.

Usage:
    # Enrich all teams
    python -m app.cli.enrich_teams

    # Dry run (no database writes)
    python -m app.cli.enrich_teams --dry-run

    # Force re-enrichment (update even if already enriched)
    python -m app.cli.enrich_teams --force

    # Specific sport
    python -m app.cli.enrich_teams --sport ncaam

    # Verbose output
    python -m app.cli.enrich_teams --verbose
"""

import argparse
import logging
import sys

import structlog
from sqlmodel import Session, create_engine

from app.core.config import settings
from app.services.team_enricher import EnrichmentReport, TeamEnricher

logger = structlog.get_logger(__name__)


def main() -> None:
    """Main CLI entry point for team enrichment."""
    parser = argparse.ArgumentParser(
        description="Enrich team data with colors and aliases from external sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--sport",
        type=str,
        default="ncaam",
        help="Sport code to enrich (default: ncaam)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without committing changes to database",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-enrichment even if data already exists",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--delete-duplicates",
        action="store_true",
        help="Delete duplicate teams (keeps slug-based IDs, removes numeric seed data IDs)",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        )

    # Print header
    print("=" * 60)
    print("GamePulse Team Enrichment Service")
    print("=" * 60)
    print(f"Sport: {args.sport}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Force: {args.force}")
    if args.delete_duplicates:
        print(f"Delete Duplicates: {args.delete_duplicates}")
    print("=" * 60)
    print()

    try:
        # Create database engine and session
        engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

        with Session(engine) as session:
            # Initialize enricher
            enricher = TeamEnricher(session)

            # Run enrichment (unless only deleting duplicates)
            if not args.delete_duplicates:
                print("Fetching external data sources...")
                report = enricher.enrich_all_teams(
                    sport=args.sport,
                    dry_run=args.dry_run,
                    force=args.force,
                )
            else:
                # Skip enrichment, just detect duplicates
                from sqlmodel import select

                from app.models.dim_team import DimTeam

                stmt = select(DimTeam).where(
                    DimTeam.sport == args.sport, DimTeam.is_current
                )
                teams = list(session.exec(stmt).all())
                duplicates = enricher.detect_duplicates(teams)

                # Create minimal report for display
                mock_report = EnrichmentReport(
                    teams_processed=len(teams),
                    teams_enriched=0,
                    teams_skipped=len(teams),
                    teams_failed=0,
                    colors_added=0,
                    aliases_added=0,
                    duplicates_found=len(duplicates),
                    duplicate_groups=duplicates,
                    errors=[],
                )
                report = mock_report

            # Print report
            print()
            print("=" * 60)
            print("Enrichment Report")
            print("=" * 60)
            print(f"Teams Processed:  {report.teams_processed}")
            print(f"Teams Enriched:   {report.teams_enriched}")
            print(f"Teams Skipped:    {report.teams_skipped}")
            print(f"Teams Failed:     {report.teams_failed}")
            print(f"Colors Added:     {report.colors_added}")
            print(f"Aliases Added:    {report.aliases_added}")
            if report.duplicates_found > 0:
                print(
                    f"⚠️  Duplicates:      {report.duplicates_found} name(s) with multiple team_id values"
                )
            print("=" * 60)

            if report.duplicate_groups and len(report.duplicate_groups) > 0:
                print()
                print("⚠️  Duplicate Teams Detected:")
                print()
                for dup in report.duplicate_groups:
                    print(f"  • {dup['team_name']}: {dup['count']} teams found")
                    for team_id in dup["team_ids"]:
                        print(f"    - {team_id}")
                print()
                print("Note: Duplicates occur when both seed data (numeric IDs) and")
                print("NCAA API ingestion (slug IDs) create separate team records.")
                print("Both versions are enriched independently.")
                print()

            if report.errors:
                print()
                print("Errors:")
                for error in report.errors:
                    print(f"  - {error}")
                print()

            # Delete duplicates if requested
            deletion_result = None
            if args.delete_duplicates and report.duplicates_found > 0:
                print()
                print("=" * 60)
                print("Deleting Duplicate Teams")
                print("=" * 60)
                print("Strategy: Keep slug-based IDs, delete numeric seed data IDs")
                print()

                deletion_result = enricher.delete_duplicate_teams(dry_run=args.dry_run)

                print()
                print("Deletion Summary:")
                print(f"  Teams Deleted:     {deletion_result['teams_deleted']}")
                print(
                    f"  Groups Resolved:   {deletion_result['duplicate_groups_resolved']}"
                )
                print()
                if deletion_result["deleted_team_ids"]:
                    print("Deleted team_ids:")
                    for team_id in deletion_result["deleted_team_ids"]:
                        print(f"  - {team_id}")
                    print()

            if args.dry_run:
                print()
                print("🔍 DRY RUN - No changes committed to database")
                print()
            else:
                print()
                if (
                    args.delete_duplicates
                    and deletion_result
                    and deletion_result["teams_deleted"] > 0
                ):
                    print(
                        f"✅ Deleted {deletion_result['teams_deleted']} duplicate teams"
                    )
                else:
                    print("✅ Enrichment completed successfully")
                print()

            # Exit with appropriate code
            if report.teams_failed > 0:
                sys.exit(1)
            else:
                sys.exit(0)

    except KeyboardInterrupt:
        print()
        print("❌ Enrichment cancelled by user")
        sys.exit(130)

    except Exception as e:
        print()
        print(f"❌ Critical error: {e}")
        logger.exception("enrich_teams_cli.critical_error")
        sys.exit(1)


if __name__ == "__main__":
    main()
