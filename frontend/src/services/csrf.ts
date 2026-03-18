export function getCookieValue(name: string): string | null {
  if (typeof document === "undefined" || !document.cookie) {
    return null;
  }

  const encodedName = encodeURIComponent(name);
  const cookies = document.cookie.split("; ");
  for (const cookie of cookies) {
    const [rawName, ...rawValue] = cookie.split("=");
    if (rawName === encodedName) {
      return decodeURIComponent(rawValue.join("="));
    }
  }
  return null;
}
