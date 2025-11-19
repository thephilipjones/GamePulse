import { Box, HStack, Text, VStack } from "@chakra-ui/react";
import React from "react";
import type { GamePublic } from "../client/types.gen";
import { GameStatusBadge } from "./GameStatusBadge";
import { SocialPostsFeed } from "./SocialPostsFeed";
import { TeamCircle } from "./TeamCircle";

interface GameCardProps {
  game: GamePublic;
}

/**
 * Generates a 2-letter abbreviation from team name.
 * Uses first 2 letters of first word, uppercase.
 */
function getTeamAbbreviation(teamName: string): string {
  const words = teamName.trim().split(/\s+/);
  const firstWord = words[0] || "";
  return firstWord.slice(0, 2).toUpperCase();
}

/**
 * GameCard component displaying team matchup in vertical layout.
 *
 * Layout (matches mockup):
 * - Status badge (top-left)
 * - Team circles with scores centered between them
 * - Placeholder areas for future features (graph, moments)
 *
 * Features:
 * - Vertical stack layout
 * - Team circles with 2-letter abbreviations
 * - Solid dark background (no gradients)
 * - Muted styling for FINAL games
 * - Light/dark mode support
 *
 * Optimized with React.memo to prevent unnecessary re-renders.
 */
function GameCardComponent({ game }: GameCardProps) {
  const isFinal = game.game_status === "final";

  // Generate 2-letter abbreviations
  const awayAbbr = getTeamAbbreviation(game.away_team.team_name);
  const homeAbbr = getTeamAbbreviation(game.home_team.team_name);

  // Text opacity for muted final games
  const textOpacity = isFinal ? 0.6 : 1;

  return (
    <Box
      bg="bg.card"
      borderWidth="1px"
      borderColor="border.card"
      borderRadius="xl"
      p={{ base: 3, md: 5 }}
      position="relative"
      role="article"
      aria-label={`Game: ${game.away_team.team_name} at ${game.home_team.team_name}`}
    >
      {/* Content Stack */}
      <VStack gap={{ base: 3, md: 6 }} align="stretch">
        {/* Top Row: Status Badge (left) + Excitement Score (right) - placeholder */}
        <HStack justify="space-between" align="flex-start">
          <GameStatusBadge
            status={
              game.game_status as
                | "scheduled"
                | "pre"
                | "in_progress"
                | "live"
                | "final"
            }
            startTime={game.game_start_time}
            gameClock={game.game_clock}
            gamePeriod={game.game_period}
          />
          {/* Excitement score placeholder for Epic 5 */}
          <Box />
        </HStack>

        {/* Team Circles + Scores (Centered) */}
        <HStack
          justify="center"
          align="center"
          gap={{ base: 3, md: 8 }}
          py={{ base: 2, md: 4 }}
        >
          {/* Away Team Circle (Left) */}
          <TeamCircle
            teamName={game.away_team.team_name}
            primaryColor={game.away_team.primary_color}
            secondaryColor={game.away_team.secondary_color}
            abbreviation={awayAbbr}
          />

          {/* Scores (Center) */}
          <HStack gap={{ base: 1, md: 3 }} opacity={textOpacity}>
            <Text
              fontSize={{ base: "3xl", md: "5xl" }}
              fontWeight="black"
              letterSpacing="tight"
              color="text.primary"
            >
              {game.away_score ?? "—"}
            </Text>
            <Text fontSize={{ base: "xl", md: "3xl" }} color="text.muted">
              -
            </Text>
            <Text
              fontSize={{ base: "3xl", md: "5xl" }}
              fontWeight="black"
              letterSpacing="tight"
              color="text.primary"
            >
              {game.home_score ?? "—"}
            </Text>
          </HStack>

          {/* Home Team Circle (Right) */}
          <TeamCircle
            teamName={game.home_team.team_name}
            primaryColor={game.home_team.primary_color}
            secondaryColor={game.home_team.secondary_color}
            abbreviation={homeAbbr}
          />
        </HStack>

        {/* Momentum Graph Placeholder (Epic 5) */}
        <Box
          h={10}
          bg="rgba(255, 255, 255, 0.02)"
          borderRadius="md"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Text fontSize="xs" color="gray.600">
            Momentum Graph (Epic 5)
          </Text>
        </Box>

        {/* Top Moments - Social Posts Feed (Story 4-10) */}
        <SocialPostsFeed gameId={game.game_id} />
      </VStack>
    </Box>
  );
}

/**
 * Memoized GameCard component.
 * Only re-renders when game_key or game data changes.
 */
export const GameCard = React.memo(
  GameCardComponent,
  (prevProps, nextProps) => {
    return (
      prevProps.game.game_key === nextProps.game.game_key &&
      prevProps.game.away_score === nextProps.game.away_score &&
      prevProps.game.home_score === nextProps.game.home_score &&
      prevProps.game.game_status === nextProps.game.game_status &&
      prevProps.game.game_clock === nextProps.game.game_clock
    );
  },
);

GameCard.displayName = "GameCard";
