const WEATHER_EMOJI = {
  Dry: "☀️",
  Humid: "🌫️",
  "Light rain": "🌦️",
  "Heavy rain": "🌧️",
};

export function formatWeather(weather) {
  if (!weather) return "-";
  return `${WEATHER_EMOJI[weather] || "🌡️"} ${weather}`;
}
