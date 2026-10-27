# Sovelluksen mediat

Lisää tiedostot suoraan näihin kansioihin. Myös omat alikansiot toimivat.

- `music/`: odotus- ja pelimusiikki sekä voiton äänimaisema (MP3, WAV, OGG, M4A).
- `videos/`: alkuvideot, lopetusvideot ja diojen videot (MP4, WebM).
- `sound-effects/`: lopetusäänen vaihtoehdot (MP3, WAV, OGG, M4A).

Avaa **Peliasetukset**. Sovellus lukee kansion automaattisesti käynnistyksessä ja päivittää asetusten tiedostolistan viiden sekunnin välein. Uusia tiedostoja ei tarvitse ladata selaimella eikä palvelinta tarvitse käynnistää uudelleen. Musiikin ja videoiden kohdalla valitse **Valitse mediakansiosta**, sitten **Tallenna esitys**. Äänitehosteen **Käytä tätä ääntä** tallentuu heti. Alkuvideon voi valita ensimmäisen dian videoksi.

Valinta on aina käyttäjän päätettävissä: tiedoston lisääminen ei vaihda kesken pelin soivaa musiikkia tai käynnistä videota. Nykyiset valinnat säilyvät.

Yksi tiedosto voi olla enintään 80 Mt. Siirrä tiedosto kokonaan ennen kuin valitset sen. Tiedostot kopioidaan automaattisesti `runtime/media/`-välimuistiin, joten nykyinen valinta toimii myös lähdetiedoston poistamisen jälkeen. Muokattu tiedosto saa uuden valinnan; valitse se uudelleen ottaaksesi uuden version käyttöön. ZIP-vienti sisältää tallennetun esityksen käyttämät tiedostot.

Valmiiksi valitut musiikit, äänitehosteet ja videot ovat projektin mukana Gitissä. Muut itse lisäämäsi tiedostot jäävät paikallisiksi; siirrä ne toiselle koneelle kopioimalla tämä kansio tai viemällä asetukset ja mediat ZIP-pakettina.
