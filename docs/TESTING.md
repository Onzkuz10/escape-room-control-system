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

## Windows-rajauksen tarkistus 2026-10-16

- Todellinen ongelma toistettiin: selaimen muokatut kehykset poikkesivat tallennetuista oletusalueista. Näkyvien kehysten tallennuksen jälkeen fyysisen kameran numerot 1, 2, 3, 4 tunnistuivat pistein 98,2 / 99,7 / 99,9 / 100 ja pelitila vaihtui ratkaistuksi.
- Korjauksen selaintesti ajettiin erillisellä portin 8001 palvelimella ja omalla konfiguraatiolla. Prosenttikenttien muutokset x=20 %, y=30 %, leveys=16 %, korkeus=30 % tallentuivat ilman painiketta. 40×20 pikselin veto vastasi backendillä tarkalleen siirtymää 40/pinnan leveys, 20/pinnan korkeus. 30×20 pikselin kahvaveto muutti valitun alueen leveyttä/korkeutta samalla muunnoksella, myös päällekkäisten alueiden tapauksessa. Tallennettu rajaus säilyi sivun päivityksessä.
- Pikselitestit tarkistavat rajauksen alku-/loppukoordinaatit 1280×720-, 1920×1080- ja 640×480-kuvilla sekä kuvan viimeisen pikselin mukaanoton.
- 94 pytest-testiä läpäisi; TypeScript/Vite-build onnistui. Starlette ilmoitti olemassa olevan anyio-deprekaatiovaroituksen.


## Pre-game, media ja pelinäkymät — 22.10.2026

- Windows: `npm run build --prefix frontend` läpäisty ja 98 pytest-testiä läpäisty. Uudet tarkistukset kattavat pre-gamen kuluttamattoman peliajan, diojen rajat, näkymien vaihdon, automaattisen ratkaisun portituksen numeronäkymään, pelaajan tilannekuvan oikeellisuustietojen piilottamisen ajastinnäkymässä, median latauksen ja validoinnin sekä esityksen tallentumisen ja uudelleenyhdistämisen.
- Paikallisessa selaimessa erillisellä portin 8011 testipalvelimella varmistettu: pre-game → seuraava dia → Start game → iso valkoinen ajastin → pienet neutraalit numerot → Seuraava näkymä → suuret numerot → automaattinen onnistuminen.
- Tiedostovalitsimesta ladattu WAV-testitiedosto molempiin musiikkivalintoihin sekä kuva diaan. WAV sisälsi vain hiljaisuutta eikä ole sovelluksen musiikkia. Tallentaminen ja sivun uudelleenlataus säilyttivät tiedostovalinnat.
- Selaimen audioelementistä varmistettu toiston käynnistyminen aktivoinnista, raidan vaihtuminen pelin alussa, tauotus ja jatkuminen. Käyttäjän omien lopullisten musiikki- ja videotiedostojen toisto tulee varmistaa käytettävällä pelaajien laitteella.
- Lopullinen ajastinnäkymä mahtui 1280 × 720 -ikkunaan ilman pysty- tai vaakavieritystä. Fyysistä kameraa tai kaiuttimien ääntä ei arvioitu tässä testissä.
- `tests/browser_smoke.py` päivitetty uuteen pre-game- ja numeronäkymän kulkuun. Tässä muutoksessa selaintarkistukset tehtiin selainohjaimella; koko erillistä smoke-skriptiä ei ajettu.

## Kameraluettelo ja edellinen näkymä — 25.10.2026

- Windows: 107 pytest-testiä läpäisty ja TypeScript/Vite-build onnistui. Testit kattavat kameraluettelon, Windowsin/MSMF:n ja macOS:n/AVFoundationin rajapintavalinnan, yli yhdeksän kameraindeksin tuen, irrotetun kameran hylkäyksen, haun virhetilan sekä edelliseen näkymään palaamisen ajastinta ja numeroita nollaamatta.
- Localhostin portissa 8000 varmistettu toimiva health-vastaus ja selaimessa automaattisesti löytyvä Camo-kamera nimellisessä valikossa. Luettelointi ei avaa kameraa. Fyysistä kamerakuvaa tai Mac-laitetta ei testattu; macOS:n rajapintavalinta tarkistettiin testikaksoisella.
- Päivitetty asennus tarvitsee `./scripts/setup.sh`-ajon Macilla ennen käynnistystä. Riippuvuuden macOS-asennus sisältää AVFoundationin Python-sidokset.

## Ohjauskeskus, loppunäkymät ja ohjaajan hyväksyntä — 25.10.2026

- Pelin käynnistys, tauotus, jatkaminen, näkymänvaihto ja nollaus ovat yhdessä ohjausrivissä. Kameran asetukset avataan tarvittaessa. Simulointipainike on poistettu.
- Pelaajien näytöltä poistettu ylä- ja alatunnisteet sekä ääniohjaimet. Valmiustilassa on musta tausta ja pieni harmaa odotusteksti. Äänentoisto on ohjauskeskuksessa; sen toiminta tarkistettiin selaimen audioelementin toistotilasta.
- Erillisen portin 8011 testipalvelimella tarkistettu 5 minuutin lämmin korostus, 3 minuutin punainen tärinä ja viimeisen minuutin päivittyvät millisekunnit. Pelaajien näkymä mahtui 1280 × 720 -ikkunaan.
- Testivideoilla tarkistettu sekä voitto- että häviövideon automaattinen käynnistys, toisto loppuun kerran, pelaajan videon mykistys ja äänen toisto ohjauskeskuksessa. Lopetusvideoiden tiedostovalinnat validoidaan ja tallennetaan esitysasetuksiin.
- Pöytäasettelussa tarkistettu neljä pöytää, 24 porrastetusti ilmestyvää paikkaa ja vierityksetön projektorinäkymä.
- Ihmisen tarkistusvaatimus estää automaattisen ratkaisun. Hätähyväksyntä kysyy vahvistuksen ja käynnistää voittovideon myös puuttuvilla kamerahavainnoilla. Aikarajan päättymisen jälkeen hyväksyntä hylätään. Kytkin säilyy nollauksen ja palvelimen uudelleenkäynnistyksen yli.
- 111 pytest-testiä läpäisty. TypeScript/Vite-build läpäisty. Selaintarkistukset tehtiin selainohjaimella; koko erillistä smoke-skriptiä ei ajettu.

## Koodidiojen grafiikka ja lopetusvideoiden erillinen käynnistys — 25.10.2026

- Numeropaikkojen tyhjät havainnot näytetään tyhjinä. Toisella alkudialla on neljä tyhjää koodipaikkaa ja alaspäin osoittava animoitu nuoli.
- Voitto ja häviö näyttävät ensin tuloksen; voitossa näkyy jäljellä oleva aika. Kumpikin lopetusvideo ja sen ääni käynnistyvät vasta ohjauskeskuksen Seuraava näkymä -painikkeesta. Edellinen näkymä pysäyttää videon ja palauttaa tuloksen. Tämä korvaa aiemman automaattisen käynnistyksen pelin päättyessä.
- 115 pytest-testiä läpäisty. Uudet testit kattavat molemmat lopputulokset, videon odotuksen, käynnistämisen ja peruuttamisen, puuttuvan videon, nollauksen, pelaajien uudelleenyhdistämisen ja koodidialografiikan tallennuksen. TypeScript/Vite-build läpäisty.

## Asetusnäkymä ja lopputulos — 25.10.2026

- Erillinen asetusnäkymä `/#settings`, tallennus, palautus ja mediat sisältävä ZIP-vienti/-tuonti. Tiedostojen nimet validoidaan, polkusiirtymät ja puuttuvat mediat hylätään; tuonti käyttää uusia medianimiä. Asetusten tallennusvirhe siivoaa uudet tiedostot ja jättää vanhat asetukset voimaan.
- Äänenvoimakkuuden livesäätö tarkistettu selaimessa ja palvelimen tallentamasta arvosta (27 %). Pelin vaihe, aika ja havainnot säilyvät ääniasetusmuutoksessa.
- Lukittu kaksiosainen ohjepari tarkistettu selaimessa: samojen pöytien siirtymä valonauhan sisälle, punainen pysähtymismerkki ja vihreä poistumislupa. Järjestyksen, animaation ja lukituksen poistamisen yritykset hylätään myös API:ssa.
- Koodidialografiikassa paikallaan pysyvät numerot vaihtuvat yksitellen satunnaisella viiveellä; sumennus 11 px. Varsinaisen pelin tyhjät numeropaikat pysyvät tyhjinä.
- Voiton numerorullat pysähtyvät 1,05 / 1,50 / 1,95 / 2,40 sekunnin kohdalla, vaihtuvat vihreäksi ja neljä pling-ääntä ajoitetaan samoihin kohtiin ohjauskeskuksen Web Audio -rajapinnassa. Selaimessa tarkistettu neljä oikeaa numeroa, kulunut aika ja videon puuttuminen ennen Seuraava näkymä -painallusta. Fyysisten kaiuttimien ääntä ei arvioitu.
- Kapea 390 px asetusnäkymä tarkistettu samasta sovelluksesta erillisessä testikehyksessä. Projektorikoon voitto- ja ohjenäkymät tarkistettu ilman ylimääräistä vieritystä.
- 124 pytest-testiä ja TypeScript/Vite-build läpäisty. Mukana myös UTF-8-tallennus ja vanhan Windows-koodauksen luku. Erillistä koko Playwright-smoke-skriptiä ei ajettu; se päivitettiin vastaamaan uutta kulkua.

## Osittaisten oikeellisuusvihjeiden poisto — 25.10.2026

- Pelaajien numeropaikat ovat aina neutraaleja ennen koko pelin ratkeamista: ei vihreää väriä, hyväksyntämerkkiä tai OIKEIN-tekstiä. Numeron tunnistuminen ei paljasta, kuuluuko se oikeaan ratkaisuun.
- Pelaajien WebSocket-tilannekuva peittää oikeellisuuden myös numero- ja taukonäkymässä sekä silloin, kun oikea koodi odottaa ihmisen hyväksyntää. Ohjauskeskuksen tarkistus ja koko koodin ratkaisulogiikka säilyvät.
- 136 pytest-testiä ja TypeScript/Vite-build läpäisty. Testit kattavat kaikki pelivaiheet ja molemmat näkymät, ihmisen hyväksyntää odottavan koodin sekä pelaajan WebSocketin.

## Hillitty lopputulos — 25.10.2026

- Voittotuloksen pling-äänet ja Web Audio -äänigeneraattori poistettu. Myös numerorullat, vihreät välähdykset, hehkut ja pitkä lisäteksti poistettu.
- Tuloksessa on tumma neutraali tausta, Huone ratkaistu -otsikko, ratkaisuun kulunut aika isona sekä jäljellä oleva aika ja lopullinen koodi pienempinä. Ainoa tulosnäkymän animaatio on rauhallinen koko näkymän häivytys.
- Lopetusvideo ja sen ääni odottavat edelleen Seuraava näkymä -painiketta. Pelaajien pelinaikaisiin neutraaleihin numeroihin ei lisätty oikeellisuusvihjeitä.
- TypeScript/Vite-build läpäisty. Backendin ratkaisulogiikkaa ei muutettu.

## Mekaaninen lopputulos ja valittava lopetusääni — 25.10.2026

- Lopputulos uusittu grafiitin ja teräksen sävyihin. Neljä numerokasettia lukittuu vuorotellen ja salpa vetäytyy; meripihkanvärinen merkkivalo on ainoa korostusväri. Pelinaikaiset numerot pysyvät neutraaleina.
- Asetuksissa on enintään neljän vaihtoehdon esikuuntelu ja erillinen äänen valinta. Mitään ääntä ei valita automaattisesti. Valinta ei muuta pelivaihetta, aikaa tai havaintoja, ja kaikki vaihtoehdot kulkevat mukana ZIP-paketissa.
- ElevenLabs-generointia ei ole vielä tehty: Chrome-kirjautuminen odottaa käyttäjää. Generointiraja on yksi; tästä syntyvät vaihtoehdot voidaan tuoda äänikirjastoon. Tyhjää kirjastoa ei täytetty korvaavilla äänillä.
- 140 pytest-testiä ja TypeScript/Vite-build läpäisty. Uudet testit kattavat valinnan, neljän vaihtoehdon rajan, kestovalidoinnin, tuonnin/viennin ja epäonnistuneen tallennuksen siivouksen. Mekaaninen lopputulos tarkistettu selaimessa.

## Lasipinnat, mekaaninen liike ja luodut äänet — 25.10.2026

- Teräskotelo, ruuvit ja näkyvä salpa korvattu sovelluksen ilmeeseen sopivilla läpikuultavilla lasikorteilla. Suuret numerot napsahtavat paikalleen yksi kerrallaan; oranssi vaihtuu vihreäksi vasta 3,3 sekunnin kohdalla. Liike kunnioittaa vähennetyn animaation asetusta.
- ElevenLabsissa tehtiin käyttäjän luvalla yksi generaatio, joka tuotti neljä 4 sekunnin WAV-vaihtoehtoa. Kaikki neljä tuotu paikallisiin peliasetuksiin. Ääntä ei valittu käyttäjän puolesta eikä toista generaatiota tehty.
- Selaimessa tarkistettu oranssi välivaihe, kaikkien neljän numeron lukittuminen ja vihreä lopputila erillisellä testipalvelimella muuttamatta nykyistä peliä. Tarkistettu 1280×720- ja 390×600-näkymät.
- Ensimmäisen äänen esikuuntelussa selaimen audioelementti toisti 4,0 sekunnin tiedostoa ilman virhettä. Fyysisten kaiuttimien äänenlaatua ei arvioitu. Äänenvalinta säilyi tyhjänä.
- TypeScript/Vite-build läpäisty. Backendin toimintalogiikkaan ei tehty muutoksia tässä ulkoasuviimeistelyssä; edellisen vaiheen 140 pytest-testiä olivat läpäisseet.

## Tervetulodia — 25.10.2026

- Ensimmäinen oletusdia ja paikallisen pelin ensimmäinen dia: Tervetuloa pakohuoneeseen! Pöytä- ja valonauhaohje säilyvät sen jälkeen peräkkäisinä. Validointi estää parin erottamisen, järjestyksen vaihdon ja animaation muuttamisen.
- 141 pytest-testiä läpäisty. Paikallisesta palvelimesta varmistettu uusi diajärjestys ja nykyisen lopputuloksen säilyminen.


## Loppuratkaisun morph ja numeroklikit — 25.10.2026

- Numerokorttien ja ajastimen jatkuva paikan- ja koonmuutos tarkistettu oikeasta pelinäkymästä lopputulokseen. Mitatut korttien paikat etenivät alkuperäisestä rivistä välivaiheen kautta loppuasetteluun. Ei erillistä tyhjää numerovaihetta. Oranssi vaihtuu vihreäksi koko sarjan lopussa.
- Käyttäjän pyynnöstä ensimmäinen ElevenLabs-vaihtoehto valittu paikalliseen peliin. Uutta generaatiota ei tehty. Ensimmäisestä iskusta valmistetun 180 ms näytteen testissä varmistettu kuuluva sisältö, 6 ms iskukohta, nollaan vaimennetut reunat ja tyhjän äänen hylkäys.
- Ohjauskeskuksen selaimessa kaikki neljä Web Audio -lähdettä päättyivät oikeassa järjestyksessä, noin 380 ms välein. Iskut sijoittuvat morphin sisään. Fyysisten kaiuttimien viivettä tai äänenlaatua ei arvioitu.
- 1280×720- ja 390×844-näkymät tarkistettu. Kapeassa näkymässä ei vaakavieritystä. Vähennettyä liikettä kunnioittava polku säilyy. TypeScript/Vite-build ja git diff --check läpäisty. Backendin toimintalogiikkaa ei muutettu.

## Hiljainen etsintämerkki ja ajastimen valonauha — 25.10.2026

- Ajastimen valonauha käyttää alkudiojen meripihkanväristä reunaa ja samaa hillittyä välkeanimaatiota. Seuraava näkymä sammuttaa nauhan 550 ms aikana; numeroiden suureneminen alkaa 650 ms jälkeen. Pelaajille ei lisätä etsintälupaa tai uutta ohjetekstiä.
- Erillisellä portin 8011 testipalvelimella ja omalla tilapäisellä asetustiedostolla varmistettu todellisessa Chrome-selaimessa API:n, backend-tilan ja WebSocketilla päivittyvän pelaajanäkymän koko kulku. Numerokortin leveys säilyi noin 70 px:ssä nauhan sammumiseen asti ja kasvoi vasta sen jälkeen noin 179 px:iin.
- Tauotus, paluu ajastimeen ja nauhan syttyminen, käsihyväksyntää odottava koodi 3590, voitto, nollaus ja uudelleenyhdistäminen tarkistettu. Vähennetyn liikkeen asetus poistaa välkkeen ja siirtymät. 1280×720- ja 390×844-näkymissä ei vaaka- tai pystyvieritystä. Selaimessa ei JavaScript-virheitä.
- TypeScript/Vite-build ja git diff --check läpäisty. Backendin pelilogiikkaa ei muutettu. Fyysisen valonauhan ja näytön yhteinen sammutus on harjoiteltava järjestäjien kanssa; sovellus ei ohjaa fyysistä nauhaa.

## Numeropaikkojen valittavat kuvakkeet — 25.10.2026

- Peliasetuksissa jokaiselle neljälle numeropaikalle oma valinta: matematiikka, golf, auto, lapio tai ei kuvaketta. Oletukset vastaavat kellotauluja 3–5–9–0. Kuvakkeet näkyvät alusta asti pieninä ja kasvavat numeroiden kanssa valonauhan sammumisen jälkeen.
- 151 pytest-testiä läpäisty. Uudet API-testit kattavat tallennuksen, pelaajan WebSocketin, paikkakohtaisuuden havaintojen ja koodin muuttuessa, nollauksen, vanhat asetukset, tyhjät valinnat, ZIP-viennin/-tuonnin, virheelliset arvot ja tallennusvirheen. Pelinaikainen asetusten muutos hylätään.
- Erillisellä portin 8012 testipalvelimella tarkistettu Chromessa oikeiden asetusvalintojen ja tallennuspainikkeen kautta kulkeva ketju API:in ja pelaajan WebSocket-näkymään. Tallentamattomat valinnat säilyivät tilapäivitysten yli. Tarkistettu yksittäinen tyhjä paikka, kaikki tyhjät, oletusten palautus, uudelleenlataus ja ratkaisun käsihyväksyntä.
- Pelaajanäkymät 1280×720, 1024×600 ja 390×844 sekä asetukset 390 px leveydessä tarkistettu. Ei vaakavieritystä, eikä pelaajanäkymässä pystyvieritystä. Kuvake oli alussa enintään 44×25 px ja kasvoi numeronäkymässä. Vähennetty liike poistaa siirtymät. Ei selainvirheitä. TypeScript/Vite-build läpäisty.


## Mediakansio ja lyhyen peiton sieto — 26.10.2026

- Musiikin, videoiden ja äänitehosteiden rekursiivinen löytäminen, Unicode-nimet, tiedoston päivitys ja poisto, vanhan selainlatauksen uudelleenkäyttö, WAV-kesto ja virheelliset tiedostot testattu. Kansiosta valittu ääni, musiikki ja video kulkevat ZIP-paketissa ilman alkuperäistä kansiota.
- Numeron kahden sekunnin muisti, peiton jälkeinen paluu ilman välähdystä, yksittäisen väärän havainnon sieto, uuden numeron vakautus ja muistin vanheneminen testattu. Muistissa olevasta oikeasta numerosta ei synny voittoa peiton aikana. Vanha kamerakuva tyhjentää näytön.
- 160 pytest-testiä läpäisty, yksi symbolisen linkin testi ohitettu Windowsin käyttöoikeuksien vuoksi. TypeScript/Vite-build läpäisty.

- Paikallinen palvelin käynnistetty uudella versiolla pelitilanne säilyttäen. Kaikki yhdeksän mediakansion tiedostoa löytyivät ilman virheitä ja niiden HTTP-osoitteet vastasivat 200. Aiemmin valitut musiikki ja lopetusääni säilyttivät URL-osoitteensa.
- Musiikin, voitto-/häviövideoiden, ensimmäisen dian videon ja äänenvalintojen React-palvelinrenderöinti tarkistettu oikealla mediakatalogilla. Neljä aiempaa ääntä eivät kahdentuneet. Interaktiivinen selaintarkistus jäi tekemättä, koska tämän istunnon selainohjaus ei käynnistynyt kahdella yrityksellä.

- Samanaikainen livesäätö ja kansiosta valittavan äänen skannaus testattu: äänen valinta ei palauta vanhaa äänenvoimakkuutta tai mykistystä.
