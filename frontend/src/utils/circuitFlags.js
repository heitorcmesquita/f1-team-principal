const CIRCUIT_FLAGS = {
  Australia: "au",
  China: "cn",
  Japan: "jp",
  Bahrain: "bh",
  "Saudi Arabia": "sa",
  Miami: "us",
  "Emilia-Romagna": "it",
  Monaco: "mc",
  Spain: "es",
  Canada: "ca",
  Austria: "at",
  "Great Britain": "gb",
  Belgium: "be",
  Hungary: "hu",
  Netherlands: "nl",
  Italy: "it",
  Azerbaijan: "az",
  Singapore: "sg",
  "United States": "us",
  Mexico: "mx",
  Brazil: "br",
  "Las Vegas": "us",
  Qatar: "qa",
  "Abu Dhabi": "ae",
};

export function getCircuitFlagCode(circuitName) {
  return CIRCUIT_FLAGS[circuitName] || null;
}

export function getCircuitFlagPath(circuitName) {
  const code = getCircuitFlagCode(circuitName);
  return code ? `/flags/${code}.svg` : null;
}
