import { createSystem, defaultConfig } from "@chakra-ui/react";
import { buttonRecipe } from "./theme/button.recipe";

export const system = createSystem(defaultConfig, {
  globalCss: {
    html: {
      fontSize: "16px",
    },
    body: {
      fontSize: "0.875rem",
      margin: 0,
      padding: 0,
      bg: "bg.page",
    },
    ".main-link": {
      color: "ui.main",
      fontWeight: "bold",
    },
  },
  theme: {
    tokens: {
      colors: {
        ui: {
          main: { value: "#009688" },
        },
      },
    },
    semanticTokens: {
      colors: {
        // Page and card backgrounds
        bg: {
          page: {
            value: { base: "{colors.gray.50}", _dark: "#1a1d29" },
          },
          card: {
            value: { base: "white", _dark: "#22262f" },
          },
        },
        // Border colors
        border: {
          card: {
            value: {
              base: "{colors.gray.200}",
              _dark: "rgba(255, 255, 255, 0.1)",
            },
          },
        },
        // Text colors
        text: {
          primary: {
            value: { base: "{colors.gray.900}", _dark: "white" },
          },
          secondary: {
            value: { base: "{colors.gray.600}", _dark: "{colors.gray.400}" },
          },
          muted: {
            value: { base: "{colors.gray.500}", _dark: "{colors.gray.500}" },
          },
        },
        // Game status colors
        game: {
          live: {
            value: { base: "#ef4444", _dark: "#ef4444" },
          },
          final: {
            value: { base: "{colors.gray.500}", _dark: "{colors.gray.400}" },
          },
          scheduled: {
            value: { base: "#3b82f6", _dark: "#60a5fa" },
          },
        },
      },
    },
    recipes: {
      button: buttonRecipe,
    },
  },
});
