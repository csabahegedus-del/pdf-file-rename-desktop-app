# PDF Számla Átnevező – Desktop App (Windows 11)

Natív (nem szkennelt) PDF közüzemi számlák automatikus átnevezője.  
A program az `input` mappában lévő PDF-eket beolvassa, tartalmuk alapján azonosítja a szolgáltatót,
kinyeri a számlaszámot, időszakot és típust, majd egységes névformátumra nevezi át a fájlokat.

## Támogatott szolgáltatók

| Szolgáltató | Típus |
|---|---|
| E.ON Dél-Dunántúli Áramhálózati Zrt. | Villamos energia |
| ELMŰ Hálózati Kft. | Villamos energia |
| E2 Hungary Zrt. | Földgáz |
| MVM Next Energiakereskedelmi Zrt. | Földgáz |
| DMRV Zrt. | Víziközmű |
| ÉDV Zrt. | Víziközmű |
| Fővárosi Vízművek Zrt. | Víziközmű |
| Heves Megyei Vízmű Zrt. | Víziközmű |
| TETTYE FORRÁSHÁZ Zrt. | Víziközmű |

## Telepítés

### Előfeltételek
- Python 3.11 vagy újabb (https://www.python.org/downloads/)
- A `python` parancs legyen elérhető a PATH-ban (telepítéskor pipáld be az *Add Python to PATH* lehetőséget)

### Függőségek telepítése
```cmd
pip install -r requirements.txt
```

## Használat

### 1. PDF fájlok előkészítése
Másold az átnevezendő PDF számlákat az `input` mappába.

### 2. Előnézet futtatása
Dupla kattintás a **`preview.bat`** fájlra:
- Beolvassa és elemzi az `input` mappában lévő PDF-eket
- **Nem módosítja** az eredeti fájlokat
- Egy Excel összesítőt ment a `preview` mappába (eredeti és javasolt új nevek)

### 3. Átnevezés futtatása
Dupla kattintás a **`run.bat`** fájlra:
- Az előnézettel megegyező elemzést végez
- Az átnevezett fájlokat az `output` mappába másolja
- Excel összesítőt ment a `preview` mappába

### 4. Naplók
A program naplófájlokat ment a `log` mappába minden futás alkalmával.

## Mappaszerkezet

```
pdf-file-rename-desktop-app/
├── input/          ← ide kerülnek a bemeneti PDF-ek
├── output/         ← ide kerülnek az átnevezett PDF-ek (run.bat után)
├── preview/        ← Excel összesítő fájlok
├── log/            ← naplófájlok
├── src/            ← program forráskód
├── config.json     ← felhasználói beállítások (leképezések)
├── preview.bat     ← előnézet indítása
├── run.bat         ← átnevezés indítása
└── requirements.txt
```

## Konfiguráció (`config.json`)

A `config.json` fájlban testre szabható:
- **ELMŰ**: Mérési pont azonosító utolsó 4 számjegye → cégnév
- **Fővárosi Vízművek**: Cím kulcsszó → cégnév
- **Heves Megyei Vízmű**: Cím kulcsszó → cégnév
- **DMRV**: Számlaszám → egyedi megjegyzés (pl. "Godollo, viz")
- **E.ON**: Város neve

### Példa `config.json` bejegyzés (ELMŰ):
```json
"elmu": {
    "measurement_point_company_map": {
        "9487": "Kumi Futár",
        "1234": "Másik Cég"
    }
}
```

## Kimeneti fájlnév formátumok

| Szolgáltató | Példa |
|---|---|
| E.ON Dél-Dunántúli | `E.ON Dél-Dunántúli (Pécs)_130645352952 (2026.01.01-2026.01.31) elszamolo.pdf` |
| ELMŰ | `ELMU_160000323609 (2025.12.01-2025.12.31) áram elszamolo (9487) Kumi Futár.pdf` |
| E2 Hungary | `E2_562003254374 (2025.12) gáz elszámoló.pdf` |
| MVM Next | `MVM_101316409301 gáz (2024.02.29.-2025.03.04) H épület_elszámoló (2025.02.hó).pdf` |
| DMRV | `DMRV_4010718333 (2025.03.16-2025.04.15) rész4.pdf` |
| ÉDV | `EDV_3016624394 (2026.01.06-2026.02.06) Dunaharaszti, viz.pdf` |
| Fővárosi Vízművek | `Fovarosi Vizmuvek_104000804901 (2026.01.06-2026.02.05) 4.rész Delta, viz.pdf` |
| Heves Megyei Vízmű | `Heves Megyei Vizmu_2026-00-10019011 (2026.01.11 - 2026.02.10) Bosch (2026.01.havi).pdf` |
| TETTYE | `Tettye_8364VK26 (2026.05.01-2026.06.30) reszszamla [viz].pdf` |

