// Team color mapping for analytics and UI consistency.
// Values are aligned with data/static/teams.json (single source of truth).
export const TEAM_COLORS = {
  McLaren: {
    primary: "#FF8700",
    secondary: "#FFB800",
    logo: "/logos/mclaren.png",
    drivers: {
      "Lando Norris": "#FF8700",
      "Oscar Piastri": "#FFB800",
    },
  },

  Ferrari: {
    primary: "#E8001B",
    secondary: "#FF3333",
    logo: "/logos/ferrari.png",
    drivers: {
      "Charles Leclerc": "#FF3333",
      "Lewis Hamilton": "#E8001B",
    },
  },

  "Red Bull": {
    primary: "#0600EF",
    secondary: "#1E41FF",
    logo: "/logos/red bull.png",
    drivers: {
      "Max Verstappen": "#0600EF",
      "Isack Hadjar": "#1E41FF",
    },
  },

  Mercedes: {
    primary: "#00A19A",
    secondary: "#00D4BE",
    logo: "/logos/mercedes.webp",
    drivers: {
      "George Russell": "#00D4BE",
      "Kimi Antonelli": "#00A19A",
    },
  },

  "Aston Martin": {
    primary: "#006B3F",
    secondary: "#00A859",
    logo: "/logos/aston martin.png",
    drivers: {
      "Fernando Alonso": "#00A859",
      "Lance Stroll": "#006B3F",
    },
  },

  Alpine: {
    primary: "#0F46F3",
    secondary: "#4D7FFF",
    logo: "/logos/alpine.png",
    drivers: {
      "Pierre Gasly": "#4D7FFF",
      "Jack Doohan": "#0F46F3",
    },
  },

  Williams: {
    primary: "#0082FA",
    secondary: "#64B0FF",
    logo: "/logos/williams.png",
    drivers: {
      "Carlos Sainz": "#0082FA",
      "Alexander Albon": "#64B0FF",
    },
  },

  "Racing Bulls": {
    primary: "#5E72E4",
    secondary: "#8B9FFF",
    logo: "/logos/racing bulls.png",
    drivers: {
      "Liam Lawson": "#5E72E4",
      "Arvin Lindblad": "#8B9FFF",
    },
  },

  Haas: {
    primary: "#FFFFFF",
    secondary: "#FF6B00",
    logo: "/logos/haas.png",
    drivers: {
      "Esteban Ocon": "#FF6B00",
      "Oliver Bearman": "#FFFFFF",
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
    primary: "#111111",
    secondary: "#C9A227",
    logo: "/logos/cadillac.png",
    drivers: {
      "Valtteri Bottas": "#111111",
      "Sergio Perez": "#C9A227",
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

export function getSeriesColor(series) {
  if (!series || !series.team) return "#9ca3af";
  return getDriverColor(series.team, series.name) || getTeamColor(series.team) || "#9ca3af";
}
