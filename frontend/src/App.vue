<template>
  <router-view />
</template>

<script setup>
</script>

<style>
/* ─── CSS 变量主题 ─── */
:root {
  /* Light (default) */
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-sidebar: #f9fafb;
  --bg-hover: #f3f4f6;
  --bg-active: #e5e7eb;
  --bg-input: #ffffff;
  --bg-bubble-user: #000000;
  --bg-bubble-ai: #f3f4f6;
  --bg-modal: #ffffff;
  --bg-overlay: rgba(0,0,0,.4);
  --border: #e5e7eb;
  --border-light: #f3f4f6;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --text-muted: #9ca3af;
  --text-bubble-user: #ffffff;
  --text-bubble-ai: #111827;
  --text-on-accent: #ffffff;
  --accent: #10a37f;
  --accent-hover: #0d8c6d;
  --danger: #ef4444;
  --danger-hover: #dc2626;
  --shadow: 0 2px 8px rgba(0,0,0,.08);
  --shadow-lg: 0 12px 32px rgba(0,0,0,.12);
}
html.dark {
  --bg-primary: #212121;
  --bg-secondary: #2f2f2f;
  --bg-sidebar: #171717;
  --bg-hover: #2f2f2f;
  --bg-active: #424242;
  --bg-input: #2f2f2f;
  --bg-bubble-user: #2f2f2f;
  --bg-bubble-ai: transparent;
  --bg-modal: #2f2f2f;
  --bg-overlay: rgba(0,0,0,.6);
  --border: #424242;
  --border-light: #373737;
  --text-primary: #ececec;
  --text-secondary: #b4b4b4;
  --text-muted: #8e8e8e;
  --text-bubble-user: #ececec;
  --text-bubble-ai: #d1d5db;
  --text-on-accent: #ffffff;
  --accent: #10a37f;
  --accent-hover: #0d8c6d;
  --danger: #ef4444;
  --danger-hover: #dc2626;
  --shadow: 0 2px 8px rgba(0,0,0,.3);
  --shadow-lg: 0 12px 32px rgba(0,0,0,.5);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  transition: background .2s, color .2s;
}
a {
  color: inherit;
  text-decoration: none;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
