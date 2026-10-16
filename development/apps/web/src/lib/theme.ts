export const themePreferenceKey = "flame.theme";

// Run before the page paints so a saved dark preference doesn't flash white.
export const themeBootstrap = `(function(){var t;try{t=localStorage.getItem(${JSON.stringify(themePreferenceKey)})}catch{}document.documentElement.dataset.theme=t==='light'||t==='dark'?t:matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'})()`;
