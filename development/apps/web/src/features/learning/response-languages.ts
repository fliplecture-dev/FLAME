// Requested first eight choices; remaining choices follow 2011 Census mother-tongue totals.
// https://censusindia.gov.in/nada/index.php/catalog/42458/download/46089/C-16_25062018.pdf
export const responseLanguages = [
  { code: "en", name: "English", native: "English" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "ml", name: "Malayalam", native: "മലയാളം" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
  { code: "mr", name: "Marathi", native: "मराठी" },
  { code: "bn", name: "Bengali", native: "বাংলা" },
  { code: "gu", name: "Gujarati", native: "ગુજરાતી" },
  { code: "ur", name: "Urdu", native: "اردو" },
  { code: "or", name: "Odia", native: "ଓଡ଼ିଆ" },
  { code: "pa", name: "Punjabi", native: "ਪੰਜਾਬੀ" },
  { code: "as", name: "Assamese", native: "অসমীয়া" },
  { code: "kok", name: "Konkani", native: "कोंकणी" },
  { code: "mni", name: "Manipuri", native: "মৈতৈলোন্" },
  { code: "sa", name: "Sanskrit", native: "संस्कृतम्" },
] as const;
export type ResponseLanguage = typeof responseLanguages[number]["code"];
export function isResponseLanguage(value: unknown): value is ResponseLanguage {
  return responseLanguages.some(language => language.code === value);
}
