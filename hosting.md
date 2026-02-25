# 🚀 Hosting & Infrastructure: Kcal-Tracker

Diese Dokumentation beschreibt das Cloud-Hosting-Setup für den Kcal-Tracker auf dem Raspberry Pi 5.

## 🏗 Architektur-Komponenten

### 1. Docker Networking
Die Container kommunizieren über ein dediziertes Bridge-Netzwerk, um Isolation und DNS-Auflösung zu gewährleisten.

* **Netzwerk-Name:** `web-network`
* **Verbundene Container:** `food-tracker` (App), `cloudflare-tunnel` (Gateway)
* **Lokaler Endpunkt:** `http://192.168.178.38:8787`

### 2. Cloudflare Tunnel (External Access)
Der Zugriff erfolgt über einen verschlüsselten Tunnel ohne Port-Freigaben am Router.

* **Team Domain:** `darwin-labs.cloudflareaccess.com`
* **Public Hostname:** `kcal-tracker.darwin-labs.org`
* **Service-Konfiguration:** HTTP auf Port `8787`

### 3. Identity & Access Management (Zero Trust)
Die Anwendung ist durch eine Google OAuth-Authentifizierung vor unbefugtem Zugriff geschützt.

* **Identitätsanbieter:** Google OAuth 2.0
* **UX-Optimierung:** * **Instant Auth:** Aktiviert (direkte Weiterleitung zu Google)
    * **Custom Logo:** `https://cdn-icons-png.flaticon.com/512/9273/9273130.png`

## 🛠 Wartungs-Befehle

### Netzwerk-Reparatur
Falls die Container die Verbindung verlieren:
```bash
docker network connect web-network food-tracker
docker network connect web-network cloudflare-tunnel

```

### Log-Analyse

```bash
# Tunnel-Status prüfen
docker logs cloudflare-tunnel

# App-Status prüfen
docker logs food-tracker

```

## 🔐 Google Cloud Console Infos

Die Verwaltung der OAuth-Anmeldedaten erfolgt im Google Cloud Console Projekt unter dem Punkt "OAuth-Zustimmungsbildschirm". Wichtig: Neue Test-User müssen dort manuell hinzugefügt werden, solange die App im "Testing"-Modus ist.

## 🔑 API-Key Hinweis (aktuell)

- App-API Schlüssel werden im Web-UI generiert (`Settings -> Generate API key`).
- Pro User ist genau ein aktiver Schlüssel vorgesehen.
- Beim Erstellen eines neuen Schlüssels wird der alte automatisch entfernt.
- Cloudflare Access bleibt für Web-Zugriff die primäre Zugriffskontrolle.
