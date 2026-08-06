# Home Assistant — pakketten

Twee pakketten voor `/config/packages/`:

- **`vakantie.yaml`** — vakantiemodus, aanwezigheidssimulatie en alarmreacties
  (zie hieronder)
- **`buitenverlichting.yaml`** — buitenlampen die écht uitgaan (zie onderaan)

---

# Vakantiepakket

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
| Alarmo afgegaan | Camerasnapshot, **binnen**lampen 100%, alleen de losse sirene, **kritieke** pushmelding (doorbreekt stil/focus) naar Marks iPhone met foto. Buitenlampen en camerasirenes blijven bewust uit (burenvriendelijk bij vals alarm) |
| Automatische reset | Zodra Alarmo terugkeert uit "triggered" (of na uiterlijk 10 min als vangnet): sirene uit, binnenlampen uit, melding "alarm gereset". Alarmo herbewapent zichzelf naar *away* |
| Rookmelder | Kritieke melding naar Marks iPhone + álle lampen aan, ook buiten — bij echt brand wil je juist dat de buurt het ziet (staat áltijd aan, ook buiten vakanties) |
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

- [ ] Sensoren gekoppeld — **alleen binnenshuis**: voordeur- en
      achterdeursensor, PIR bijkeuken, PIR voordeur, PIR toilet,
      bewegingssensor wijn en de human presence sensor in de bijkeuken
- [ ] De **buiten**-presence-sensors (voordeur en achterdeur) **niet** in
      Alarmo — die zien passanten/katten en veroorzaken valse alarmen. Idem
      voor de rookmelder (die heeft z'n eigen automatisering)
- [ ] *Trigger time* van de away-modus op **5 minuten** — daarna keert Alarmo
      zelf terug naar armed_away en ruimt de reset-automatisering op
- [ ] Vertraging: *exit delay* mag kort (je armt toch via de app/het script),
      *entry delay* kort (30 s) — je komt toch pas over 2,5 week terug
- [ ] Sirene-tijd: `number.sensor_sirene_tijd` op ±5 minuten (niet maximaal —
      de reset zet 'm sowieso uit)
- [ ] Camera's mogen hun eigen sirene **niet** starten:
      `switch.bijkeuken_camera_achterdeur_auto_trigger_siren` en
      `switch.olivier_slaapkamer_camera_olivier_auto_trigger_siren` uit
- [ ] Controleer dat de meldingsactie `notify.mobile_app_iphone_van_mark`
      bestaat én je **iPhone 15 Pro** is: Ontwikkelaarshulpmiddelen → Acties →
      zoek op "mobile_app". (Er hangt ook nog een oud iPhone 11 Pro-profiel in
      HA — verwijder dat apparaat het liefst helemaal)
- [ ] Test één keer: arm *away*, loop langs een PIR, kijk of de melding met
      foto binnenkomt, de sirene afgaat én alles na 5 min vanzelf reset

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

---

# Buitenverlichting gegarandeerd uit (`packages/buitenverlichting.yaml`)

## Het probleem

De oude automatisering deed één `scene.turn_on` + één `light.turn_off` en
hoopte er het beste van. Bij LSC/Tuya-lampen loopt elk commando via de
Tuya-cloud; stuur je er vijftien tegelijk, dan sneuvelen er standaard één
of twee — elke nacht een andere. Daar komt bij:

- **`scene.turn_on` schakelt alleen entiteiten die ín de scène staan.** Elke
  lamp die je later hebt toegevoegd, of die offline was toen je de scène
  maakte, zit er niet in en gaat dus nooit uit.
- **Een lamp die om 00:30 offline is** kan niets ontvangen en komt later
  gewoon brandend weer online.

## De oplossing

`script.buitenlampen_gegarandeerd_uit` stuurt het uit-commando, **controleert
daarna of het gelukt is**, en herhaalt dat alleen voor de lampen die nog aan
staan — tot zes keer, met oplopende pauzes (15 s → 30 s → 60 s). Lukt het dan
nog niet, dan krijg je één stille melding met de namen van de boosdoeners.

Twee automatiseringen roepen dat script aan:

| Automatisering | Wanneer |
|---|---|
| `Buitenlampen: automatisch uit (schema)` | zo–do 00:30, vr/za 01:30 (jouw oude tijden) — **tenzij er muziek speelt** |
| `Buitenlampen: watchdog (nachtcontrole)` | 03:00 (harde deadline), 04:00 en een half uur vóór zonsopkomst |

De watchdog vangt precies de lampen die tijdens het schematijdstip offline
waren. Staat alles al uit, dan stopt het script direct — geen onnodig
cloudverkeer.

## Muziek = feestje bezig

Speelt er om 00:30 / 01:30 muziek op de **Nest buiten**
(`media_player.nest_audio`), de **keukenspeaker**
(`media_player.chromecastaudio1336`) of de groep **Alle speakers**
(`media_player.keuken_en_woonkamer`), dan slaat het schema over en blijft de
buitenverlichting gewoon aan. Om **03:00** gaan de lampen hoe dan ook uit —
ook als de muziek dan nog speelt.

Wil je liever dat de lampen uitgaan zodra de muziek stopt (in plaats van
wachten tot 03:00)? Dat is een extra automatisering met een `for:`-vertraging
op de mediaspeler; vraag erom als je dat handiger vindt.

## Installeren

1. Kopieer `packages/buitenverlichting.yaml` naar
   `/config/packages/buitenverlichting.yaml`.
2. **Controleer de lampenlijst** bovenin het bestand. Hij is afgeleid uit de
   entiteitenlijst; namen als *Bar licht* en *LSC Moodlight* kunnen ook
   binnen hangen. Haal weg wat niet buiten zit.
3. Herstart of herlaad de YAML-configuratie.
4. **Schakel de oude automatisering "Buitenlampen: Automatisch uit (Schema)"
   uit** (Instellingen → Automatiseringen → drie puntjes → Uitschakelen).
   Niet verwijderen — voor als je iets wilt terugkijken.
5. Test overdag: zet een paar buitenlampen aan en voer het script handmatig
   uit via Instellingen → Automatiseringen & scènes → Scripts.

## Als het daarna nóg misgaat

Kijk in de logboekweergave van de lamp (klik de entiteit → Logboek) of hij
`unavailable` was. Structureel wegvallende LSC-lampen wijzen op zwak wifi in
de tuin — een goedkope repeater of een AP buiten lost meer op dan welke
automatisering ook. Overweeg voor die lampen op termijn Zigbee in plaats van
Tuya-wifi: lokaal, sneller en zonder cloud die commando's laat vallen.
