# LOCK / Escape Room Control System — Version 1

Toimiva paikallinen pakohuoneen ohjausdemo. React + TypeScript + Vite, Python + FastAPI, OpenCV ja paikallinen Tesseract. Ohjauspaneeli, pelaajien näyttö, neljä numerohavaintoa ja ajastin jakavat yhden backend-tilan WebSocketilla. Manuaalinen testitila toimii ilman kameraa.

## macOS: ensimmäinen käynnistys

Tarvitset macOS:n, Python 3.11+ (suositus 3.12), Node.js 20.19+ tai 22.12+ ja kameratunnistukseen Tesseractin. Asenna Homebrew tarvittaessa sen virallisesta osoitteesta https://brew.sh, sitten:

```bash
brew install python@3.12 node tesseract
cd /polku/escape-room
./scripts/setup.sh
./scripts/start.sh
```

`setup.sh` luo projektikohtaisen `.venv`-ympäristön, asentaa Python- ja npm-riippuvuudet ja rakentaa käyttöliittymän. Se ei tee järjestelmälaajuisia pip-asennuksia. Jos `python3` osoittaa vanhaan Python-versioon, käytä ensin Homebrewn Pythonia PATHissa: `export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"`.

Avaa:

- Dashboard: **http://localhost:8000**
- Player Display: **http://localhost:8000/player**

Pidä terminaali auki. Lopeta **Ctrl+C**. Seuraavilla kerroilla riittää `./scripts/start.sh`. Projektin `start.command` toimii myös Finderistä kaksoisnapsauttamalla, kun asennus on tehty. Jos macOS ei avaa sitä, käytä terminaalikomentoa.

Toinen portti: `ESCAPE_PORT=8080 ./scripts/start.sh`. Käyttöliittymän muutosten jälkeen suorita `npm run build --prefix frontend` ja käynnistä palvelin uudelleen. Käytä aina yhtä backend-prosessia; useat työntekijät eivät jaa tilaa tai kameraa.

## Pelaajien näyttö toisella laitteella

Liitä Mac ja pelaajien laite samaan paikallisverkkoon. Käynnistysskripti näyttää Macin en0/en1-verkkoliitäntöjen IP-osoitteet. Tarvittaessa tarkista osoite kohdasta **Järjestelmäasetukset → Wi-Fi → Tiedot → TCP/IP** tai terminaalista `ipconfig getifaddr en0`.

Avaa pelaajien laitteella esimerkiksi **http://192.168.1.25:8000/player**. Korvaa IP Macin osoitteella. Pelaajien laitteella `localhost` viittaisi siihen laitteeseen, joten käytä Macin verkko-osoitetta. Salli Pythonin saapuvat yhteydet macOS:n palomuurikyselyssä. Vierasverkon laite-eristys voi estää yhteyden.

Kaksoisnapsautus pelaajien näytössä pyytää selaimen fullscreen-tilaa. Safari-/iOS-versioista riippuen käytä selaimen omaa koko näytön toimintoa. Näytössä ei ole ohjauspainikkeita. Estä Macin ja näyttölaitteen automaattinen lepotila pelin ajaksi; tarvittaessa Macissa aja toisessa terminaalissa `caffeinate -di`.

## Nopea testi ilman kameraa

1. Avaa Dashboard ja Player Display rinnakkain. Oletuskoodi on **4279**, peliaika **60 minuuttia**.
2. Manuaalinen tila on oletuksena käytössä. Kameranäkymän laput ovat selvästi merkitty testiesikatselu.
3. Käynnistä ajastin. Molemmissa näkymissä sama aika laskee.
4. Syötä paikkojen testinumeroiksi **4**, **2**, **7** ja **8**. Kolme merkkivaloa on vihreänä ja neljäs lukittu.
5. Vaihda viimeinen numero **9**: kaikki valot muuttuvat vihreiksi, ajastin pysähtyy ja pelaajien onnistumisanimaatio käynnistyy.
6. Nollaa huone. Nollauskysely suojaa käynnissä olevaa peliä vahingossa tapahtuvalta resetiltä.
7. **Simuloi ratkaisu** testaa koko onnistumisketjun yhdellä painikkeella. Se vaihtaa manuaaliseen tilaan ja syöttää tallennetun oikean koodin.

Numeroita ja ratkaisua voi testata myös ennen ajastimen käynnistystä. Kameratilassa poista oikeat laput ennen uuden pelin nollaamista, jos et halua huoneen ratkeavan uudelleen heti vakautuksen jälkeen.

Pysäytä ajastin ennen oikean koodin tai pelin keston muuttamista. Tallenna muutos koodipaneelin painikkeella tai keston vieressä olevalla valintamerkillä. Keston tallennus nollaa pelin. Koodin ja alueiden muutos tyhjentää aiemmat havainnot. Pelaajien näyttöön ei lähetetä oikeaa koodia.

## Testi oikeilla numerolapuilla

1. Avaa Dashboardin **Tulosta laput** tai http://localhost:8000/printables/numerolaput.html. Tulosta 100 % koossa ja leikkaa valitsemasi neljä lappua. Fontti on mukana paikallisesti.
2. Aseta laput vaakasuoraan, vasemmalta oikealle. Käytä tasaista hajavaloa, valkoista alustaa ja riittävän isoa mustaa numeroa. Suuntaa kamera suoraan lappuihin. Lappujen järjestys ratkaisee.
3. Paina **Käynnistä kamera**. Fyysinen kamera avataan palvelinta ajavalla Macilla. Hyväksy käyttöoikeus Terminalille tai käyttämällesi terminaaliohjelmalle.
4. Jos macOS ei näytä kyselyä tai kuva puuttuu, tarkista **Järjestelmäasetukset → Tietosuoja ja suojaus → Kamera**. Salli terminaaliohjelma, sulje kameraa varaavat ohjelmat ja käynnistä palvelin tarvittaessa uudelleen.
5. Valitse numerotunnistuksesta **Kamera**. Paina **Säädä alueita**. Vedä jokainen alue yhden numeron ympärille ja muuta kokoa alakulmasta. Rajauksen tulee sisältää kokonainen numero ja valkoista marginaalia, ei viereistä numeroa, teippiä tai paperin reunaa. Säädöt voi tehdä myös prosenttikentillä. Paina **Tallenna alueet**.
6. Jos väärä kamera avautuu, sulje kamera, muuta säätöpaneelin **Kameran numero** (0–9) ja avaa uudelleen. Oletus on 0.
7. Odota noin sekunti vakaata kuvaa. Oikean numeron merkkivalo syttyy vihreäksi. Väärä tunnistettu numero näkyy Dashboardissa keltaisena. Tyhjä, sumea tai epävarma havainto jää odottamaan.
8. Peitä tai siirrä yksi lappu pois: sen valo sammuu tunnistusviiveen jälkeen. Tee tämä ennen koko koodin ratkaisua, koska ratkaisu lukitaan nollaukseen asti.
9. Aseta kaikki oikeat numerot paikoilleen. Molemmat näkymät ratkaisevat huoneen.

Kamera ja manuaalinen tila ovat erillisiä: live-kuvan voi pitää päällä manuaalisessa testissä, mutta tällöin vain testisyötteet vaikuttavat numeroihin. Tunnistus käyttää OpenCV:n muotovertailua ja rajatapauksissa Tesseractia. Varmuusprosentti on havaintopisteytys. Selkeä käsiala voi toimia, mutta V1:n dokumentoitu testikohde on painettu numerolappu. Katso tarkat hylkäysrajat [arkkitehtuurista](docs/ARCHITECTURE.md).

## Ylläpito ja vianmääritys

- Tallennetut asetukset ovat `runtime/config.json`: koodi, kesto, rajausalueet ja kameraindeksi. Pelitila ja tapahtumaloki ovat muistissa; uudelleenkäynnistys aloittaa uuden pelin valmiustilassa.
- Viallinen asetustiedosto aiheuttaa lokimerkinnän ja turvallisten oletusten käytön. Poista tai nimeä `runtime/config.json` uudelleen oletusten palauttamiseksi.
- Portti varattu: sulje aiempi palvelin tai vaihda `ESCAPE_PORT`.
- Tesseract puuttuu: `brew install tesseract`, tarkista `tesseract --version`, käynnistä palvelin uudelleen. Manuaalinen tila toimii ilman Tesseractia.
- Numerot eivät tunnistu: tarkista tila, tarkennus, valaistus, rajaus ja musta-valkoinen kontrasti. Rajaa yksi kokonainen merkki kerrallaan. Kokeile toimitettuja numerolappuja.
- WebSocket katkeaa: käyttöliittymä ilmoittaa yhteyskatkosta ja yhdistää automaattisesti uudelleen. Pelaajan ajastin näyttää viimeisen vastaanotetun ajan katkon aikana. Backend jatkaa ajastinta; yhteyden palauduttua oikea aika palautuu.
- API:n tila: http://localhost:8000/api/health. Dokumentaatio: http://localhost:8000/docs.
- Sovellus käyttää luotettua paikallisverkkoa. V1:ssä ei ole ohjaajan kirjautumista. Älä julkaise tätä porttia internetiin. Selainrooli piilottaa ohjaustiedot pelaajien normaalista näkymästä, mutta ei ole käyttöoikeusraja.

## Kehitys ja testit

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
npm run build --prefix frontend
./scripts/dev.sh
```

Kehityksessä avaa http://localhost:5173. Vite välittää `/api`, `/ws` ja `/printables` FastAPI:lle. Kehitysskripti sulkee oman backend-prosessinsa poistuessaan. Sulje tavallinen portin 8000 palvelin ennen kehitysskriptin käyttöä.

Selaintestit ovat `tests/browser_smoke.py`: asenna tarvittaessa Playwright omassa kehitysympäristössäsi (`pip install playwright`, `python -m playwright install chromium`). Käynnistä tavallinen palvelin ensin. Testit palauttavat pelin oletuksiin ja vaativat erillisen testipalvelimen, joten älä aja niitä kesken pelin.

```bash
python tests/browser_smoke.py
```

Linux-työympäristössä läpäistiin 56 pytest-testiä: tilakone, ajastin, expiry/solve-järjestys, API-validointi, tallennusvirhe, kaksi WebSocket-yhteyttä, uudelleenyhdistämisen tilannekuva, numerot 0–9 ±5° ja tyhjien/sumeiden/monimerkkisten kuvien hylkäys. Kamerasta pelaajien onnistumiseen kulkeva testi käyttää tuotannon tunnistusputkea ja synteettistä kuvalähdettä kameraraudan sijaan. Selaintestien tulokset dokumentoidaan [testiraportissa](docs/TESTING.md). Fyysisen macOS-kameran hyväksyntäkoe on yllä kuvattu; sitä ei voitu suorittaa Linux-ympäristössä.

## Tulevat laajennukset

`backend/events.py` ja `backend/audio.py` muodostavat laajennusrajan. Audio Manager tilaa pelin tapahtumat ja valitsee tulevan äänitoiminnon tunnisteen. V1 ei toteuta musiikin toistoa, vihjejärjestelmää tai automaatioeditoria. Musiikki, vaiheiden muutokset, ajastinrajat ja pelaajaviestit voidaan lisätä erillisiksi tapahtumien tilaajiksi.

Tekniset perustelut, tietovirta ja tiedostorakenne: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Fontin lisenssi: [backend/assets/FONT-LICENSE.txt](backend/assets/FONT-LICENSE.txt).
