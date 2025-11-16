"""
Team enrichment service for GamePulse.

Idempotently enriches team records with colors and aliases from external data sources.
Can be re-run safely multiple times without creating duplicates or data loss.

External Data Sources:
- NCAA team colors: GitHub (glidej/ncaa-team-colors) - 346 teams
- Aliases: Programmatically generated from team names + manual seed data

Features:
- Fuzzy team name matching to external datasets using RapidFuzz
- Idempotent updates (ON CONFLICT DO UPDATE pattern)
- Merge strategy for aliases (append new, preserve existing, no duplicates)
- Comprehensive logging and reporting
- Dry-run mode for validation

Usage:
    enricher = TeamEnricher(session)
    report = enricher.enrich_all_teams(dry_run=False, force=False)
    print(f"Enriched {report.teams_enriched} teams")
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from rapidfuzz import fuzz
from sqlmodel import Session, select

from app.models.dim_team import DimTeam

logger = structlog.get_logger(__name__)


@dataclass
class EnrichmentReport:
    """Report summarizing team enrichment results."""

    teams_processed: int = 0
    teams_enriched: int = 0
    colors_added: int = 0
    aliases_added: int = 0
    teams_skipped: int = 0
    teams_failed: int = 0
    duplicates_found: int = 0
    duplicate_groups: list[dict[str, Any]] | None = None
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        """Initialize lists if None."""
        if self.errors is None:
            self.errors = []
        if self.duplicate_groups is None:
            self.duplicate_groups = []


class TeamEnricher:
    """
    Idempotent team enrichment service.

    Enriches dim_team records with:
    - Primary and secondary colors from external datasets
    - Programmatically generated aliases for fuzzy matching
    - Optional manual seed data overrides for curated aliases

    Matching Strategy:
    - Uses RapidFuzz partial_ratio for team name matching
    - Threshold: 85/100 for high-confidence color matches
    - Falls back to programmatic generation if no external match

    Idempotency:
    - Merge strategy: Appends new aliases, preserves existing
    - Color updates: Only if source data available and field is NULL or force=True
    - Safe to run multiple times without data loss or duplicates

    Args:
        session: SQLModel database session
        colors_dataset_url: Optional custom URL for colors dataset
    """

    COLORS_DATASET_URL = "https://raw.githubusercontent.com/glidej/ncaa-team-colors/master/ncaa-team-colors.json"
    MATCH_THRESHOLD = 85  # High confidence for color matching
    FUZZY_MATCH_THRESHOLD = 75  # Slightly lower for name variations

    def __init__(
        self,
        session: Session,
        colors_dataset_url: str | None = None,
    ):
        """
        Initialize TeamEnricher with database session.

        Args:
            session: Database session for loading/updating teams
            colors_dataset_url: Optional custom URL for colors dataset
        """
        self.session = session
        self.colors_dataset_url = colors_dataset_url or self.COLORS_DATASET_URL
        self.colors_data: list[dict[str, Any]] | None = None
        self.seed_data: dict[str, dict[str, Any]] | None = None

    def fetch_colors_dataset(self) -> list[dict[str, Any]]:
        """
        Fetch NCAA team colors dataset from GitHub.

        Returns:
            List of team color dictionaries with keys:
            - name: Full team name (e.g., "Duke Blue Devils")
            - colors: List of hex codes ["#primary", "#secondary", ...]
            - slug: Team slug (e.g., "duke_blue_devils")

        Raises:
            httpx.HTTPError: If fetch fails
            ValueError: If JSON parsing fails
        """
        logger.info("fetch_colors_dataset.started", url=self.colors_dataset_url)

        try:
            response = httpx.get(self.colors_dataset_url, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            logger.info(
                "fetch_colors_dataset.success",
                teams_count=len(data),
                url=self.colors_dataset_url,
            )

            self.colors_data = data
            return data

        except httpx.HTTPError as e:
            logger.error(
                "fetch_colors_dataset.http_error",
                error=str(e),
                url=self.colors_dataset_url,
            )
            raise
        except ValueError as e:
            logger.error("fetch_colors_dataset.parse_error", error=str(e))
            raise

    def match_team_to_colors_dataset(
        self, team: DimTeam
    ) -> dict[str, str | None] | None:
        """
        Match a GamePulse team to external colors dataset using fuzzy matching.

        Matching logic:
        1. Try exact match on team name (case-insensitive)
        2. Try fuzzy match using RapidFuzz partial_ratio (>= MATCH_THRESHOLD)
        3. Return best match if confidence is high enough

        Args:
            team: DimTeam instance to match

        Returns:
            Dict with 'primary' and 'secondary' color hex codes, or None if no match

        Example:
            team.team_name = "Duke"
            dataset entry = {"name": "Duke Blue Devils", "colors": ["#003087", "#FFFFFF"]}
            returns: {"primary": "#003087", "secondary": "#FFFFFF"}
        """
        if not self.colors_data:
            logger.warning("match_team_to_colors_dataset.no_data", team_id=team.team_id)
            return None

        team_name_lower = team.team_name.lower()
        best_match = None
        best_score: float = 0.0

        for entry in self.colors_data:
            dataset_name = entry.get("name", "").lower()

            # Try exact match first
            if team_name_lower == dataset_name or team_name_lower in dataset_name:
                score: float = 100.0
            else:
                # Fuzzy match
                score = fuzz.partial_ratio(team_name_lower, dataset_name)

            if score > best_score:
                best_score = score
                best_match = entry

        # Only return match if confidence is high enough
        if best_score >= self.MATCH_THRESHOLD and best_match:
            colors = best_match.get("colors", [])
            result = {
                "primary": colors[0] if len(colors) > 0 else None,
                "secondary": colors[1] if len(colors) > 1 else None,
            }

            logger.debug(
                "match_team_to_colors_dataset.match_found",
                team_id=team.team_id,
                team_name=team.team_name,
                matched_name=best_match.get("name"),
                score=best_score,
                colors=result,
            )

            return result

        logger.debug(
            "match_team_to_colors_dataset.no_match",
            team_id=team.team_id,
            team_name=team.team_name,
            best_score=best_score,
        )
        return None

    def generate_aliases(self, team_name: str) -> list[str]:
        """
        Generate aliases programmatically from team name.

        Rules:
        1. Full team name: "Duke Blue Devils"
        2. School name only: "Duke" (first word or words before mascot)
        3. Mascot only: "Blue Devils" (last word(s) after school)

        Args:
            team_name: Team name to generate aliases from

        Returns:
            List of unique aliases (lowercased, no duplicates)

        Examples:
            "Duke" → ["duke"]
            "Duke Blue Devils" → ["duke blue devils", "duke", "blue devils"]
            "North Carolina" → ["north carolina"]
            "UNC Greensboro" → ["unc greensboro", "unc", "greensboro"]
        """
        aliases = []

        # Add full name
        team_name_clean = team_name.strip()
        aliases.append(team_name_clean.lower())

        # Try to split into school + mascot
        # Common patterns: "School Mascot", "School St. Mascot", "School A&M"
        words = team_name_clean.split()

        # If multiple words, try to extract school and mascot
        if len(words) >= 2:
            # Heuristic: Last 1-2 words are likely mascot (unless abbreviation/state name)
            # First 1-2 words are likely school name

            # Add first word (school name)
            aliases.append(words[0].lower())

            # Add last word (mascot)
            if len(words) > 1 and not self._is_abbreviation(words[-1]):
                aliases.append(words[-1].lower())

            # Add last 2 words if length permits (compound mascots like "Blue Devils")
            if len(words) >= 3:
                mascot_candidate = " ".join(words[-2:])
                if not self._is_abbreviation(words[-2]):
                    aliases.append(mascot_candidate.lower())

            # Add first 2 words (school names like "North Carolina")
            if len(words) >= 3:
                school_candidate = " ".join(words[:2])
                aliases.append(school_candidate.lower())

        # Remove duplicates while preserving order
        seen = set()
        unique_aliases = []
        for alias in aliases:
            if alias not in seen:
                seen.add(alias)
                unique_aliases.append(alias)

        logger.debug(
            "generate_aliases.completed",
            team_name=team_name,
            aliases_count=len(unique_aliases),
            aliases=unique_aliases,
        )

        return unique_aliases

    def _is_abbreviation(self, word: str) -> bool:
        """
        Check if word is likely an abbreviation (St., A&M, etc.).

        Args:
            word: Word to check

        Returns:
            True if word appears to be abbreviation
        """
        # Contains period (St., Mt.)
        if "." in word:
            return True

        # Contains ampersand (A&M, T&M)
        if "&" in word:
            return True

        # All caps and short (UNC, UK, MSU) - but only if 2-4 chars
        if word.isupper() and 2 <= len(word) <= 4:
            return True

        return False

    def merge_aliases(self, existing: list[str], new: list[str]) -> list[str]:
        """
        Merge new aliases into existing list without duplicates.

        Strategy:
        - Preserve all existing aliases
        - Add new aliases that don't exist (case-insensitive check)
        - Return sorted list for consistency

        Args:
            existing: Current aliases from database
            new: New aliases to add

        Returns:
            Merged list with no duplicates (case-insensitive)
        """
        # Normalize to lowercase for comparison
        existing_lower = {alias.lower() for alias in (existing or [])}
        merged = list(existing or [])

        for alias in new:
            if alias.lower() not in existing_lower:
                merged.append(alias)
                existing_lower.add(alias.lower())

        return sorted(merged)

    def enrich_team(self, team: DimTeam, force: bool = False) -> bool:
        """
        Enrich a single team with colors and aliases.

        Args:
            team: DimTeam instance to enrich
            force: If True, update even if data already exists

        Returns:
            True if team was enriched (data changed), False if skipped

        Side effects:
            - Updates team.primary_color and team.secondary_color if found
            - Updates team.aliases by merging new programmatic aliases
            - Sets team.updated_at to current timestamp
        """
        changed = False

        # Try to match colors from external dataset
        colors = self.match_team_to_colors_dataset(team)

        if colors:
            # Update colors if force=True or field is NULL
            if force or not team.primary_color:
                if colors.get("primary") and team.primary_color != colors["primary"]:
                    team.primary_color = colors["primary"]
                    changed = True

            if force or not team.secondary_color:
                if (
                    colors.get("secondary")
                    and team.secondary_color != colors["secondary"]
                ):
                    team.secondary_color = colors["secondary"]
                    changed = True

        # Generate and merge aliases
        new_aliases = self.generate_aliases(team.team_name)
        merged_aliases = self.merge_aliases(team.aliases or [], new_aliases)

        if merged_aliases != team.aliases:
            team.aliases = merged_aliases
            changed = True

        # Update timestamp if changed
        if changed:
            team.updated_at = datetime.now(timezone.utc)

        logger.debug(
            "enrich_team.completed",
            team_id=team.team_id,
            team_name=team.team_name,
            changed=changed,
            primary_color=team.primary_color,
            aliases_count=len(team.aliases or []),
        )

        return changed

    def detect_duplicates(self, teams: list[DimTeam]) -> list[dict[str, Any]]:
        """
        Detect duplicate teams based on team_name + sport combination.

        Teams are considered duplicates if they share the same team_name
        and sport but have different team_id values (e.g., slug-based vs numeric IDs).

        Args:
            teams: List of teams to check for duplicates

        Returns:
            List of duplicate groups, each containing:
            - team_name: The duplicated team name
            - count: Number of teams with this name
            - team_ids: List of team_id values for the duplicates

        Example:
            [
                {
                    "team_name": "Duke",
                    "count": 2,
                    "team_ids": ["ncaam_duke", "ncaam_150"]
                }
            ]
        """
        from collections import defaultdict

        # Group teams by name
        name_groups: dict[str, list[DimTeam]] = defaultdict(list)
        for team in teams:
            name_groups[team.team_name].append(team)

        # Find groups with multiple entries
        duplicates = []
        for team_name, group_teams in name_groups.items():
            if len(group_teams) > 1:
                duplicates.append(
                    {
                        "team_name": team_name,
                        "count": len(group_teams),
                        "team_ids": [t.team_id for t in group_teams],
                    }
                )

        if duplicates:
            logger.warning(
                "detect_duplicates.found",
                duplicate_count=len(duplicates),
                total_duplicate_teams=sum(d["count"] for d in duplicates),
            )

        return duplicates

    def delete_duplicate_teams(self, dry_run: bool = False) -> dict[str, Any]:
        """
        Delete duplicate teams, keeping slug-based IDs and removing numeric seed data IDs.

        Strategy:
        - Keep: slug-based IDs (e.g., ncaam_duke, ncaam_north-carolina) - from NCAA API
        - Delete: numeric IDs (e.g., ncaam_150, ncaam_153) - from seed data

        The slug-based IDs are preferred because:
        1. They're created by ongoing NCAA API ingestion
        2. They're more human-readable
        3. They match the API's team identification scheme

        Args:
            dry_run: If True, report what would be deleted without actually deleting

        Returns:
            Dict with deletion summary:
            - teams_deleted: Number of teams deleted
            - duplicate_groups_resolved: Number of duplicate groups resolved
            - deleted_team_ids: List of team_id values that were deleted
        """
        import re

        result = {
            "teams_deleted": 0,
            "duplicate_groups_resolved": 0,
            "deleted_team_ids": [],
        }

        logger.info("delete_duplicate_teams.started", dry_run=dry_run)

        # Load all teams
        stmt = select(DimTeam).where(DimTeam.sport == "ncaam", DimTeam.is_current)
        teams = self.session.exec(stmt).all()

        # Detect duplicates
        duplicates = self.detect_duplicates(teams)

        if not duplicates:
            logger.info("delete_duplicate_teams.no_duplicates_found")
            return result

        # Process each duplicate group
        from collections import defaultdict

        name_to_teams: dict[str, list[DimTeam]] = defaultdict(list)
        for team in teams:
            name_to_teams[team.team_name].append(team)

        for dup_group in duplicates:
            team_name = dup_group["team_name"]
            group_teams = name_to_teams[team_name]

            # Separate slug-based vs numeric IDs
            # Numeric pattern: ncaam_<digits> (e.g., ncaam_150, ncaam_2305)
            # Slug pattern: ncaam_<text-with-dashes> (e.g., ncaam_duke, ncaam_north-carolina)
            numeric_pattern = re.compile(r"^ncaam_\d+$")

            slug_teams = [
                t for t in group_teams if not numeric_pattern.match(t.team_id)
            ]
            numeric_teams = [t for t in group_teams if numeric_pattern.match(t.team_id)]

            # Delete numeric teams (seed data), keep slug teams (API data)
            for team in numeric_teams:
                result["deleted_team_ids"].append(team.team_id)
                result["teams_deleted"] += 1

                logger.info(
                    "delete_duplicate_teams.deleting",
                    team_id=team.team_id,
                    team_name=team.team_name,
                    reason="numeric_id_from_seed_data",
                    keeping=f"{slug_teams[0].team_id if slug_teams else 'none'}",
                )

                if not dry_run:
                    self.session.delete(team)

            if numeric_teams:
                result["duplicate_groups_resolved"] += 1

        # Commit changes (unless dry run)
        if not dry_run and result["teams_deleted"] > 0:
            self.session.commit()
            logger.info(
                "delete_duplicate_teams.committed",
                teams_deleted=result["teams_deleted"],
                groups_resolved=result["duplicate_groups_resolved"],
            )
        elif dry_run:
            self.session.rollback()
            logger.info(
                "delete_duplicate_teams.dry_run_completed",
                teams_deleted=result["teams_deleted"],
                groups_resolved=result["duplicate_groups_resolved"],
            )
        else:
            logger.info("delete_duplicate_teams.no_changes")

        return result

    def enrich_all_teams(
        self,
        sport: str = "ncaam",
        dry_run: bool = False,
        force: bool = False,
    ) -> EnrichmentReport:
        """
        Enrich all teams for a given sport.

        Args:
            sport: Sport code (default: "ncaam")
            dry_run: If True, don't commit changes to database
            force: If True, update even if data already exists

        Returns:
            EnrichmentReport with summary of enrichment results

        Raises:
            Exception: If critical error occurs (caught and logged in report)
        """
        report = EnrichmentReport()

        logger.info(
            "enrich_all_teams.started",
            sport=sport,
            dry_run=dry_run,
            force=force,
        )

        try:
            # Fetch external colors dataset
            self.fetch_colors_dataset()

            # Load all teams for sport
            stmt = select(DimTeam).where(DimTeam.sport == sport, DimTeam.is_current)
            teams = self.session.exec(stmt).all()

            logger.info("enrich_all_teams.teams_loaded", count=len(teams))

            # Detect duplicates
            duplicates = self.detect_duplicates(teams)
            if duplicates:
                report.duplicates_found = len(duplicates)
                report.duplicate_groups = duplicates
                logger.warning(
                    "enrich_all_teams.duplicates_detected",
                    duplicate_groups=len(duplicates),
                    total_duplicates=sum(d["count"] for d in duplicates),
                )

            # Enrich each team
            for team in teams:
                report.teams_processed += 1

                try:
                    enriched = self.enrich_team(team, force=force)

                    if enriched:
                        report.teams_enriched += 1

                        # Track specific enrichments
                        if team.primary_color:
                            report.colors_added += 1
                        if team.aliases and len(team.aliases) > 0:
                            report.aliases_added += 1
                    else:
                        report.teams_skipped += 1

                except Exception as e:
                    report.teams_failed += 1
                    error_msg = f"Failed to enrich {team.team_id}: {e}"
                    report.errors.append(error_msg)
                    logger.error(
                        "enrich_team.error",
                        team_id=team.team_id,
                        error=str(e),
                    )

            # Commit changes (unless dry run)
            if not dry_run:
                self.session.commit()
                logger.info(
                    "enrich_all_teams.committed", teams_enriched=report.teams_enriched
                )
            else:
                self.session.rollback()
                logger.info(
                    "enrich_all_teams.dry_run_completed",
                    teams_enriched=report.teams_enriched,
                )

        except Exception as e:
            error_msg = f"Critical error during enrichment: {e}"
            report.errors.append(error_msg)
            logger.error("enrich_all_teams.critical_error", error=str(e))
            self.session.rollback()

        logger.info(
            "enrich_all_teams.completed",
            teams_processed=report.teams_processed,
            teams_enriched=report.teams_enriched,
            colors_added=report.colors_added,
            aliases_added=report.aliases_added,
            teams_failed=report.teams_failed,
            dry_run=dry_run,
        )

        return report
