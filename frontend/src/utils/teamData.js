// Team color mapping for analytics and UI consistency
export const TEAM_COLORS = {
  McLaren: {
    primary: "#FF8700",
    secondary: "#FFB14A",
    logo: "/logos/mclaren.png",
    drivers: {
      "Lando Norris": "#FFB14A",
      "Oscar Piastri": "#FF8700",
    },
  },

  Ferrari: {
    primary: "#DC0000",
    secondary: "#FF5A5A",
    logo: "/logos/ferrari.png",
    drivers: {
      "Charles Leclerc": "#FF5A5A",
      "Lewis Hamilton": "#DC0000",
    },
  },

  "Red Bull": {
    primary: "#1E41FF",
    secondary: "#6B8CFF",
    logo: "/logos/red bull.png",
    drivers: {
      "Max Verstappen": "#6B8CFF",
      "Isack Hadjar": "#1E41FF",
    },
  },

  Mercedes: {
    primary: "#00D2BE",
    secondary: "#6EF2E4",
    logo: "/logos/mercedes.webp",
    drivers: {
      "George Russell": "#6EF2E4",
      "Kimi Antonelli": "#00D2BE",
    },
  },

  "Aston Martin": {
    primary: "#006F62",
    secondary: "#2FAE9C",
    logo: "/logos/aston martin.png",
    drivers: {
      "Fernando Alonso": "#2FAE9C",
      "Lance Stroll": "#006F62",
    },
  },

  Alpine: {
    primary: "#0090FF",
    secondary: "#5DBEFF",
    logo: "/logos/alpine.png",
    drivers: {
      "Pierre Gasly": "#5DBEFF",
      "Jack Doohan": "#0090FF",
    },
  },

  Williams: {
    primary: "#005AFF",
    secondary: "#6EA8FF",
    logo: "/logos/williams.png",
    drivers: {
      "Carlos Sainz": "#6EA8FF",
      "Alexander Albon": "#005AFF",
    },
  },

  "Racing Bulls": {
    primary: "#1D4ED8",
    secondary: "#7EA4FF",
    logo: "/logos/racing bulls.png",
    drivers: {
      "Liam Lawson": "#7EA4FF",
      "Arvin Lindblad": "#1D4ED8",
    },
  },

  Haas: {
    primary: "#8A8A8A",
    secondary: "#E6E6E6",
    logo: "/logos/haas.png",
    drivers: {
      "Esteban Ocon": "#E6E6E6",
      "Oliver Bearman": "#8A8A8A",
    },
  },

  Audi: {
    primary: "#6B7280",
    secondary: "#9CA3AF",
    logo: "/logos/audi.webp",
    drivers: {
      "Nico Hulkenberg": "#9CA3AF",
      "Gabriel Bortoleto": "#6B7280",
    },
  },

  Cadillac: {
    primary: "#8B0000",
    secondary: "#C62828",
    logo: "/logos/cadillac.png",
    drivers: {
      "Valtteri Bottas": "#C62828",
      "Sergio Perez": "#8B0000",
    },
  },
};

export function getTeamLogo(teamName) {
  return TEAM_COLORS[teamName]?.logo || "/logos/f1.png";
}

export function getTeamColor(teamName, driverName = null) {
  const team = TEAM_COLORS[teamName];
  if (!team) return "#9ca3af";

  if (driverName && team.drivers[driverName]) {
    return team.drivers[driverName];
  }

  return team.primary;
}

export function getDriverColor(teamName, driverName) {
  const team = TEAM_COLORS[teamName];
  if (!team) return "#9ca3af";

  return team.drivers[driverName] || team.primary;
}
