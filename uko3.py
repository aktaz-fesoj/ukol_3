from pyproj import Transformer      #Knihovna pyproj pro práci se souřadnicovými systémy                       
import math
import statistics
from geojson import Point, Feature, FeatureCollection
from geojson import load, dump

def otevri_data(adresy, kontejnery):
    """Načítá data ze dvou souborů formátu '.geojson'. Vrací z těchto data uložená pod klíčem 'features'.
        Parameters:
                    adresy (str): Cesta k souboru 1
                    kontejnery (str): Cesta k souboru 2
        Returns:
                    data_adresy: Data uložená pod klíčem 'features' v souboru 1
                    data_kontejnery: Data uložená pod klíčem 'features' v souboru 2
    """
    try:
        with open(adresy, encoding="utf-8") as adresy_f:            #Otevření souboru s adresami a načtení dat z něj
            adresy_gj = load(adresy_f)
        with open(kontejnery, encoding="utf-8") as kontejnery_f:    #Otevření souboru s kontejnery a načtení dat z něj
            kontejnery_gj = load(kontejnery_f)
        data_adresy = adresy_gj['features']
        data_kontejnery = kontejnery_gj['features']
        print(f"Detekováno {len(data_adresy)} adresních bodů.")
        print(f"Detekováno {len(data_kontejnery)} lokalit kontejnerů na tříděný odpad.")
        print("Program nyní kontroluje data a počítá výsledky.")
        return(data_adresy, data_kontejnery)
    except FileNotFoundError:
        print("Bohužel alespoň jeden ze vstupních souborů nebyl nalezen.") 
        print("Zkontrolujte, zda soubory mají názvy adresy.geojson a kontejnery.geojson a jsou uloženy ve stejné složce, ze které spouštíte tento program.")

def prevod_wgs2jtsk(x, y):
    """Souřadnice x a y v souřadnicovém systému WGS84 převede do souřadnicového systému s-jtsk a vrátí je jako tuple
        Parameters:
                    x (double): Zeměpisná délka
                    y (double): Zeměpisná šířka
        Returns:
                    out (tuple): Uspořádaná dvojice souřadnic ve formátu s-jtsk
    """
    if abs(y) > 90 or abs(x) > 180:
        print("Nevalidní souřadnice adresy. Jsou požadovány souřadnice v souřadnicovém systému WGS84. Běh programu byl ukončen, opravte data a zkuste to znovu.")
        quit()
    wgs2jtsk = Transformer.from_crs(4326, 5514, always_xy = True)       #Převedení souřadnic z WGS84 do s-jtsk pomocí nástroje Transformer z knihovny pyproj
    out = wgs2jtsk.transform(x, y)                                      #always xy je true, tzn. první zadávaný je souřadnice zeměpisné délky
    return(out)

def vzdalenost_bodu(x1,y1,x2,y2):
    """Počítá vzdálenost dvou bodů v pravoúhlé souřadnicové síti
        Parameters:
                    x1 (double): Souřadnice x prvního bodu
                    y1 (double): Souřadnice y prvního bodu
                    x2 (double): Souřadnice x druhého bodu
                    y2 (double): Souřadnice y druhého bodu
        Returns:
                    vzd (double): Vzdálenost těchto dvou bodů
    """
    delta_x = abs(x1-x2)                        #Rozdíl mezi zeměpisnými délkami v absolutní hodnotě
    delta_y = abs(y1-y2)                        #Rozdíl mezi zeměpisnými šířkami v absolutní hodnotě
    vzd = math.sqrt(delta_x**2 + delta_y**2)    #Pythagorova věta, výpočet vzdálenosti mezi dvěma body v pravoúhlé síti
    return(vzd)

def roztrid_kontejnery(data_kontejnery):
    """Roztřídí data o kontejnerech dle atributu PRISTUP
        Parameters:
                    data_kontejnery: Seznam kontejnerů
        Returns:
                    data_volne_kontejnery: Seznam volně přístupných kontejnerů
                    data_privatni_kontejnery: Seznam privátních kontejnerů (přístupných jen obyvatelům daného domu)
    """
    try:
        data_volne_kontejnery = []
        data_privatni_kontejnery = []
        for i in range (len(data_kontejnery)):                                      #Počet opakování dán počtem všech kontejnerů
            data_kontejner_i = data_kontejnery[i]                                   #Výběr i-tého kontejneru z dat
            if data_kontejner_i["properties"]["PRISTUP"] == "volně":                #Pokud je kontejner volně přístupný, bude přidán do seznamu volných kontejnerů
                data_volne_kontejnery.append(data_kontejner_i)
            elif data_kontejner_i["properties"]["PRISTUP"] == "obyvatelům domu":    #Pokud není kontejner volně přístupný, bude přidán do seznamu privátních kontejnerů
                data_privatni_kontejnery.append(data_kontejner_i)
        return(data_volne_kontejnery, data_privatni_kontejnery)
    except KeyError:
        print("Vstupní soubor kontejnerů neobsahuje ke každému kontejneru atribut PRISTUP. Program je ukončen, opravte prosím vstupní data.")
        quit()

def roztrid_adresy(features, data_adresy, data_privatni_kontejnery):
    """Roztřídí data o adresách dle toho, zda je na nich kontejner přístupný obyvatelům daného domu
        Parameters:
                    features: Seznam určený k vypsání do výstupního souboru formátu .geojson, ve kterém je ke každé adrese uloženo id nejbližšího kontejneru
                    data_adresy: Seznam adresních bodů
                    data_privatni_kontejnery: Seznam privátních kontejnerů
        Returns:
                    features: Seznam určený k vypsání do výstupního souboru formátu .geojson, ve kterém je ke každé adrese uloženo id nejbližšího kontejneru s přidanými prvky
                    data_adresy_s: Seznam adres s privátním kontejnerem
                    data_adresy_bez: Seznam adres bez privátního kontejneru
    """
    data_adresy_bez = []
    data_adresy_s = []
    for a in range (len(data_adresy)):              #Počet opakování dán počtem všech adres
        data_adresa_a = data_adresy[a]              #Výběr a-tého kontejneru z dat
        shoda = False                               #Při každém opakování začíná shoda na hodnotě False
        try:
            adresa_dohromady = f"{data_adresa_a['properties']['addr:street']} {data_adresa_a['properties']['addr:housenumber']}"    #Spojení ulice a čísla domu do jednoho textového řetězce, aby byl porovnatelný s adresou uvedenou v datech kontejneru
        except KeyError:
            print("Vstupní soubor s adresami neobsahuje u každé adresy v properties atribut addr:street, nebo atribut addr:housenumber. Program je ukončen, přečtěte si prosím dokumentaci, opravte vstupní data a zkuste to znovu.")
            quit()
        for e in range(len(data_privatni_kontejnery)):
            data_kontejner_e = data_privatni_kontejnery[e]
            if data_kontejner_e["properties"]["STATIONNAME"] == adresa_dohromady:       #Porovnání adresy s adresou privátního kontejneru
                data_adresy_s.append(data_adresa_a)                                     #Shodují-li se adresy, je adresa přidána do seznamu adres obsloužených privátním kontejnerem
                features = priprav_do_geojsonu(features, *prevod_wgs2jtsk(*data_adresa_a["geometry"]["coordinates"]), data_adresa_a['properties']['addr:street'], data_adresa_a['properties']['addr:housenumber'], data_kontejner_e["properties"]["ID"]) #Uložení do seznamu k vypsání do nového geojson souboru s informacemi o adrese a id nejbližšího kontejneru, souřadnice jsou převedeny do s-jtsk, aby byly ve výsledném geojsonu jednotné
                shoda = True    #Pokud se mezi kontejnery najde kontejner se stejnou adresou, je proměnná shoda změněna na True
        if shoda == False:      #Pokud kontejner se stejnou adresou nalezen není, shoda zůstává False -> adresa je přidána do seznamu adres bez privátního kontejneru
            data_adresy_bez.append(data_adresa_a)
    return(features, data_adresy_s, data_adresy_bez)

features = []
def priprav_do_geojsonu(features, sour_x, sour_y, adresa_prozapis_ulice, adresa_prozapis_cislo, kontejner_id):
    """Připraví vložená data pro zápis do výstupního .geojson souboru
        Parameters:
                    features: Seznam určený k vypsání do výstupního souboru formátu .geojson, ve kterém je ke každé adrese uloženo id nejbližšího kontejneru
                    sour_x: Souřadnice x vkládaného bodu
                    sour_y: Souřadnice y vkládaného bodu
                    adresa_prozapis_ulice: Hodnota klíče "addr:street" v properties výstupního geojson souboru
                    adresa_prozapis_cislo: Hodnota klíče "addr:housenumber" v properties výstupního geojson souboru
                    kontejner_id: Hodnota klíče "kontejner" v properties výstupního geojson souboru
        Returns:
                    features: Seznam určený k vypsání do výstupního souboru formátu .geojson, ve kterém je ke každé adrese uloženo id nejbližšího kontejneru s přidanými prvky
    """
    point = Point((sour_x, sour_y))
    features.append(Feature(geometry=point, properties={"addr:street": f"{adresa_prozapis_ulice}", "addr:housenumber": f"{adresa_prozapis_cislo}", "kontejner": f"{kontejner_id}"})) #Přidání adresního místa s ID do seznamu features
    return(features)

def vypis_geojson(features):
    """Zapíše data do souboru adresy_kontejnery.geojson
        Parameters:
                    features: Seznam určený k vypsání do výstupního souboru formátu .geojson, ve kterém je ke každé adrese uloženo id nejbližšího kontejneru
    """
    feature_collection = FeatureCollection(features)
    with open('adresy_kontejnery.geojson', 'w', encoding="utf-8") as f:
        dump(feature_collection, f, ensure_ascii=False, indent=4) #Bez parametru ensure_ascii nastaveného na False docházelo k nesprávnému zápisu některých znaků, parametrt indent vylepšuje čitelnost výsledného souboru, zajišťuje vhodné odřádkovávání
    print("Informace o nejbližším kontejneru ke každě adrese je uložena v nově vytvořeném souboru 'adresy_kontejnery.geojson'.")

data_adresy, data_kontejnery = otevri_data("adresy.geojson", "kontejnery.geojson")
data_volne_kontejnery, data_privatni_kontejnery = roztrid_kontejnery(data_kontejnery)
features, data_adresy_s, data_adresy_bez = roztrid_adresy(features, data_adresy, data_privatni_kontejnery)

pocet_adres_s = len(data_adresy_s)
pocet_adres_bez = len(data_adresy_bez)
pocet_volnych_kontejneru =  len(data_volne_kontejnery)
pocet_privatnich_kontejneru =  len(data_privatni_kontejnery)

seznam_minimalnich = []
soucet_minimalnich = 0
maximalni_z_minimalnich = 0

for i in range(pocet_adres_bez):        #Počet opakování dán počtem adres bez privátního kontejneru
    try:
        adresa = data_adresy_bez[i]         #Výběr i-té adresy z dat
        nove_sour = prevod_wgs2jtsk(*adresa["geometry"]["coordinates"]) #Převedení souřadnic do s-jtsk
        adresa["geometry"]["coordinates"] = nove_sour   #Nahrazení předchozích souřadnic novými
        vzd = 0
        minimalni = 0
    except TypeError:
        print("Vstupní soubor adres neobsahuje správné souřadnice. Program je ukončen, opravte prosím vstupní data.")
        quit()
    #Následující cyklus počítá vzdálenost adresy a každého z veřejných kontejnerů, přičemž nejnižší ze vzdáleností uloží do proměnné minimalni
    for u in range(pocet_volnych_kontejneru):      #Počet opakování dán počtem volně přístupných kontejneru
        kontejner = data_volne_kontejnery[u]       #Výběr u-tého kontejneru z dat
        try:
            vzd = vzdalenost_bodu(*adresa["geometry"]["coordinates"], *kontejner["geometry"]["coordinates"])        #Výpočet vzdálenosti
        except TypeError:
            print("Vstupní soubor kontejnerů neobsahuje správné souřadnice. Program je ukončen, opravte prosím vstupní data.")
            quit()
        if u == 0 or vzd < minimalni:   #Zápis minimální vzdálenosti při prvním opakování a vždy při "překonání" této vzdálenosti
            minimalni = vzd
        try:
            minimalni_info = {"ulice_min":adresa["properties"]["addr:street"], "cislo_min":adresa["properties"]["addr:housenumber"], "kontejner_min":kontejner["properties"]["ID"]} #Uložení informací o minimální vzdálenosti a id kontejneru k němuž se tato vzdálenost vztahuje
        except KeyError:
            print("Vstupní soubory neobsahují některý s požadovaných atributů. Program je ukončen, přečtěte si prosím dokumentaci, opravte vstupní data a zkuste to znovu.")
            quit()

    if minimalni > maximalni_z_minimalnich: #Hledání nejvyšší z nejmenších vzdáleností
        maximalni_z_minimalnich = minimalni
        if maximalni_z_minimalnich > 10000: # Je-li nejvyšší z nejmenších vzdáleností vyšší než 10000 metrů, program skončí s chybovou hláškou
            print(f"Pravděpodobná chyba ve vstupních datech! Existuje adresní místo se vzdáleností více než 10 km (konkrétně {maximalni_z_minimalnich} m) k nejbližšímu kontejneru.")
            print("Běh programu je z tohoto důvodu ukončen. Zkontrolujte prosím vstupní data.")
            exit()
        maximalni_info = {"ulice_max":adresa["properties"]["addr:street"], "cislo_max":adresa["properties"]["addr:housenumber"], "hodnota_max": round(maximalni_z_minimalnich)} #Uložení informací o nejvyšší z nejnižších vzdáleností, aby mohly být následně vypsány
    features = priprav_do_geojsonu(features, adresa["geometry"]["coordinates"][0], adresa["geometry"]["coordinates"][1], minimalni_info["ulice_min"], minimalni_info["cislo_min"], minimalni_info["kontejner_min"]) #Uložení do seznamu k vypsání do nového geojson souboru s informacemi o adrese a id nejbližšího kontejneru
    seznam_minimalnich.append(minimalni)    #Přidání minimální vzdálenosti ke kontejneru pro danou adresu do seznamu takových vzdáleností
    soucet_minimalnich += minimalni         #Přištění této vzdálenosti k předchozím takovýmto vzdálenostem

for i in range(pocet_adres_s):      #Do seznamu přidám vzdálenosti 0 za každou adresu s privátním kontejnerem, především kvůli následnému výpočtu mediánu
    seznam_minimalnich.append(0)

print(f"Celkem {pocet_adres_bez} adres bez domácího kontejneru.")
print(f"Celkem {pocet_adres_s} adres s domácím kontejnerem.")
print(f"Celkem {pocet_volnych_kontejneru} volně přístupných kontejnerů.")
print(f"Celkem {pocet_privatnich_kontejneru} kontejnerů přístupných pouze obyvatelům domu.")

med = round(statistics.median(seznam_minimalnich))      #Výpočet a zaokrouhlení mediánu na celé metry
print(f"Průměrná vzdálenost ke kontejneru je: {round(soucet_minimalnich/len(data_adresy))} m.") #Výpočet a zaokrouhlení průměru na celé metry. Dělím celkovým počtem adres, tedy beru v potaz i adresy s privátním kontejnerem (vzdálenost k němu je 0, není potřeba ji přičítat do součtu minimalních)
print(f"Medián vzdáleností ke kontejneru je: {med} m.")
print(f"Největší vzdálenost ke kontejneru je z adresy {maximalni_info['ulice_max']} {maximalni_info['cislo_max']} a to {maximalni_info['hodnota_max']} m.")

vypis_geojson(features) #Funkce vytvoří nový soubor a zapíše do něj informace o id nejbližšího kontejneru ke každé adrese