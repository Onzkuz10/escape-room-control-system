# LOCK / Escape Room Control System — Version 1

Toimiva paikallinen pakohuoneen ohjausdemo. React + TypeScript + Vite, Python + FastAPI, OpenCV ja paikallinen käsinkirjoitettujen numeroiden CNN-malli. Ohjauspaneeli, pelaajien näyttö, neljä numerohavaintoa ja ajastin jakavat yhden backend-tilan WebSocketilla. Manuaalinen testitila toimii ilman kameraa.

## macOS: ensimmäinen käynnistys

Tarvitset macOS:n, Python 3.11+ (suositus 3.12), Node.js 20.19+ tai 22.12+ ja projektin mukana tulevan ONNX-käsialamallin. Asenna Homebrew tarvittaessa sen virallisesta osoitteesta https://brew.sh, sitten:

```bash
brew install python@3.12 node
cd /polku/escape-room
./scripts/setup.sh
./scripts/start.sh
```

Jos päivität vanhaa asennusta, suorita `./scripts/setup.sh` uudelleen: kameraluettelon uusi riippuvuus ja macOS:n AVFoundation-sidokset asentuvat samalla.

`setup.sh` luo projektikohtaisen `.venv`-ympäristön, asentaa Python- ja npm-riippuvuudet ja rakentaa käyttöliittymän. Se ei tee järjestelmälaajuisia pip-asennuksia. Jos `python3` osoittaa vanhaan Python-versioon, käytä ensin Homebrewn Pythonia PATHissa: `export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"`.

Avaa:

- Dashboard: **http://localhost:8000**
- Player Display: **http://localhost:8000/player**

Pidä terminaali auki. Lopeta **Ctrl+C**. Seuraavilla kerroilla riittää `./scripts/start.sh`. Projektin `start.command` toimii myös Finderistä kaksoisnapsauttamalla, kun asennus on tehty. Jos macOS ei avaa sitä, käytä terminaalikomentoa.

Toinen portti: `ESCAPE_PORT=8080 ./scripts/start.sh`. Käyttöliittymän muutosten jälkeen suorita `npm run build --prefix frontend` ja käynnistä palvelin uudelleen. Käytä aina yhtä backend-prosessia; useat työntekijät eivät jaa tilaa tai kameraa.

## Windows ja käsinkirjoitettujen numeroiden tunnistus

Tunnistus käyttää valmista **ONNX Model Zoo MNIST-12 CNN** -käsialamallia nykyisen OpenCV:n kautta. Tesseractia, API-avainta, pilvipalvelua tai erillistä ML-ajoympäristöä ei tarvita. Malli ja sen lisenssit sisältyvät projektiin. `/api/health` kertoo kentissä `recognition_engine` ja `ocr_available` käytössä olevan moottorin ja mallin saatavuuden.

Valitse **Kamera** ja rajaa jokaiseen kehykseen yksi kokonainen numero. Malli on koulutettu käsinkirjoitetuille yksittäisille numeroille 0–9. Numerotunnistus näyttää mallin pisteet, kolme parasta ehdotusta sekä esikäsitellyn 28×28-kuvan, jonka malli todella näkee. Pisteet ovat mallin luottamuslukuja, eivät todennäköisyyksiä siitä, että kameratulos on oikea. Hyväksymisraja on 15/100, mutta lähes tasavahvat ehdokkaat ja selvästi virheelliset rajaukset hylätään. Ajallinen vakautus säilyy käytössä.

Käsialavertailu: `.venv\Scripts\python.exe scripts\check_handwriting.py --download`. Se käyttää ensimmäisiä 1 000 alkuperäisen MNIST-testiaineiston käsialanäytettä ja niiden tummennettuja/kallistettuja kopioita. Raportti syntyy `runtime/handwriting-test/report.json`-tiedostoon. Tulos ei mittaa fyysisen kameran tarkkuutta; kuvauskulma, tausta ja käsiala vaikuttavat edelleen.

## Pelaajien näyttö toisella laitteella

Liitä Mac ja pelaajien laite samaan paikallisverkkoon. Käynnistysskripti näyttää Macin en0/en1-verkkoliitäntöjen IP-osoitteet. Tarvittaessa tarkista osoite kohdasta **Järjestelmäasetukset → Wi-Fi → Tiedot → TCP/IP** tai terminaalista `ipconfig getifaddr en0`.

Avaa pelaajien laitteella esimerkiksi **http://192.168.1.25:8000/player**. Korvaa IP Macin osoitteella. Pelaajien laitteella `localhost` viittaisi siihen laitteeseen, joten käytä Macin verkko-osoitetta. Salli Pythonin saapuvat yhteydet macOS:n palomuurikyselyssä. Vierasverkon laite-eristys voi estää yhteyden.

Kaksoisnapsautus pelaajien näytössä pyytää selaimen fullscreen-tilaa. Safari-/iOS-versioista riippuen käytä selaimen omaa koko näytön toimintoa. Pelaajien näytössä ei ole äänten aktivointipainiketta. Ääni toistuu ohjauskeskuksen välilehdestä; pidä se auki pelin ajan. Estä Macin ja näyttölaitteen automaattinen lepotila pelin ajaksi; tarvittaessa Macissa aja toisessa terminaalissa `caffeinate -di`.

## Pre-game, diat ja taustamusiikki

Pelin alussa isoa ajastinta ympäröi tasaisesti palava meripihkanvärinen valonauha. Kun kaikki neljä tehtävää (päiväkirja, ristikko, matikkatehtävä ja kirjatehtävä) on tarkistettu, ohjaaja painaa **Seuraava näkymä** ja asettaa samalla fyysisen valonauhan välkkymään. Näytön nauha himmenee ja välkkyy; numerot suurenevat 650 ms viiveen jälkeen. Välkkyvä nauha tarkoittaa, että pelaajat saavat liikkua. Fyysistä valonauhaa ohjataan erikseen; sovellus ei ohjaa valolaitetta.

1. Avaa ohjauspaneelin **Pelin ohjaus → Diat, musiikki ja lopetusvideot**.
2. Lisää omat musiikkitiedostot erikseen pre-gameen ja peliin (MP3, WAV, OGG tai M4A). Musiikkia ei ole mukana valmiina. Valitse äänenvoimakkuus ja tarvittaessa mykistys.
3. Muokkaa diojen otsikoita ja tekstejä. Lisää, poista tai järjestä dioja. Jokaiseen diaan voi ladata oman GIF-, MP4- tai WebM-animaation tai kuvan. Valitse halutessasi myös tekstin animaatio. Videot toistuvat mykistettyinä taustamusiikin rinnalla. Enintään 20 diaa ja 80 Mt / tiedosto.
4. Paina **Tallenna esitys**. Media säilyy `runtime/media/`-kansiossa ja asetukset `runtime/config.json`-tiedostossa. Dioja ja musiikkia voi muokata valmiustilassa ja pre-gamessa.
5. Paina **Aloita pre-game näkymä**. Tavallinen ohjauskeskuksen painallus sallii äänentoiston. Musiikki kuuluu ohjauskeskuksen laitteen kaiuttimista ja toistuu silmukassa. Pelaajien näyttö toistaa vain kuvaa.
6. Vaihda dioja **Edellinen dia**- ja **Seuraava dia** -painikkeilla. Pre-game ei kuluta peliaikaa.
7. Paina **Käynnistä peli**. Ajastin käynnistyy valkoisin, isoin numeroin. Musiikki vaihtuu valittuun pelimusiikkiin; ilman pelimusiikkia toisto päättyy.
8. Pelin aikainen **Seuraava näkymä** suurentaa numeroruudut ja pienentää ajastimen. Numerot tarkistetaan automaattisesti vasta tässä näkymässä. **Edellinen näkymä** palauttaa numeronäkymästä isoon ajastimeen peliaikaa nollaamatta. Myös Seuraava näkymä kiertää takaisin ajastimeen. Kaikki oikeat numerot ratkaisevat huoneen ja pysäyttävät ajastimen sekä musiikin.

Ajastimen tauotus tauottaa myös pelimusiikin; jatkaminen jatkaa toistoa. Nollaus palauttaa valmiustilan, ensimmäisen dian ja ajastinnäkymän. Yhteyden palauduttua pelaajien näyttö saa nykyisen vaiheen, dian ja pelinäkymän automaattisesti. Ohjauskeskuksen uudelleenlatauksen jälkeen selain voi vaatia yhden napsautuksen ohjauspaneeliin äänentoiston sallimiseksi. Tiedostojen toistettavuus riippuu selaimen tukemista ääni- ja videokoodekeista.

## Nopea testi ilman kameraa

1. Avaa Dashboard ja Player Display rinnakkain. Oletuskoodi on **4279**, peliaika **60 minuuttia**.
2. Manuaalinen tila on oletuksena käytössä. Kameranäkymän laput ovat testiesikatselu.
3. Aloita pre-game, vaihda dia ja paina **Käynnistä peli**. Molemmissa näkymissä sama aika laskee.
4. Syötä testinumeroiksi **4**, **2**, **7** ja **9**. Pelaajille numerot näkyvät pieninä ilman oikeellisuuden vahvistusta ja ajastin jatkuu.
5. Vaihda viimeiseksi numeroksi **8** ja paina **Seuraava näkymä**. Numerot suurenevat. Pelaajien numerot pysyvät neutraaleina; vain ohjauskeskus näyttää yksittäisten numeroiden oikeellisuuden. Korjaa viimeiseksi numeroksi **9**: huone ratkeaa automaattisesti.
6. Nollaa huone. Nollauskysely suojaa käynnissä olevaa peliä vahingossa tapahtuvalta nollaukselta.
7. **Varmistus ja hätävara → Hyväksy ratkaisu** päättää pelin voittoon ohjaajan vahvistuksen jälkeen myös ilman kamerahavaintoa. Painike on käytettävissä vain pelin ollessa käynnissä tai tauolla.

Numeroita voi testata ennen peliä ja pre-gamen aikana, mutta ne eivät silloin ratkaise huonetta. Käynnistä peli tyhjentää pre-gamen havainnot. Kameratilassa käytetään samoja vakautus- ja tuoreustarkistuksia myös numeronäkymään siirtymisen jälkeen.

Pysäytä ajastin ennen oikean koodin tai pelin keston muuttamista. Tallenna muutos koodipaneelin painikkeella tai keston vieressä olevalla valintamerkillä. Keston tallennus nollaa pelin. Koodin ja alueiden muutos tyhjentää aiemmat havainnot. Pelaajien näyttöön ei lähetetä oikeaa koodia.

## Testi oikeilla numerolapuilla

1. Avaa Dashboardin **Tulosta laput** tai http://localhost:8000/printables/numerolaput.html. Tulosta 100 % koossa ja leikkaa valitsemasi neljä lappua. Fontti on mukana paikallisesti.
2. Aseta laput vaakasuoraan, vasemmalta oikealle. Käytä tasaista hajavaloa, valkoista alustaa ja riittävän isoa mustaa numeroa. Suuntaa kamera suoraan lappuihin. Lappujen järjestys ratkaisee.
3. Paina **Käynnistä kamera**. Fyysinen kamera avataan palvelinta ajavalla Macilla. Hyväksy käyttöoikeus Terminalille tai käyttämällesi terminaaliohjelmalle.
4. Jos macOS ei näytä kyselyä tai kuva puuttuu, tarkista **Järjestelmäasetukset → Tietosuoja ja suojaus → Kamera**. Salli terminaaliohjelma, sulje kameraa varaavat ohjelmat ja käynnistä palvelin tarvittaessa uudelleen.
5. Valitse numerotunnistuksesta **Kamera**. Paina **Säädä alueita**. Vedä jokainen alue yhden numeron ympärille ja muuta kokoa alakulmasta. Rajauksen tulee sisältää kokonainen numero ja valkoista marginaalia, ei viereistä numeroa, teippiä tai paperin reunaa. Säädöt voi tehdä myös prosenttikentillä. Rajaukset tallentuvat automaattisesti kehyksen vapauttamisen tai prosenttikentän muokkauksen jälkeen. Tallennuksen tila näkyy kameran alla.
6. Kameranäkymän **Kamera**-valikko näyttää palvelinta ajavan tietokoneen kamerat nimineen automaattisesti. Valitse haluamasi kamera ennen käynnistämistä. Lista päivittyy 10 sekunnin välein; **Päivitä kamerat** hakee laitteet heti. Vaihtaaksesi kameraa sulje nykyinen kamera, valitse toinen ja käynnistä se. Macissa käytetään AVFoundationia; myös käyttöjärjestelmän tarjoamat USB- ja virtuaalikamerat näkyvät luettelossa. Kameroita ei avata pelkkää luettelointia varten. Käyttöoikeus tai toisen sovelluksen varaus voi silti estää valitun kameran avaamisen.
7. Odota noin sekunti vakaata kuvaa. Oikean numeron merkkivalo syttyy vihreäksi. Väärä tunnistettu numero näkyy Dashboardissa keltaisena. Tyhjä, sumea tai epävarma havainto jää odottamaan.
8. Peitä tai siirrä yksi lappu pois: sen valo sammuu tunnistusviiveen jälkeen. Tee tämä ennen koko koodin ratkaisua, koska ratkaisu lukitaan nollaukseen asti.
9. Käynnistä peli ja vaihda **Seuraava näkymä** -painikkeella numeronäkymään. Aseta kaikki oikeat numerot paikoilleen. Molemmat näkymät ratkaisevat huoneen.

Kamera ja manuaalinen tila ovat erillisiä: live-kuvan voi pitää päällä manuaalisessa testissä, mutta tällöin vain testisyötteet vaikuttavat numeroihin. Tunnistus käyttää paikallista MNIST CNN -käsialamallia. Mallin luottamuspisteet ja syötekuva näkyvät ohjauspaneelissa. Painetut laput ovat edelleen käytettävissä, mutta kameran todellinen tarkkuus on arvioitava käytettävällä käsialalla ja valaistuksella. Katso tarkat hylkäysrajat [arkkitehtuurista](docs/ARCHITECTURE.md).

## Ylläpito ja vianmääritys

- Tallennetut asetukset ovat `runtime/config.json`: koodi, kesto, rajausalueet ja kameraindeksi. Pelitila ja tapahtumaloki ovat muistissa; uudelleenkäynnistys aloittaa uuden pelin valmiustilassa.
- Viallinen asetustiedosto aiheuttaa lokimerkinnän ja turvallisten oletusten käytön. Poista tai nimeä `runtime/config.json` uudelleen oletusten palauttamiseksi.
- Portti varattu: sulje aiempi palvelin tai vaihda `ESCAPE_PORT`.
- Käsialamalli puuttuu tai on vioittunut: palauta `backend/assets/models/mnist-12.onnx` projektista ja käynnistä palvelin uudelleen. Mallin tarkiste ja lähde ovat `backend/assets/models/MODEL.md`-tiedostossa.
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

`backend/events.py` ja `backend/audio.py` muodostavat laajennusrajan. Audio Manager tilaa pelin tapahtumat ja valitsee tulevan äänitoiminnon tunnisteen. Musiikin toisto on toteutettu pelaajien selaimessa pelivaiheen mukaan. Vihjejärjestelmä ja automaatioeditori ovat tulevia laajennuksia. Musiikki, vaiheiden muutokset, ajastinrajat ja pelaajaviestit voidaan lisätä erillisiksi tapahtumien tilaajiksi.

Tekniset perustelut, tietovirta ja tiedostorakenne: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Fontin lisenssi: [backend/assets/FONT-LICENSE.txt](backend/assets/FONT-LICENSE.txt).


## Ajastimen tehosteet, lopetusvideot ja ihmisen tarkistus

- Viimeiset 5 minuuttia: lämmin korostus ja rauhallinen syke. Viimeiset 3 minuuttia: punainen ajastin ja tärinä. Viimeinen minuutti: millisekunnit päivittyvät paikallisesti palvelimen ajasta. Käyttöjärjestelmän vähennetyn liikkeen asetus poistaa tärinän ja sykeanimaation.
- **Diat, musiikki ja lopetusvideot** sisältää erilliset MP4/WebM-valinnat voitolle ja häviölle. Tallenna esitys ennen peliä. Pelin päättyessä näytetään ensin lopputulos ja voitossa jäljelle jäänyt aika. Valittu video käynnistyy vasta ohjauskeskuksen Seuraava näkymä -painikkeesta; video toistuu kerran ja sen ääni kuuluu ohjauskeskuksesta. Edellinen näkymä palauttaa tulokseen. Ilman videota näytetään voitto- tai häviönäkymä.
- Dian **Neljä pöytää ja animoidut paikat** -asettelu näyttää neljä pöytää ja kuusi paikkaa kunkin ympärillä. Pöydät ja paikat ilmestyvät porrastetusti.
- **Vaadi ihmisen tarkistus** estää automaattisen voiton myös kaikkien numeroiden ollessa oikein. Ohjaaja tarkistaa ratkaisun ja painaa **Hyväksy ratkaisu**, joka kysyy vahvistuksen. Kytkin säilyy seuraaviin peleihin. Hätähyväksyntä toimii myös ilman oikeaa kamerahavaintoa, mutta ei päättyneen aikarajan jälkeen.
- Valmiustilassa pelaajille näkyy vain musta tausta ja pieni harmaa odotusteksti.

Toisen dian **Koodi ja nuoli pöydälle** -asettelu näyttää neljä tyhjää numeropaikkaa ja animoidun alaspäin osoittavan nuolen. Dian otsikko on muokattavissa; oletusohje on Ratkaiskaa koodi.

## Peliasetukset, varmuuskopiointi ja lukitut ohjediat

Avaa ohjauskeskuksen sivupalkista **Peliasetukset**. Koodi ja peliaika tallentuvat **Tallenna peliasetukset** -painikkeesta; diojen ja median muutokset **Tallenna esitys** -painikkeesta. Näitä muokataan ennen peliä. Äänenvoimakkuus ja mykistys toimivat livesäätöinä kaikissa pelivaiheissa ja tallentuvat automaattisesti.

**Numeropaikkojen kuvakkeet** antaa valita jokaiseen neljään paikkaan erikseen matematiikan, golfin, auton, lapion tai **Ei kuvaketta**. Kellotaulujen oletusjärjestys on matematiikka (3), golf (5), auto (9) ja lapio (0). Valinnat tallentuvat peliasetusten mukana ja kulkevat ZIP-viennissä/-tuonnissa. Kuvakkeet ovat alusta asti pieniä symboleja numeropaikkojen yllä ja kasvavat numeronäkymässä valonauhan himmetessä. Kuvake pysyy valitussa paikassa koodin tai kamerahavaintojen muuttuessa. Palauta oletusjärjestys **Palauta kellotaulujen kuvakkeet** -painikkeesta; painike ei muuta oikeaa koodia.

**Vie asetukset ja mediat** lataa ZIP-paketin, joka sisältää myös esityksen käyttämät tiedostot. **Valitse asetuspaketti → Tuo asetukset** palauttaa paketin samalla tai toisella koneella. Tuonti korvaa asetukset ja palauttaa pelin valmiustilaan; se on käytettävissä ennen peliä. Paketin enimmäiskoko on 512 Mt ja yhden median 80 Mt. Tiedostot saavat tuonnissa uudet nimet, joten olemassa olevia medioita ei ylikirjoiteta.

Ensimmäinen dia toivottaa pelaajat tervetulleiksi tekstillä Tervetuloa pakohuoneeseen! Sen jälkeen pöytä- ja valonauhaohje muodostavat kiinteän dianparin. Pöydät siirtyvät samassa näkymässä valonauhan sisään. Tasaisen valon aikana poistuva hahmo pysähtyy ja näkyy punainen X; himmeästi välkkyvän valon aikana hahmo saa poistua ja näkyy vihreä hyväksyntä. Paria ei voi poistaa, vaihtaa keskenään tai muuttaa tavallisella dian muokkauksella. Seuraava koodidia näyttää neljä paikallaan pysyvää, voimakkaasti sumennettua numeroa: yksi niistä vaihtuu satunnaisin väliajoin.

Voittotilassa näytetään Huone ratkaistu -näkymä: pelin numerokortit ja jäljellä oleva aika siirtyvät pehmeästi lopputuloksen paikoille. Numerot napsahtavat vuorotellen paikalleen läpikuultavissa lasikorteissa kesken siirtymän. Numerot ja aika ovat aluksi oransseja ja vaihtuvat vihreiksi vasta koko sarjan lopussa. Näkyvissä ovat ratkaisuun kulunut peliaika, jäljellä oleva aika ja lopullinen koodi. Tauot eivät kuluta ratkaisuun laskettavaa aikaa. Lopetusvideo odottaa edelleen **Seuraava näkymä** -painallusta.

Pelaajien näytössä yksittäisen numeron oikeellisuutta ei näytetä väreillä, merkeillä tai teksteillä. Ennen voittoa pelaajien WebSocketin oikeellisuuslista on aina tyhjästä tiedosta muodostettu neljän epätoden lista. Ohjauskeskuksen tarkistustiedot säilyvät ohjaajalla. Vain koko koodin hyväksytty ratkaisu käynnistää vihreän voittoanimaation.

**Peliasetukset → Mekaaninen lopetusääni** tarjoaa selaimesta ladatut ja mediakansiosta löydetyt äänivaihtoehdot. Valitse yksi Käytä tätä ääntä -painikkeesta; mitään vaihtoehtoa ei oteta käyttöön automaattisesti. Valinta tallentuu heti myös pelin aikana. Äänetön on käytettävissä erikseen. Vaihtoehdot ja valinta sisältyvät asetuspaketin vientiin ja tuontiin. Esikuuntelu hiljentää taustamusiikkia tilapäisesti. Valitusta lopetusäänestä käytetään 180 ms klikkiä neljästi, täsmälleen numeroiden loksahtamisissa. Lopetusääni kuuluu vain ohjauskeskuksesta, sen äänenvoimakkuus noudattaa livesäätöä ja vanhaa lopputulosta avattaessa ääntä ei aloiteta uudestaan.

## Mediakansio ja numeroiden lyhyt muisti

Projektin `media/music/`, `media/videos/` ja `media/sound-effects/` toimivat paikallisena mediakirjastona. Asetukset hakevat tiedostot automaattisesti viiden sekunnin välein; valitse haluamasi tiedosto kansiovalikosta ja tallenna esitys. Äänitehoste valitaan Käytä tätä ääntä -painikkeesta. Katso tarkat ohjeet [media/README.md](media/README.md). Lähdekansion sijainnin voi vaihtaa `ESCAPE_LIBRARY`-ympäristömuuttujalla.

Kameran vahvistettu numero säilyy näkyvissä enintään kaksi sekuntia viimeisestä sitä tukevasta havainnosta. Käden lyhyt peitto tai yksittäinen väärä havainto ei tyhjennä ruutua. Uusi numero tarvitsee edelleen kolme samanlaista näytettä vähintään 0,65 sekunnin ajalta. Muistissa säilyvä numero ei voi yksin ratkaista peliä: voitto vaatii kaikkien neljän numeron tuoreen havainnon samasta kuvasta. Kameran pysäytys ja yli kaksi sekuntia vanha kuva tyhjentävät havainnot.
