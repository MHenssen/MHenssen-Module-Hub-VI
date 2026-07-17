# Home Assistant — Vakantiepakket

Klaar-voor-gebruik "vakantiemodus" voor 2,5 week afwezigheid, gebouwd rond de
bestaande Alarmo-installatie, de deur-/bewegingssensoren, sirenes, camera's en
de iOS companion-apps.

## Wat zit erin (`packages/vakantie.yaml`)

| Onderdeel | Wat het doet |
|---|---|
| `input_boolean.vakantiemodus` | De hoofdschakelaar waar alles op draait |
| Script **Vakantie – vertrekcheck** | Controleert of beide deuren dicht zijn (weigert anders!), zet verwarming tuinhuis + airco + alle lampen + TV uit, schakelt vakantiemodus in en zet Alarmo op *away* |
| Avondsimulatie | Woonkamer → tafellampen → (soms) leeshoek rond zonsondergang, elke dag met andere willekeurige tijden |
| Bedtijdsimulatie | Vanaf ±22:30: slaapkamer aan, beneden uit, badkamer kort aan, daarna alles donker — met willekeurige vertragingen |
| Alarmo afgegaan | Camerasnapshot, alle lampen 100%, beide sirenes aan, **kritieke** pushmelding (doorbreekt stil/focus) naar Mark én Sophie met foto |
| Rookmelder | Kritieke melding naar beide telefoons + alle lampen aan (staat áltijd aan, ook buiten vakanties) |
| Dagrapport 19:00 | Eén melding per dag: alarmstatus, deuren, backup-status, zonopbrengst, verbruik. Blijft dit bericht uit → er is iets mis met HA of internet thuis |
| Activiteit achterdeur | Melding + snapshot bij camera-events tijdens vakantie |
| Digitale waakhond (optioneel, standaard uit) | Blafgeluid op de Nest-speaker bij detectie aan de voordeur na zonsondergang |

## Installatie

1. Zet in `configuration.yaml` (eenmalig, overslaan als het er al staat):
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Kopieer `packages/vakantie.yaml` naar `/config/packages/vakantie.yaml`
   (map `packages` aanmaken als die nog niet bestaat).
3. Maak de map `/config/www/snapshots` aan (nodig voor de camerafoto's in
   meldingen).
4. Herstart Home Assistant.
5. Voeg `input_boolean.vakantiemodus` en het script toe aan je dashboard.

## Alarmo-checklist vóór vertrek

Open Alarmo (zijbalk) en controleer voor de modus **Away**:

- [ ] Sensoren gekoppeld: voordeur- en achterdeursensor, PIR bijkeuken,
      PIR voordeur, PIR toilet, bewegingssensor wijn, de drie human presence
      sensors
- [ ] De rookmelder **niet** als inbraaksensor (die heeft z'n eigen
      automatisering)
- [ ] Vertraging: *exit delay* mag kort (je armt toch via de app/het script),
      *entry delay* kort (30 s) — je komt toch pas over 2,5 week terug
- [ ] Sirene-tijd: `number.sensor_sirene_tijd` op het maximum
- [ ] Test één keer: arm *away*, loop langs een PIR, kijk of de melding met
      foto binnenkomt en de sirene afgaat

## iOS: kritieke meldingen testen

De alarm- en rookmeldingen gebruiken `critical: 1` — die doorbreken
stil-/focus-modus. Test dit vóór vertrek: de companion-app vraagt eenmalig om
toestemming voor kritieke meldingen (Instellingen → Companion App →
Notificaties).

## Buiten HA om regelen (belangrijk!)

- **Externe uptime-check**: als HA of je internet uitvalt, kan HA je dat niet
  vertellen. Maak een gratis monitor aan op bijv. UptimeRobot die
  `https://ha.henssen.uk` elke 5 min aanroept en mailt bij downtime (een
  403-antwoord telt gewoon als "online").
- **Buurman/familie**: geef iemand een sleutel en zet diens nummer klaar; de
  meldingen vertellen jou *dat* er iets is, iemand ter plaatse lost het op.
- **Post/brievenbus**: geen automatisering tegen opgestapelde post — vraag de
  buren.

## Opvallende punten in de huidige setup (optimalisatie-ideeën)

1. **Gevaarlijke naamgeving**: `switch.lampen_voortuin_stopcontact_1` is in
   werkelijkheid de **verwarming van het tuinhuis**. Hernoem het entity-id
   (Instellingen → Apparaten → entiteit → tandwiel) voordat een automatisering
   die "alle voortuinlampen" aanstuurt per ongeluk wekenlang een kachel aanzet.
2. **Dubbele apparaten**: er staan twee complete setjes `iphone_van_mark`-
   sensoren (het oude iPhone 11 Pro-profiel) en dubbele lampen
   (`sweet_lampen`/`sweet_lampen_2`, `ganglamp`/`ganglamp_2`,
   `tuinlamp`/`tuinlamp_2`, drie keer `tafellamp`). Oude apparaten verwijderen
   maakt automatiseringen betrouwbaarder.
3. **Geen waterlekkagesensoren**: voor een paar tientjes leg je LSC/Tuya-
   lekkagesensoren bij wasmachine, vaatwasser en cv — juist bij 2,5 week
   afwezigheid de moeite waard.
4. **Vriezerbewaking**: een slimme plug met verbruiksmeting op de vriezer +
   automatisering "vermogen < 1 W gedurende 1 uur → melding" voorkomt een
   ontdooide vriezer bij thuiskomst.
5. **Camera Olivier**: zet tijdens de vakantie de privacy-mode uit en opname
   aan — extra binnenshuis-oog; thuis kan hij weer op privacy.
