import os
import urllib.request

FONTS = {
    "Roboto": "https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/Roboto-Regular.ttf",
    "OpenSans": "https://raw.githubusercontent.com/google/fonts/main/ofl/opensans/OpenSans%5Bwdth%2Cwght%5D.ttf",
    "Montserrat": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    "Oswald": "https://raw.githubusercontent.com/google/fonts/main/ofl/oswald/Oswald%5Bwght%5D.ttf",
    "Raleway": "https://raw.githubusercontent.com/google/fonts/main/ofl/raleway/Raleway%5Bwght%5D.ttf",
    "Merriweather": "https://raw.githubusercontent.com/google/fonts/main/ofl/merriweather/Merriweather-Regular.ttf",
    "PlayfairDisplay": "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
    "Lora": "https://raw.githubusercontent.com/google/fonts/main/ofl/lora/Lora%5Bwght%5D.ttf",
    "DancingScript": "https://raw.githubusercontent.com/google/fonts/main/ofl/dancingscript/DancingScript%5Bwght%5D.ttf",
    "Pacifico": "https://raw.githubusercontent.com/google/fonts/main/ofl/pacifico/Pacifico-Regular.ttf"
}

os.makedirs("fonts", exist_ok=True)

for name, url in FONTS.items():
    try:
        print(f"Downloading {name}...")
        urllib.request.urlretrieve(url, f"fonts/{name}.ttf")
    except Exception as e:
        print(f"Failed to download {name}: {e}")

print("Done downloading fonts.")
