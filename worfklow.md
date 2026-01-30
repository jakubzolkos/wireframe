Motywacja
- inzynierowie elektryczni spedzaja bardzo duzo czasu implementujac przykladowe schematy obecne w PDFach

uzytkownik ma liste opisow PDF
Klika przycisk zeby wgrac kolejny
Laduje sie nowy widok (ekran ladowania)
Parser probuje znalezc przykladowe schematy w PDF'ie (ekran z paskiem ladowania)
Jak znajdzie to pokazuje wyekstrahowane zdjecia w kolumnie po lewej a po prawej jest datasheet ktory ma wskaznik gdzie dokladnie jest referencja
Uzytkownik moze kliknac na inny schemat aby przewinac datasheet do miejca gdzie jest ten schemat
Schematy maja dodatkowe opisy ktore LLM wydedukuje na podstawie datasheetu ktore opisuja czym ten schemat jest
W tym kroku system sprobuje pobrac symbol IC lub poprosi o wgranie go przez uzytkownika

Uzytkownik wtedy moze wybrac ktory schemat chce zaimplementowac i klika Continue
Wtedy pokazuje sie edytor EDA a AI rozpocznie ekstrakcje topologi schematu i projekt wokol wgranego symbolu IC
