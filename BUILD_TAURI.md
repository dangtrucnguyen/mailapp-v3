# MailApp Desktop — Beta

Application native macOS (ARM + Intel) basée sur Tauri v2.

## Prérequis (macOS)

```bash
# Installer Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# Redémarrer le terminal ou:
source "$HOME/.cargo/env"

# Installer les outils macOS
xcode-select --install
```

## Build

```bash
cd frontend
npm install
npm run tauri:build
```

Sortie: `src-tauri/target/release/bundle/dmg/MailApp_3.0.0-beta.1_universal.dmg`

## Build debug (plus rapide, pour test)

```bash
npm run tauri:build:debug
```

## Dev (hot reload)

```bash
npm run tauri:dev
```

## Configuration serveur

L'API pointe sur `https://op13.scigroup.fr` par défaut.
Pour changer en dev : `export MAILAPP_API_URL=http://192.168.1.242:6000`

## Icône personnalisée

```bash
# Sur macOS uniquement
npx tauri icon ./path/to/icon-1024x1024.png
```
