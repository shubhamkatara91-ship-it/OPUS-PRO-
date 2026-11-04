# OPUS PRO Android build

This directory contains the native Android WebView shell. GitHub Actions builds a debug APK with `gradle assembleDebug` and uploads it as an Actions artifact. The APK requires an HTTPS OPUS PRO backend URL on first launch; no production backend is bundled in this shell.
