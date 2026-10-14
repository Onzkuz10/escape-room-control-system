# Testiraportti — 14.10.2026

Testiympäristö: Linux, Python 3.12, Node.js 24, paikallinen FastAPI, headless Chromium. Varsinaista macOS-laitetta tai fyysistä webkameraa ei ollut käytettävissä.

## Automaattiset tarkistukset

| Tarkistus | Tulos |
| --- | --- |
| `npm run build --prefix frontend` | TypeScript ja Vite läpäisty |
| `.venv/bin/pytest -q` | 56 testiä läpäisty |
| `bash -n scripts/setup.sh scripts/start.sh scripts/dev.sh start.command` | Läpäisty |
| `./scripts/start.sh` | Palvelin käynnistyi ja palveli molemmat näkymät |
| `python tests/browser_smoke.py` | Kaikki selaintarkistukset läpäisty |

Pytest sisältää ajastimen käynnistyksen/pysäytyksen/jatkamisen, monotonisen ajan, voittotilan lukituksen, nollauksen, timeoutin etusijan, varoitustapahtuman, tilaajan virheen eristämisen, salaisen koodin puuttumisen pelaajan tilannekuvasta, konfiguraation validoinnin, HTTP-komennot, tallennusvirheen atomisuuden, kaksi yhtäaikaista WebSocketia, uudelleenyhdistämisen ja staattiset sivureitit.

Tunnistustestit kattavat kaikki numerot 0–9, kallistukset −5°, 0° ja +5°, tyhjän ja mustan kuvan, sumean kuvan, kaksi numeroa samalla alueella, leikkautuneen numeron, ristikkäisen piirroksen sekä vakautuksen ja signaalin katoamisen. Kuvilla testattiin tuotannon OpenCV-muotovertailua. Synteettinen kamerakuva käy läpi varsinaisen kameratunnistussilmukan ja tuottaa pelaajien WebSocketiin onnistumistilan. Kameran laitteisto korvataan vain tässä testissä; sovelluksessa kameraa ei simuloida.

Testirunko tuottaa yhden Starlette/AnyIO-riippuvuuden deprecation-varoituksen. Testit läpäisevät; varoitus ei koske sovelluksen ajastimen tai kameran toiminnallisuutta.

## Selaimella testatut käyttäjäpolut

- Dashboard ja Player Display yhtä aikaa aidon HTTP-/WebSocket-backendin kanssa.
- Ajastimen käynnistys ja pysäytys; pelaajien aika vastaa ohjauspaneelin aikaa ja pysyy pysäytettynä.
- Numerot 4278: täsmälleen kolme vihreää merkkivaloa. Muutos 4279: neljä vihreää valoa, voittoteksti ja 24 animoitua hiukkasta.
- Nollaus vahvistusdialogin kautta: aika palautuu ja merkkivalot tyhjentyvät.
- Oikean koodin muokkaus 0138: alkunolla säilyy ja asetukset palautuvat sivun uudelleenlatauksessa.
- Tunnistusalueen säätö prosenttikentällä sekä hiirellä vetäminen; backend säilyttää muuttuneet koordinaatit.
- Ratkaisun simulointi yhdellä painikkeella.
- Kahden sekunnin pelin timeout näkyy pelaajien näytössä 00:00-tilana.
- Pelaajien sivun avaaminen uudelleen palauttaa backendin nykyisen päätöstilan.
- Pelaajien WebSocket-viesteissä ei ole oikeaa koodia tai tapahtumalokia. Pelaajien sivulla ei ole painikkeita, syötekenttiä tai valikoita.
- Kameratilan valinta ilman kameraa ja paluu manuaaliseen testiin.
- Dashboardin leveydet 390, 768, 1024 ja 1440 px; ei vaakavieritystä. Pelaajien näyttö 390 ja 1440 px.
- Ei JavaScript-poikkeuksia eikä ulkoisia verkkopyyntöjä käyttöliittymän käytön aikana.

## Macilla tehtävä lopullinen laitetesti

Noudata README:n kohtaa **Testi oikeilla numerolapuilla**. Tarkista erikseen:

1. AVFoundation avaa oikean kameran ja macOS:n käyttöoikeus annetaan terminaaliohjelmalle.
2. Live-kuva näyttää neljä fyysistä numerolappua ja rajaukset vastaavat niitä.
3. Numerot 0–9 tunnistuvat tulostetuista lapuista omassa valaistuksessa.
4. Peitetty tai poistettu lappu poistaa aktiivisen merkkivalon.
5. Neljä oikeaa numeroa pysäyttää ajastimen ja käynnistää animaation.
6. Erillinen samassa verkossa oleva laite näyttää saman ajan ja merkkivalot.

Fyysisen kameran laatu, valotus, macOS-käyttöoikeudet, paikallisverkon palomuuri ja Safari-fullscreen jäävät laitekohtaisesti tarkistettaviksi. Demoon ei väitetä suoritetun macOS-laitetestiä.
