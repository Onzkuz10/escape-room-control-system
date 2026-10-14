# Escape Room Control System — Version 1

## Päätökset

React, TypeScript ja Vite tuottavat staattisen käyttöliittymän. FastAPI palvelee buildin, HTTP-komennot, MJPEG-kamerakuvan ja WebSocketin samalla portilla. Yksi paikallinen Python-prosessi omistaa kaiken pelitilan ja kameran. Tuotantokäyttöön ei tarvita Node-prosessia, pilveä, tietokantaa, CDN:ää eikä ulkoisia fonttipalveluita. Asennuksen riippuvuuksien lataaminen tarvitsee internetin; käyttö toimii offline.

Ajastin käyttää `time.monotonic()`-kelloa: järjestelmäkellon siirto ei muuta peliaikaa. Backend päivittää tilan 100 ms välein; selaimet näyttävät viimeisimmän tilan, eivät hallitse omia ajastimia. Ajan päättyminen tarkistetaan ennen numerohavainnon soveltamista. Ratkaisu ja ajan loppuminen jäävät voimaan nollaukseen asti. Ajastin pysähtyy ratkaisuun. Pause säilyttää havainnot. Nollaus palauttaa peliajan, tyhjentää havainnot ja aloittaa vakautuksen alusta. Koodin tai keston muuttaminen vaatii pysäytetyn pelin; keston muutos nollaa pelin.

WebSocket on vain lukua varten. Komennot lähetetään validoituina HTTP-pyyntöinä. Tämä tekee virheiden näyttämisestä ja API:n testauksesta suoraviivaista. Pelaajien `role=player`-tilannekuva ei sisällä oikeaa koodia, kameratietoja tai tapahtumalokia. Rooleja ei ole todennettu: kyseessä on luotetun paikallisverkon demo. Ohjauspaneeli ja API ovat kaikkien samassa verkossa olevien saavutettavissa. Ennen käyttöä julkisessa tai osallistujille avoimessa verkossa lisää ohjaajan tunnistus, erilliset verkot ja HTTPS. V1 ei ole fyysisen poistumisoven tai turvallisuuslaitteen ohjain.

## Tietovirta

```mermaid
flowchart LR
  Camera[Mac-webkamera] --> Capture[OpenCV / kuvaussäie]
  Capture --> MJPEG[MJPEG-kuva]
  MJPEG --> Dashboard[Dashboard /]
  Capture --> ROI[4 rajattua aluetta]
  ROI --> Recognition[OpenCV-mallit + Tesseract]
  Recognition --> Stabilizer[Ajallinen vakautus]
  Stabilizer --> State[FastAPI / yhteinen pelitila]
  Dashboard -->|HTTP-komennot| State
  State -->|WebSocket 10 Hz| Dashboard
  State -->|WebSocket 10 Hz| Player[Player Display /player]
  State --> Bus[Tapahtumaväylä]
  Bus --> Audio[Audio Manager / tulevat äänitoiminnot]
  Bus --> Future[Tulevat vihjeet ja automaatiot]
```

## Rakenne

```text
backend/
  main.py          HTTP, WebSocket, taustasilmukat, asetusten tallennus
  state.py         Pelin tilakone ja ajastin
  models.py        Pydantic-validointi ja oletusalueet
  camera.py        Kameran omistus, kuvaussäie ja JPEG-puskuri
  recognition.py   Kuvan esikäsittely, muotovertailu, OCR ja vakautus
  events.py        Tapahtumaväylä ja viimeisten 60 tapahtuman historia
  audio.py         Erillinen Audio Manager -laajennuspiste
  assets/          Paikalliset numeromallien fontit ja lisenssi
frontend/src/
  Dashboard.tsx    Ohjauspaneeli ja pelin asetukset
  CameraPanel.tsx  Live-kuva ja rajausalueiden säätö
  Player.tsx       Pelaajien näyttö ja onnistumisanimaatio
  useRoom.ts       WebSocket, uudelleenyhdistäminen ja komennot
  types.ts         Tilatyypit ja ajastimen esitys
  styles.css       Responsiivinen visuaalinen järjestelmä
printables/        Paikallinen, tulostettava numerolappusarja 0–9
scripts/           Asennus, käynnistys ja kehityskäyttö
runtime/config.json Paikallisesti tallennetut asetukset; ei versionhallintaan
```

## Kameratunnistus

Kamera sijaitsee palvelinta ajavalla Macilla. macOS käyttää OpenCV:n AVFoundation-ajuria. Kameran avaaminen tapahtuu käyttäjän painikkeesta. Pelaajien laite vastaanottaa vain pelitilan; sen selain ei tarvitse kamerakäyttöoikeutta eikä getUserMedia/HTTPS-yhteyttä.

Kuvaus on erillisessä säikeessä; hidas OCR ei pysäytä kameran esikatselua tai ajastinta. Tunnistus lukee aina uusimman kuvan, jotta jono ei kasva. Tunnistus suoritetaan `asyncio.to_thread`-työnä, yleensä noin 2–5 kertaa sekunnissa. Tesseract-aliprosessilla on aikaraja. Kamerakuvia ei tallenneta levylle.

Jokaisen alueen käsittely:

1. Harmaasävy, sumeuden ja pimeyden hylkäys, Gaussian-suodatus ja Otsu-kynnystys.
2. Musteen määrän, merkittävien ulkoääriviivojen ja numeron koon tarkistus. Tyhjät alueet, useat merkit ja reunasta leikkautuneet numerot hylätään.
3. Numeron normalisointi ja vertailu paikallisiin 0–9-malleihin. Mallit kattavat mukana toimitetun fontin, lihavoinnin, OpenCV:n kaksi fonttia ja ±6° kallistuksen. Hyväksyminen vaatii vähintään 84 % muotosamankaltaisuuden ja 8,5 prosenttiyksikön eron seuraavaan ehdokkaaseen.
4. Rajatapauksissa paikallinen Tesseract (`--psm 13`, numerorajaus) hyväksyy havainnon vain, jos OCR-varmuus on vähintään 75, muotomalli on sama numero, samankaltaisuus vähintään 68 % ja ero seuraavaan vähintään 3,5 prosenttiyksikköä. Vahva muotovertailu voi tunnistaa numeron, jonka OCR lukisi kirjaimena. Näytön varmuusarvo on havaintopisteytys, ei kalibroitu virhetodennäköisyys.
5. Vähintään kolme peräkkäistä samaa havaintoa ja vähintään 0,65 sekunnin vakaus. Ristiriitainen numero poistaa vanhan numeron heti; tyhjä tai epävarma signaali poistaa sen 0,55 sekunnissa. Yli 1,5 sekunnin näytekatko aloittaa vakautuksen uudelleen.

Ratkaisun hyväksyminen kameratilassa vaatii lisäksi, että saman tuoreen kuvan kaikki neljä havaintoa ovat varmoja ja vastaavat vakautettuja numeroita. Lyhyt epävarman signaalin merkkivalon viive ei voi yksin käynnistää voittoa.

Yli kaksi sekuntia vanhaa kamerakuvaa ei käytetä. Kameran sulkeminen tai vika tyhjentää aktiiviset kamerahavainnot. Käynnissä olevan tunnistustyön tulos pudotetaan, jos sen aikana tapahtui nollaus, tilanvaihto tai alueiden muutos. Ratkaistu tila säilytetään nollaukseen asti.

Tunnistuksen tulos ei koskaan riipu oikeasta koodista. V1 on tarkoitettu selkeille mustille painetuille numeroille valkoisella paperilla; vapaata käsialaa, suurta perspektiivivääristymää, heijastusta ja sekavaa taustaa ei luvata tunnistettaviksi. Käytä mukana toimitettuja lappuja ensimmäiseen testiin.

## Tapahtumat ja laajennukset

Tapahtumissa on järjestysnumero, UTC-aikaleima, tyyppi ja payload. V1 julkaisee:

| Tapahtuma | Merkitys |
| --- | --- |
| `system.ready` | Palvelin valmis |
| `timer.started`, `timer.paused` | Ajastimen ohjaus |
| `timer.warning` | 5 minuutin raja alittuu kerran pelissä |
| `timer.expired` | Aika loppui |
| `digits.changed` | Havaitut numerot ja oikeat paikat muuttuvat |
| `game.solved`, `game.reset`, `game.simulated` | Pelin päätös, nollaus ja testaus |
| `mode.changed`, `config.changed`, `camera.status` | Ohjaus- ja kameramuutokset |

`AudioManager` tilaa tapahtumaväylän ja valitsee tulevan äänitoiminnon tunnisteen. V1 ei lataa tai soita musiikkia. Vihje- ja automaatiomoduulit voivat myöhemmin tilata saman väylän. Hidas toiminto tulee välittää työjonoon; tapahtumankäsittelijä ei saa estää ajastinta. Kuuntelijan poikkeus ei pysäytä muita kuuntelijoita.

Vihjeiden lisääminen tarkoittaisi uutta validoitua komentoa, ajallisesti rajattua viestiä pelitilaan ja Player-komponenttia. Vaiheisiin reagoiva musiikki voi tilata uuden `stage.changed`-tapahtuman. Näitä ei ole toteutettu V1:een. Tapahtumahistoria ja pelitila ovat muistissa, asetukset levyllä. Tila ja yhteydet eivät jakaudu usealle työntekijälle, joten käytä aina `--workers 1`.
