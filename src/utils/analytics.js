const ANALYTICS_API =
  "https://roboinsight-api.onrender.com";

async function fetchJson(url) {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `Analytics API request failed: ${response.status}`
    );
  }

  return response.json();
}

export async function loadAnalyticsOverview() {
  return fetchJson(
    `${ANALYTICS_API}/analytics/overview`
  );
}

export async function loadHistoricalTrends({
  hours = 24,
  bucketMinutes = 15,
} = {}) {
  return fetchJson(
    `${ANALYTICS_API}/analytics/trends?hours=${hours}&bucket_minutes=${bucketMinutes}`
  );
}