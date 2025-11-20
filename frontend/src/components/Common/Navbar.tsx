import { Box, Flex, HStack, Heading, IconButton, Text } from "@chakra-ui/react";
import { Link, useNavigate, useSearch, useRouterState } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import { useTheme } from "next-themes";
import { FiMoon, FiSun } from "react-icons/fi";
import { useGames } from "../../hooks/useGames";
import { DateNavigator } from "../DateNavigator";

function getTodayDate(): string {
  const date = new Date();
  return date.toISOString().split("T")[0];
}

function Navbar() {
  const { theme, setTheme } = useTheme();
  const routerState = useRouterState();
  const navigate = useNavigate({ from: "/_layout/" });
  const search = useSearch({ from: "/_layout/", strict: false });

  // Get current date from URL or default to today
  const currentDate = (search as { date?: string })?.date || getTodayDate();
  const { data } = useGames(currentDate);

  // Check if we're on the dashboard route
  const isOnDashboard = routerState.location.pathname === "/";

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  const handleDateChange = (newDate: string) => {
    navigate({
      to: "/",
      search: { date: newDate },
    });
  };

  return (
    <Flex
      direction={{ base: "column", md: "row" }}
      position="sticky"
      bg="bg.page"
      borderBottom="1px solid"
      borderColor="border.card"
      w="100%"
      top={0}
      px={{ base: 4, md: 8 }}
      py={{ base: 2, md: 4 }}
      zIndex={10}
      gap={{ base: 2, md: 4 }}
      align="center"
      justify="space-between"
    >
      {/* Mobile: Row 1 (Logo + Title + Theme) | Desktop: Left side (Logo + Title) */}
      <Flex
        justify="space-between"
        align="center"
        w={{ base: "100%", md: "auto" }}
      >
        <Link to="/">
          <HStack gap={{ base: 2, md: 3 }}>
            <Box
              w={{ base: 8, md: 10 }}
              h={{ base: 8, md: 10 }}
              bg="purple.500"
              borderRadius="full"
              flexShrink={0}
            />
            <Heading
              as="h1"
              size={{ base: "lg", md: "xl" }}
              fontWeight="black"
              color="text.primary"
            >
              GamePulse
            </Heading>
          </HStack>
        </Link>

        {/* Theme toggle - visible on mobile only (on desktop it's on the right) */}
        <IconButton
          aria-label="Toggle theme"
          onClick={toggleTheme}
          variant="ghost"
          size="sm"
          display={{ base: "flex", md: "none" }}
        >
          {theme === "light" ? <FiMoon /> : <FiSun />}
        </IconButton>
      </Flex>

      {/* Date Navigator - Mobile: Row 2 (centered) | Desktop: Center */}
      {isOnDashboard && (
        <Flex justify="center" flex={{ base: "0", md: "1" }} w={{ base: "100%", md: "auto" }}>
          <DateNavigator
            currentDate={currentDate}
            onDateChange={handleDateChange}
          />
        </Flex>
      )}

      {/* Desktop only: Right side (Last updated + Theme toggle) */}
      <Flex gap={2} alignItems="center" display={{ base: "none", md: "flex" }}>
        {/* Last updated timestamp */}
        {data?.generated_at && (
          <Text fontSize="sm" color="text.muted" display={{ base: "none", lg: "block" }}>
            Last updated{" "}
            {formatDistanceToNow(new Date(data.generated_at), {
              addSuffix: true,
            })}
          </Text>
        )}
        <IconButton
          aria-label="Toggle theme"
          onClick={toggleTheme}
          variant="ghost"
          size="md"
        >
          {theme === "light" ? <FiMoon /> : <FiSun />}
        </IconButton>
      </Flex>
    </Flex>
  );
}

export default Navbar;
