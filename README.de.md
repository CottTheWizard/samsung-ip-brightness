# Samsung IP Brightness – deutsche Anleitung

Eine kleine Windows-App, die die **echte Panelhelligkeit** kompatibler Samsung-Monitore direkt über das lokale Netzwerk steuert. Mit Schieberegler, Tray-Symbol, täglichem Zeitplan, globalen Tastenkürzeln und optionalem Autostart. Kein Cloud-Konto und kein Servicemenü nötig.

**Getestetes Modell:** Odyssey OLED G9 **G95SC**, IP Remote aktiviert. Andere Tizen-Monitore können funktionieren, sind aber nicht bestätigt. Die App verwendet `backlightControl` auf HTTPS-Port **1516** und die Helligkeitsskala **0–50**. Der Samsung-Befehl `brightnessControl` wird nicht verwendet, weil er bei manchen Geräten die Schattendetails steuert.

## Einrichtung

1. **Python installieren:** [Python für Windows](https://www.python.org/downloads/windows/), Version 3.10 oder neuer. **Tcl/Tk** und den **Python Launcher (`py`)** mitinstallieren. Zusätzliche Python-Pakete werden nicht benötigt.
2. Auf GitHub **Code → Download ZIP** wählen. ZIP in einen dauerhaften Ordner entpacken.
3. PC und Monitor mit demselben vertrauenswürdigen lokalen Netzwerk verbinden. HDMI/DisplayPort allein reicht für die Netzwerksteuerung nicht.
4. Am Monitor **Einstellungen → Alle Einstellungen → Verbindung → Netzwerk → Experteneinstellungen → IP-Fernbedienung / IP Remote** einschalten. Die Menünamen können je nach Firmware abweichen. Dafür ist kein Servicemenü nötig.
5. Unter **Netzwerkstatus → IP-Einstellungen** die IPv4-Adresse des Monitors nachsehen. Im Router möglichst eine feste DHCP-Zuweisung einrichten.
6. **`Start.cmd` doppelklicken.** Im Fenster die eigene Monitor-IP eintragen und **Pair monitor** anklicken.
7. Die Anfrage am Monitor innerhalb von 40 Sekunden mit **Erlauben** bestätigen.
8. Den Regler bewegen und prüfen, ob sich die Bildhelligkeit sichtbar ändert. Eine erfolgreiche Zahlenrückmeldung allein garantiert das nicht auf jedem Modell.

## Desktop-Verknüpfung und Autostart

**`Install.ps1` rechtsklicken → Mit PowerShell ausführen.** Das Skript erstellt Verknüpfungen auf dem Desktop und im Startmenü und fragt nach dem optionalen Autostart bei der Windows-Anmeldung. Es lädt keine Programme herunter und verändert keine Monitoreinstellungen.

Falls Windows die Skriptausführung blockiert, nach Prüfung des Skripts im entpackten Ordner ausführen:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1
```

Den Ordner danach nicht verschieben. Falls doch, `Install.ps1` erneut ausführen.

## Bedienung

| Funktion | Bedienung |
| --- | --- |
| Dunkler | **Strg + Alt + F11** |
| Heller | **Strg + Alt + F12** |
| Wert direkt setzen | Schieberegler, 0–50 |
| Fenster wieder öffnen | Desktop-/Startmenü-Verknüpfung oder `Start.cmd` |
| Fenster ausblenden | Fenster schließen; Tastenkürzel bleiben aktiv |
| App vollständig beenden | **Quit app** |

Pro Tastendruck ändert sich die Panelhelligkeit um **3 Einheiten**. Die App muss laufen. Erneutes Starten öffnet das vorhandene Fenster. Netzwerkbefehle werden nacheinander im Hintergrund verarbeitet.

## Tray-Symbol

Das Sonnensymbol erscheint unten rechts im Windows-Infobereich, gegebenenfalls unter **^**. Anklicken öffnet das Fenster. Rechtsklick bietet **Öffnen**, **Dunkler**, **Heller**, **Zeitplan ein/aus** und **Beenden** (englische Menütexte). Der Tooltip zeigt die zuletzt bekannte Helligkeit. Beim Schließen des Fensters laufen Zeitplan und Tastenkürzel weiter. Nach einem Explorer-Neustart wird das Symbol wiederhergestellt.

## Täglicher Zeitplan

Im Fenster unter **Daily schedule** eine Uhrzeit und einen Wert je Zeile eintragen:

```text
08:00=30
20:00=15
23:00=5
```

**Enable daily schedule** aktivieren und **Save schedule** anklicken. Das Beispiel ist zunächst **deaktiviert**. Zeiten müssen im 24-Stunden-Format `HH:MM` stehen und dürfen nicht doppelt vorkommen; Helligkeitswerte reichen von 0 bis 50.

Der Plan wiederholt sich täglich nach der **lokalen Windows-Uhrzeit**, einschließlich Sommer-/Winterzeit. Beim Aktivieren, App-Start und nach dem Aufwachen wird der zuletzt fällige Eintrag angewendet. Vor der ersten Tageszeit gilt der letzte Eintrag vom Vortag. Manuelle Änderungen bleiben bis zum nächsten Zeiteintrag erhalten.

Ist der Monitor nicht erreichbar, versucht die App es nach 60 Sekunden erneut, ohne ein Fenster aufzudrängen. Sie weckt den Monitor nicht auf. PC und App müssen laufen. Es werden keine Windows-Aufgaben angelegt. Die Helligkeit wird direkt umgestellt, ohne sanften Übergang. Über das Tray-Menü kann der gespeicherte Zeitplan pausiert und fortgesetzt werden.

## Datenschutz

Das öffentliche Projekt enthält keine vorkonfigurierte Monitor-IP und keine Zugangstoken. Die eigene IP und der mit **Windows DPAPI verschlüsselte** Token werden ausschließlich unter `%LOCALAPPDATA%\SamsungIPBrightness\config.json` gespeichert. Diese Datei nicht veröffentlichen. Auf einem anderen Windows-Konto muss neu gekoppelt werden.

Keine Cloud, Werbung oder Telemetrie. Zur lokalen Verbindung wird das selbstsignierte Monitor-Zertifikat ohne Prüfung akzeptiert: deshalb nur in einem vertrauenswürdigen Netzwerk verwenden. Keine Monitorports ins Internet freigeben. Ein lokaler Listener auf `127.0.0.1:47864` ermöglicht das erneute Öffnen und lokale Helligkeitsbefehle; andere Programme auf demselben PC können ihn ebenfalls ansprechen. Er ist nicht im LAN erreichbar.

## Wenn etwas nicht funktioniert

- **Keine Verbindung:** Monitor eingeschaltet? Richtige IP? IP Remote aktiviert? Gastnetz oder Netzwerkisolation können die Verbindung verhindern.
- **Kopplung fehlgeschlagen:** Auf die Anfrage am Monitor achten und erneut koppeln. Normalen PC-Eingang anzeigen lassen.
- **Befehl nicht unterstützt:** Modell, Firmware oder Bildmodus können die Funktion einschränken. Die App schaltet den Bildmodus nicht selbst um.
- **Zahlen ändern sich ohne sichtbare Wirkung:** Die Firmware bestätigt möglicherweise nur den Wert. Mit der Helligkeitseinstellung im Monitormenü vergleichen. In einem GitHub-Issue Modell und Firmware nennen, keine Token oder Konfigurationsdateien anhängen.
- **Tastenkürzel belegt:** Andere Apps mit Strg + Alt + F11/F12 beenden und diese App neu starten. Bei manchen Tastaturen zusätzlich **Fn** drücken. Auch den alten privaten Prototyp vorher beenden.
- **Fenster öffnet nicht:** Im Terminal `py -3 samsung_brightness.py` ausführen, um den Fehler zu sehen. Python benötigt Tcl/Tk. Nach Verschieben des Ordners die Verknüpfungen neu installieren.

## Entfernen

App mit **Quit app** beenden und `Uninstall.ps1` ausführen. Es entfernt nur die Verknüpfungen und den Autostart. Anschließend den Projektordner löschen. Zum Löschen der Kopplung zusätzlich `%LOCALAPPDATA%\SamsungIPBrightness` entfernen.

Weitere technische Details, Tests und Protokollreferenzen: [English README](README.md). Lizenz: [MIT](LICENSE).
