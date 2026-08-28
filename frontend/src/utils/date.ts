/**
 * Safely parses a UTC timestamp string from the backend and converts it to the user's local timezone.
 *
 * Background: SQLite and Python datetime serialization may omit the explicit 'Z' suffix
 * (e.g. "2026-08-28T09:16:00" instead of "2026-08-28T09:16:00Z"). In ECMAScript, ISO strings
 * without timezone designators are treated as local time instead of UTC.
 * This utility ensures UTC is properly recognized so that `toLocaleString()` automatically converts
 * to the browser's local timezone.
 */
export function formatLocalDateTime(isoString?: string | null): string {
  if (!isoString) return '';
  try {
    let cleanStr = isoString.trim();
    // If the string is in ISO format (contains 'T') and doesn't end with 'Z' or offset, append 'Z'
    if (cleanStr.includes('T') && !cleanStr.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(cleanStr)) {
      cleanStr += 'Z';
    } else if (!cleanStr.includes('T') && /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(cleanStr)) {
      // If SQLite format: "2026-08-28 09:16:00" -> convert to ISO UTC "2026-08-28T09:16:00Z"
      cleanStr = cleanStr.replace(' ', 'T') + 'Z';
    }
    const d = new Date(cleanStr);
    if (isNaN(d.getTime())) {
      return isoString;
    }
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  } catch {
    return isoString;
  }
}
