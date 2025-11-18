import { Box, Flex, HStack, Heading, IconButton, Text } from "@chakra-ui/react";
import { Link } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import { useTheme } from "next-themes";
import { FiMoon, FiSun } from "react-icons/fi";
import { useGames } from "../../hooks/useGames";

function Navbar() {
  const { theme, setTheme } = useTheme();
  const { data } = useGames();

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  return (
    <Flex
      justify="space-between"
      position="sticky"
      align="center"
      bg="bg.page"
      borderBottom="1px solid"
      borderColor="border.card"
      w="100%"
      top={0}
      px={8}
      py={4}
      zIndex={10}
    >
      {/* Left: Logo + Title + Last Updated */}
      <Link to="/">
        <HStack gap={3}>
          <Box
            w={10}
            h={10}
            bg="purple.500"
            borderRadius="full"
            flexShrink={0}
          />
          <Heading as="h1" size="xl" fontWeight="black" color="text.primary">
            GamePulse
          </Heading>
          {data?.generated_at && (
            <Text fontSize="sm" color="text.muted" ml={4}>
              Last updated{" "}
              {formatDistanceToNow(new Date(data.generated_at), {
                addSuffix: true,
              })}
            </Text>
          )}
        </HStack>
      </Link>

      {/* Right: Theme toggle */}
      <Flex gap={2} alignItems="center">
        <IconButton
          aria-label="Toggle theme"
          onClick={toggleTheme}
          variant="ghost"
        >
          {theme === "light" ? <FiMoon /> : <FiSun />}
        </IconButton>
      </Flex>
    </Flex>
  );
}

export default Navbar;
