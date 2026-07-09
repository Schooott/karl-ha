<p align="center">
  <img src="custom_components/cali/brand/icon@2x.png" width="160" alt="Cali" />
</p>

<h1 align="center">Cali für Home Assistant</h1>

Gegenstelle für Cali, die macOS-Desktop-Assistentin:
Entities gezielt freigeben, Aktionen mit serverseitiger Whitelist ausführen und
Cali als Benachrichtigungsziel in Automationen nutzen.

## Installation

**Via HACS (empfohlen):**
1. HACS → drei Punkte oben rechts → *Benutzerdefinierte Repositories*
2. `https://github.com/schooott/cali-ha` als Typ *Integration* hinzufügen
3. „Cali" installieren, Home Assistant neu starten
4. Einstellungen → Geräte & Dienste → *Integration hinzufügen* → **Cali**

**Manuell:** `custom_components/cali/` nach `config/custom_components/cali/`
kopieren und neu starten.

## Authentifizierung von Cali (der Mac-App)

1. In HA einen eigenen Benutzer **cali** anlegen (Einstellungen → Personen →
   Benutzer, *kein* Administrator, „Nur lokales Netzwerk" aus, falls Nabu Casa
   genutzt wird).
2. Als dieser Benutzer einmal anmelden → Profil → Sicherheit →
   **Langlebiges Zugriffstoken** erstellen.
3. Token + HA-URL(s) in Calis Einstellungen eintragen.

## Entities freigeben

Zwei Wege, kombinierbar:

- **Label `cali`** auf Entities oder ganze Geräte setzen (gut für Bulk).
- Integrations-**Optionen** → Entity-Picker (gut für Einzelfälle).

Alles andere ist für Cali unsichtbar. Schlösser und Alarmanlagen sind
grundsätzlich **read-only**, auch wenn sie freigegeben sind – die
Aktions-Whitelist liegt serverseitig in dieser Integration.

## Cali als Benachrichtigungsziel

In jeder Automation als Aktion **„Cali sprechen lassen"** (`cali.speak`) wählen:

```yaml
action: cali.speak
data:
  message: "Die Waschmaschine ist fertig."
  emotion: happy   # optional: neutral, happy, wink, love, surprised, crazy, sceptic, tired, sad, denying, angry, broken
  wake: true       # Cali einblenden, falls versteckt
```

## API (für den Cali-Client)

- `cali/entities` – freigegebene Entities, kompakt (Name, Bereich, Zustand, erlaubte Aktionen)
- `cali/action` – `{entity_id, action, params?}`, serverseitig whitelisted
- `cali/subscribe` – pusht `notify`-Events (aus `cali.speak`) und `state`-Updates freigegebener Entities

## Icon in Home Assistant

Die Icons liegen direkt in der Integration (`custom_components/cali/brand/`) und
werden ab Home Assistant 2026.3 über die lokale Brands-API ausgeliefert – kein
PR ans brands-Repo nötig.
