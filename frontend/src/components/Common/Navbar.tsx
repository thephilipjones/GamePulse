import { Flex, IconButton, Text, useBreakpointValue } from "@chakra-ui/react";
import { Link } from "@tanstack/react-router";
import { useTheme } from "next-themes";
import { FiMoon, FiSun } from "react-icons/fi";

function Navbar() {
  const display = useBreakpointValue({ base: "none", md: "flex" });
  const { theme, setTheme } = useTheme();

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  return (
    <Flex
      display={display}
      justify="space-between"
      position="sticky"
      color="white"
      align="center"
      bg="bg.muted"
      w="100%"
      top={0}
      p={4}
    >
      <Link to="/">
        <Text fontSize="xl" fontWeight="bold" color="ui.main">
          GamePulse
        </Text>
      </Link>
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
