# database/medicine.py
"""
Expanded medicine database (v3) built from uploaded CIB&RC / PPQS files.

Improvements over v2:
- larger coverage for the same 5 core crops
- more combination products from chemical/insecticide PDFs
- more pest/disease variants for tomato, rice, cotton, potato, wheat
- still curated for project use, not a verbatim full dump

Use lowercase lookup keys. Add aliases in your bot layer.
"""


# ─────────────────────────────────────────────────────────────────────────────
# DISEASE ALIAS MAP
# Maps AI-output variants / scientific names → canonical MEDICINE_DB keys.
# Usage: canonical = DISEASE_ALIASES.get(raw.lower().strip(), raw.lower().strip())
# ─────────────────────────────────────────────────────────────────────────────
DISEASE_ALIASES = {
    # ── Fungal – Blight ──
    "alternaria":                       "early blight",
    "alternaria solani":                "early blight",
    "leaf spot early blight":           "early blight",
    "tomato early blight":              "early blight",
    "potato early blight":              "early blight",
    "target spot":                      "early blight",
    "phytophthora":                     "late blight",
    "phytophthora infestans":           "late blight",
    "tomato late blight":               "late blight",
    "potato late blight":               "late blight",
    "phytophthora blight":              "late blight",
    # ── Anthracnose ──
    "colletotrichum":                   "anthracnose",
    "colletotrichum gloeosporioides":   "anthracnose",
    "fruit rot anthracnose":            "anthracnose",
    "die back":                         "anthracnose",
    "dieback":                          "anthracnose",
    # ── Leaf Spot ──
    "septoria":                         "septoria leaf spot",
    "septoria leaf spot disease":       "septoria leaf spot",
    "cercospora":                       "leaf spot",
    "cercospora leaf spot":             "leaf spot",
    "leaf blight":                      "leaf spot",
    "leafspot":                         "leaf spot",
    # ── Powdery Mildew ──
    "white powdery growth":             "powdery mildew",
    "powdery mildew disease":           "powdery mildew",
    "erysiphe":                         "powdery mildew",
    "oidium":                           "powdery mildew",
    # ── Rice Blast ──
    "neck blast":                       "blast",
    "leaf blast":                       "blast",
    "rice blast":                       "blast",
    "pyricularia oryzae":               "blast",
    "pyricularia":                      "blast",
    # ── Sheath Blight ──
    "rhizoctonia blight":               "sheath blight",
    "rhizoctonia solani":               "sheath blight",
    "sheath rot":                       "sheath blight",
    "rice sheath blight":               "sheath blight",
    # ── Brown Spot ──
    "helminthosporium":                 "brown leaf spot",
    "brown spot":                       "brown leaf spot",
    "rice brown spot":                  "brown leaf spot",
    "helminthosporium oryzae":          "brown leaf spot",
    # ── Bacterial Blight ──
    "blb":                              "bacterial leaf blight",
    "bacterial blight":                 "bacterial leaf blight",
    "xanthomonas":                      "bacterial leaf blight",
    "xanthomonas oryzae":               "bacterial leaf blight",
    # ── Wilt ──
    "fusarium":                         "fusarium wilt",
    "fusarium oxysporum":               "fusarium wilt",
    "soil borne wilt":                  "fusarium wilt",
    "soil-borne wilt":                  "fusarium wilt",
    "ralstonia":                        "bacterial wilt",
    "ralstonia solanacearum":           "bacterial wilt",
    "bacterial stem wilt":              "bacterial wilt",
    # ── Damping Off ──
    "pythium":                          "damping off",
    "seedling wilt":                    "damping off",
    "collar rot":                       "damping off",
    "seedling damping off":             "damping off",
    # ── Rust / Smut ──
    "yellow rust":                      "rust",
    "brown rust":                       "rust",
    "leaf rust":                        "rust",
    "stripe rust":                      "rust",
    "wheat rust":                       "rust",
    "puccinia":                         "rust",
    "wheat loose smut":                 "loose smut",
    "ustilago":                         "loose smut",
    # ── Downy Mildew ──
    "peronospora":                      "downy mildew",
    "plasmopara":                       "downy mildew",
    "peronosclerospora":                "downy mildew",
    "onion downy mildew":               "downy mildew",
    "maize downy mildew":               "downy mildew",
    # ── Maize Blight ──
    "northern leaf blight":             "turcicum leaf blight",
    "turcicum blight":                  "turcicum leaf blight",
    "helminthosporium turcicum":        "turcicum leaf blight",
    "nlb":                              "turcicum leaf blight",
    # ── Onion ──
    "alternaria porri":                 "purple blotch",
    "onion purple blotch":              "purple blotch",
    # ── Whitefly (canonical = "whitefly") ──
    "white fly":                        "whitefly",
    "whiteflies":                       "whitefly",
    "bemisia":                          "whitefly",
    "bemisia tabaci":                   "whitefly",
    "cotton whitefly":                  "whitefly",
    "tomato whitefly":                  "whitefly",
    "potato whitefly":                  "whitefly",
    # ── Mites (canonical = "mites") ──
    "red spider mite":                  "mites",
    "red spider mites":                 "mites",
    "spider mite":                      "mites",
    "spider mites":                     "mites",
    "two spotted mite":                 "mites",
    "tetranychid mite":                 "mites",
    "tetranychus":                      "mites",
    "cotton mite":                      "mites",
    # ── Aphids ──
    "aphid":                            "aphids",
    "cotton aphids":                    "aphids",
    "tomato aphid":                     "aphids",
    "potato aphid":                     "aphids",
    # ── Thrips ──
    "thrip":                            "thrips",
    "onion thrips":                     "thrips",
    "cotton thrips":                    "thrips",
    # ── Bollworms ──
    "bollworm":                         "bollworms",
    "american bollworm":                "bollworms",
    "spotted bollworm":                 "bollworms",
    "helicoverpa":                      "bollworms",
    "helicoverpa armigera":             "bollworms",
    "cotton bollworms":                 "bollworms",
    "tobacco caterpillar":              "bollworms",
    "spodoptera litura":                "bollworms",
    # ── Stem Borer ──
    "yellow stem borer":                "stem borer",
    "rice stem borer":                  "stem borer",
    "chilo partellus":                  "stem borer",
    "maize stem borer":                 "stem borer",
    "spotted stem borer":               "stem borer",
    # ── Leaf Folder ──
    "leaf roller":                      "leaf folder",
    "rice leaf folder":                 "leaf folder",
    # ── Hoppers ──
    "bph":                              "brown plant hopper",
    "rice brown plant hopper":          "brown plant hopper",
    "wbph":                             "white backed plant hopper",
    "white-backed plant hopper":        "white backed plant hopper",
    "glh":                              "green leafhopper",
    "green leaf hopper":                "green leafhopper",
    "rice green leafhopper":            "green leafhopper",
    "leafhopper":                       "leafhoppers",
    "leaf hopper":                      "leafhoppers",
    "jassid":                           "jassids",
    # ── Leaf Miner ──
    "leaf miner attack":                "leaf miner",
    "tomato leaf miner":                "leaf miner",
    "liriomyza":                        "leaf miner",
    # ── Fruit Borer ──
    "tomato fruit borer":               "fruit borer",
    "shoot and fruit borer":            "fruit borer",
    # ── Fall Armyworm ──
    "faw":                              "fall armyworm",
    "spodoptera frugiperda":            "fall armyworm",
    "maize armyworm":                   "fall armyworm",
    # ── Weeds ──
    "broadleaf weeds":                  "weed control",
    "grassy weeds":                     "weed control",
    "onion weeds":                      "weed control",
    "broadleaf and grassy weeds":       "weed control",
}


def normalize_disease(raw_disease: str) -> str:
    """Normalise AI-output disease name → canonical MEDICINE_DB key."""
    cleaned = raw_disease.lower().strip()
    for prefix in ("disease:", "pest:", "issue:", "problem:"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    return DISEASE_ALIASES.get(cleaned, cleaned)


MEDICINE_DB = {
    "tomato": {
        "early blight": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Azoxystrobin", "formulation": "23% SC", "dosage": "125 gm a.i. / 500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Captan", "formulation": "50% WP", "dosage": "750 gm a.i. / 1500 gm formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Picarbutrazox", "formulation": "9.53% w/w SC", "dosage": "100–125 gm a.i. / 1000–1250 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Iprovalicarb + Propineb", "formulation": "5.5% + 61.25% WP", "dosage": "2.25–2.5 kg formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Chlorothalonil", "formulation": "4.8% w/w + 40% w/w SC", "dosage": "3 ml formulation (as listed in source)", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Boscalid", "formulation": "25% + 35% WG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Tetraconazole", "formulation": "3.8% w/w EW", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Thifluzamide", "formulation": "24% SC", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Mancozeb", "formulation": "11.5% + 30% WP", "dosage": "750–875 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Pseudomonas fluorescens", "formulation": "1.75% WP", "dosage": "Seed treatment: 5 g/kg seed; Foliar spray: 3 kg/ha (6 g/litre water)", "water_dilution": "500 litres", "waiting_period": "-", "source": "CIBRC Bio-pesticides 30.09.2025"},
                {"active_ingredient": "Bacillus subtilis", "formulation": "1.50% L.F", "dosage": "Seed treatment: 10 ml/kg seed; Foliar spray: 3.0 litre/ha", "water_dilution": "500 litres", "waiting_period": "-", "source": "CIBRC Bio-pesticides 30.09.2025"},
            ],
        },
        "late blight": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Azoxystrobin", "formulation": "23% SC", "dosage": "125 gm a.i. / 500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Picarbutrazox", "formulation": "9.53% w/w SC", "dosage": "100–125 gm a.i. / 1000–1250 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Iprovalicarb + Propineb", "formulation": "5.5% + 61.25% WP", "dosage": "2.25–2.5 kg formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Chlorothalonil", "formulation": "4.8% w/w + 40% w/w SC", "dosage": "3 ml formulation (as listed in source)", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Mancozeb", "formulation": "11.5% + 30% WP", "dosage": "750–875 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Mancozeb", "formulation": "8.3% + 66.7% WG", "dosage": "1500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "septoria leaf spot": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Azoxystrobin + Boscalid", "formulation": "25% + 35% WG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Chlorothalonil", "formulation": "4.8% w/w + 40% w/w SC", "dosage": "3 ml formulation (as listed in source)", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
            ],
        },
        "leaf spot": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "fruit rot": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Pyraclostrobin + Fipronil", "formulation": "10% + 5% SC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Insecticide/Chemical Combination 03.10.2025"},
            ],
        },
        "anthracnose": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Tetraconazole", "formulation": "3.8% w/w EW", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Fungicides 30.09.2025"},
            ],
        },
        "ring rot": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Thiophanate Methyl", "formulation": "70% WP", "dosage": "715 gm formulation per hectare", "water_dilution": "750–1000 litres", "waiting_period": "7 days", "source": "CIBRC Fungicides 30.09.2025"},
            ],
        },
        "powdery mildew": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Azoxystrobin + Chlorothalonil", "formulation": "4.8% w/w + 40% w/w SC", "dosage": "3 ml formulation (as listed in source)", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
            ],
        },
        "damping off": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Captan", "formulation": "75% WS", "dosage": "20–30 g per kg seed (soil drench/seed treatment as listed)", "water_dilution": "1 litre reference in source", "waiting_period": "1 day", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "mites": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Abamectin", "formulation": "1.90% EC", "dosage": "450–600 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "leaf miner": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Abamectin", "formulation": "1.90% EC", "dosage": "450–600 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Broflanilide", "formulation": "300 g/l SC", "dosage": "62–84 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "1 day", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Broflanilide", "formulation": "20% SC", "dosage": "125 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "1 day", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "fruit borer": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Broflanilide", "formulation": "300 g/l SC", "dosage": "62–84 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "1 day", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "1.00% EC (10000 PPM)", "dosage": "1000–1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Bacillus thuringiensis var. galleriae", "formulation": "1.3% flowable concentrate", "dosage": "1.0–1.5 litre formulation per hectare", "water_dilution": "500 litres", "waiting_period": "-", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Nuclear Polyhedrosis Virus of Helicoverpa armigera", "formulation": "0.43% AS", "dosage": "1500 ml formulation per hectare", "water_dilution": "400–600 litres", "waiting_period": "-", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Lufenuron", "formulation": "16.9% + 16.9% SC", "dosage": "150 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Thiamethoxam-based combination", "formulation": "as listed in source", "dosage": "125 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pyraclostrobin + Fipronil", "formulation": "10% + 5% SC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Insecticide/Chemical Combination 03.10.2025"},
            ],
        },
        "thrips": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Broflanilide", "formulation": "20% SC", "dosage": "125 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "1 day", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Thiamethoxam-based combination", "formulation": "as listed in source", "dosage": "125 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "whitefly": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Spiromesifen", "formulation": "22.90% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "200 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Propargite + Bifenthrin", "formulation": "50% + 5% SE", "dosage": "1100–1150 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "mites": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Spiromesifen", "formulation": "22.90% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Propargite + Bifenthrin", "formulation": "50% + 5% SE", "dosage": "1100–1150 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "aphids": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "200 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "jassids": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "200 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Propargite + Bifenthrin", "formulation": "50% + 5% SE", "dosage": "1100–1150 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
    },

    "potato": {
        "late blight": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Amisulbrom", "formulation": "20% SC", "dosage": "100 g a.i. / 500 ml formulation per hectare", "water_dilution": "375–500 litres", "waiting_period": "19 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Azoxystrobin", "formulation": "23% SC", "dosage": "125 gm a.i. / 500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "12 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Captan", "formulation": "50% WG", "dosage": "1500 gm formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Captan", "formulation": "50% WP", "dosage": "2.5 kg formulation per hectare", "water_dilution": "750–1000 litres", "waiting_period": "-", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Captan", "formulation": "75% WP", "dosage": "1667 gm formulation per hectare", "water_dilution": "1000 litres", "waiting_period": "8 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Chlorothalonil", "formulation": "75% WP", "dosage": "0.875–1.25 kg formulation per hectare", "water_dilution": "600–800 litres", "waiting_period": "14 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Iprovalicarb + Propineb", "formulation": "5.5% + 61.25% WP", "dosage": "2.0 kg formulation per hectare", "water_dilution": "500 litres", "waiting_period": "26 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Propineb + Cymoxanil", "formulation": "70.0% + 6.0% WP", "dosage": "2000–2250 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "At the end of harvest", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Picarbutrazox", "formulation": "9.53% w/w SC", "dosage": "1000–1250 ml formulation per hectare", "water_dilution": "750–1000 litres", "waiting_period": "34 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "1750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "47 days", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "early blight": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Captan", "formulation": "50% WG", "dosage": "1500 gm formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Captan", "formulation": "50% WP", "dosage": "2.5 kg formulation per hectare", "water_dilution": "750–1000 litres", "waiting_period": "-", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Captan", "formulation": "75% WP", "dosage": "1667 gm formulation per hectare", "water_dilution": "1000 litres", "waiting_period": "8 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Aureofungin", "formulation": "46.15% w/v SP", "dosage": "0.005% spray concentration", "water_dilution": "750 litres", "waiting_period": "30 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Chlorothalonil", "formulation": "75% WP", "dosage": "0.875–1.25 kg formulation per hectare", "water_dilution": "600–800 litres", "waiting_period": "14 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Propineb + Cymoxanil", "formulation": "70.0% + 6.0% WP", "dosage": "2000–2250 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "At the end of harvest", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "1750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "47 days", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "black scurf": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Azoxystrobin", "formulation": "23% SC", "dosage": "4.00 ml formulation (seed/tuber use as listed)", "water_dilution": "2.5 litres", "waiting_period": "-", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Pencycuron", "formulation": "22.9% SC", "dosage": "0.25–0.50 ml formulation", "water_dilution": "-", "waiting_period": "78 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Thifluzamide", "formulation": "24% SC", "dosage": "2.5 ml / 10 kg potato tuber", "water_dilution": "-", "waiting_period": "Used as seed treatment", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "1750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "47 days", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
    },

    "rice": {
        "blast": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Carpropamid", "formulation": "27.8% SC", "dosage": "0.1% formulation", "water_dilution": "300–500 litres depending upon crop stage", "waiting_period": "-", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim", "formulation": "50% WP", "dosage": "250–500 gm formulation per hectare", "water_dilution": "750 litres", "waiting_period": "-", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Picoxystrobin", "formulation": "22.52% w/w SC", "dosage": "600 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "12 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Prochloraz", "formulation": "39.6% w/w EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "26 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Prochloraz + Tricyclazole", "formulation": "23.5% + 20.0% w/w SE", "dosage": "1000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "28 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Inpyrfluxam + Tebuconazole", "formulation": "6% + 20% w/v SC", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Iprodione + Carbendazim", "formulation": "25% + 25% WP", "dosage": "500 gm formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Aureofungin", "formulation": "46.15% w/v SP", "dosage": "0.005% spray concentration", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "750 g formulation per hectare", "water_dilution": "750 litres or drone use as listed", "waiting_period": "57 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "1.92% + 10.08% GR", "dosage": "12.5 kg formulation per hectare", "water_dilution": "Broadcasting", "waiting_period": "46 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Mancozeb + Tebuconazole", "formulation": "4.7% + 59.7% + 5.6% WG", "dosage": "2000 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "31 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Pymetrozine + Dinotefuran + Pyraclostrobin", "formulation": "30% + 10% + 20% WG", "dosage": "375 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "leaf blast": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Inpyrfluxam + Tebuconazole", "formulation": "6% + 20% w/v SC", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Pymetrozine + Thiamethoxam + Hexaconazole", "formulation": "25% + 17.5% + 12.5% WG", "dosage": "400 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "19 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pyraclostrobin + Fipronil", "formulation": "10% + 5% SC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "53 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "sheath blight": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Pencycuron", "formulation": "22.9% SC", "dosage": "600–750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "69 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Polyoxin D Zinc Salt", "formulation": "5% SC", "dosage": "600 gm formulation per hectare", "water_dilution": "500 litres", "waiting_period": "0 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Inpyrfluxam + Tebuconazole", "formulation": "6% + 20% w/v SC", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Iprodione + Carbendazim", "formulation": "25% + 25% WP", "dosage": "500 gm formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Propiconazole + Difenoconazole", "formulation": "13.9% + 13.9% EC", "dosage": "0.7–1.0 ml/L", "water_dilution": "500 litres", "waiting_period": "46 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Isopyrazam + Difenoconazole", "formulation": "11.5% + 11.5% w/w SC", "dosage": "400 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Isopyrazam + Azoxystrobin", "formulation": "11.16% + 17.86% w/w SC", "dosage": "400 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "39 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Thifluzamide", "formulation": "24% SC", "dosage": "375 gm formulation per hectare", "water_dilution": "500 litres", "waiting_period": "28 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "1.92% + 10.08% GR", "dosage": "12.5 kg formulation per hectare", "water_dilution": "Broadcasting", "waiting_period": "46 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Mancozeb + Tebuconazole", "formulation": "4.7% + 59.7% + 5.6% WG", "dosage": "2000 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "31 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Pymetrozine + Tebuconazole", "formulation": "30% + 37% WG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "33 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "brown leaf spot": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Aureofungin", "formulation": "46.15% w/v SP", "dosage": "0.005% spray concentration", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim", "formulation": "5% GR", "dosage": "12.5 kg formulation per hectare", "water_dilution": "-", "waiting_period": "-", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Isopyrazam + Difenoconazole", "formulation": "11.5% + 11.5% w/w SC", "dosage": "400 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Isopyrazam + Azoxystrobin", "formulation": "11.16% + 17.86% w/w SC", "dosage": "400 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "39 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Mancozeb + Tebuconazole", "formulation": "4.7% + 59.7% + 5.6% WG", "dosage": "2000 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "31 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Pymetrozine + Tebuconazole", "formulation": "30% + 37% WG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "33 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "dirty panicle": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Propiconazole + Difenoconazole", "formulation": "13.9% + 13.9% EC", "dosage": "0.7–1.0 ml/L", "water_dilution": "500 litres", "waiting_period": "46 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Isopyrazam + Azoxystrobin", "formulation": "11.16% + 17.86% w/w SC", "dosage": "400 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "39 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Azoxystrobin + Mancozeb + Tebuconazole", "formulation": "4.7% + 59.7% + 5.6% WG", "dosage": "2000 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "31 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Pymetrozine + Tebuconazole", "formulation": "30% + 37% WG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "33 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "bacterial leaf blight": {
            "category": "bacterial",
            "recommended_products": [
                {"active_ingredient": "Pseudomonas fluorescens", "formulation": "2.0% AS", "dosage": "Seedling root dip: 10 ml/litre water; Foliar spray: 1.87–2.50 litre/ha", "water_dilution": "500 litres", "waiting_period": "NIL", "source": "CIBRC Bio-pesticides 30.09.2025"},
                {"active_ingredient": "Bacillus subtilis", "formulation": "2.0% AS", "dosage": "Seedling root dip: 10 ml/litre water; Foliar spray: 1.87–2.50 litre/ha", "water_dilution": "500 litres", "waiting_period": "NIL", "source": "CIBRC Bio-pesticides 30.09.2025"},
            ],
        },
        "leafspot": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Captan", "formulation": "50% WP", "dosage": "1000 gm formulation per hectare", "water_dilution": "750 litres", "waiting_period": "NA", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "stem borer": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acephate", "formulation": "75% SP", "dosage": "666–1000 g formulation per hectare", "water_dilution": "300–500 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "97% DF", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "95% SG", "dosage": "592 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Benfuracarb", "formulation": "3% GR", "dosage": "33000 g formulation per hectare", "water_dilution": "-", "waiting_period": "20 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Bifenthrin", "formulation": "8.80% CS", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Bifenthrin", "formulation": "10% EC", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Fipronil", "formulation": "80% WG", "dosage": "50–62.5 g formulation per hectare", "water_dilution": "375–500 litres", "waiting_period": "19 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid + Chlorpyriphos", "formulation": "0.40% + 20% EC", "dosage": "2.5 litre formulation per hectare", "water_dilution": "500–800 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azoxystrobin + Fipronil", "formulation": "10% + 5% SC", "dosage": "1250 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "53 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Fipronil + Dinotefuran", "formulation": "14.8% + 7.5% + 4.8% SC", "dosage": "875 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Thiamethoxam + Hexaconazole", "formulation": "25% + 17.5% + 12.5% WG", "dosage": "400 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "19 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Tolfenpyrad + Bifenthrin", "formulation": "15% + 7.5% SE", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "35 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Thiamethoxam + Fipronil + Chlorantraniliprole", "formulation": "1.25% + 1.25% + 0.60% GR", "dosage": "4500 g formulation per hectare", "water_dilution": "-", "waiting_period": "77 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Thiocyclam Hydrogen Oxalate + Clothianidin", "formulation": "3% + 1.2% GR", "dosage": "10000–12500 g formulation per hectare", "water_dilution": "-", "waiting_period": "56 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Pymetrozine", "formulation": "10% + 50% WG", "dosage": "300 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "43 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Lufenuron", "formulation": "16.9% + 16.9% SC", "dosage": "50 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "39 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Fipronil + Dinotefuran", "formulation": "14.8% + 7.5% + 4.8% SC", "dosage": "875 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "1500–2500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.03% EC", "dosage": "2000 ml formulation per hectare", "water_dilution": "1000 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
            ],
        },
        "leaf folder": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acephate", "formulation": "75% SP", "dosage": "666–1000 g formulation per hectare", "water_dilution": "300–500 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "97% DF", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "95% SG", "dosage": "592 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Bifenthrin", "formulation": "8.80% CS", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Bifenthrin", "formulation": "10% EC", "dosage": "500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Fipronil", "formulation": "80% WG", "dosage": "50–62.5 g formulation per hectare", "water_dilution": "375–500 litres", "waiting_period": "19 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azoxystrobin + Fipronil", "formulation": "10% + 5% SC", "dosage": "1250 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "53 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Thiamethoxam + Fipronil + Chlorantraniliprole", "formulation": "1.25% + 1.25% + 0.60% GR", "dosage": "4500 g formulation per hectare", "water_dilution": "-", "waiting_period": "77 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Pymetrozine", "formulation": "10% + 50% WG", "dosage": "300 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "43 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Lufenuron", "formulation": "16.9% + 16.9% SC", "dosage": "50 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "39 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "1500–2500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
            ],
        },
        "brown plant hopper": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acephate", "formulation": "95% SG", "dosage": "592 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid", "formulation": "20% SP", "dosage": "50–100 g formulation per hectare", "water_dilution": "500–600 litres", "waiting_period": "7 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Benzpyrimoxan", "formulation": "10% SC", "dosage": "750–1000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "31 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Sulfoxaflor", "formulation": "21.8% w/w SC", "dosage": "375 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "14 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "36 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Dinotefuran", "formulation": "29.2% + 11.7% WDG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Fipronil + Dinotefuran", "formulation": "14.8% + 7.5% + 4.8% SC", "dosage": "875 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Dinotefuran + Pyraclostrobin", "formulation": "30% + 10% + 20% WG", "dosage": "375 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Thiamethoxam + Hexaconazole", "formulation": "25% + 17.5% + 12.5% WG", "dosage": "400 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "19 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Benzpyrimoxan + Pymetrozine", "formulation": "10% + 20% WG", "dosage": "500–700 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "36 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Benzpyrimoxan + Thiamethoxam", "formulation": "10% + 3.3% SC", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Triflumezopyrim", "formulation": "11.3% + 1.9% SC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "31 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Tolfenpyrad + Bifenthrin", "formulation": "15% + 7.5% SE", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "35 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "1500–2500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.03% EC", "dosage": "2000 ml formulation per hectare", "water_dilution": "1000 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
            ],
        },
        "white backed plant hopper": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Sulfoxaflor", "formulation": "21.8% w/w SC", "dosage": "375 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "14 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "36 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Dinotefuran", "formulation": "29.2% + 11.7% WDG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Fipronil + Dinotefuran", "formulation": "14.8% + 7.5% + 4.8% SC", "dosage": "875 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Benzpyrimoxan + Pymetrozine", "formulation": "10% + 20% WG", "dosage": "500–700 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "36 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Benzpyrimoxan + Thiamethoxam", "formulation": "10% + 3.3% SC", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Dinotefuran + Pyraclostrobin", "formulation": "30% + 10% + 20% WG", "dosage": "375 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid + Chlorpyriphos", "formulation": "0.40% + 20% EC", "dosage": "2.50 litre formulation per hectare", "water_dilution": "500–800 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "green leafhopper": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acephate", "formulation": "75% SP", "dosage": "666–1000 g formulation per hectare", "water_dilution": "300–500 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "97% DF", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "36 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Dinotefuran", "formulation": "29.2% + 11.7% WDG", "dosage": "500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Benzpyrimoxan + Pymetrozine", "formulation": "10% + 20% WG", "dosage": "500–700 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "36 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Pymetrozine + Fipronil + Dinotefuran", "formulation": "14.8% + 7.5% + 4.8% SC", "dosage": "875 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Tolfenpyrad + Bifenthrin", "formulation": "15% + 7.5% SE", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "35 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "plant hoppers": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acephate", "formulation": "75% SP", "dosage": "666–1000 g formulation per hectare", "water_dilution": "300–500 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "97% DF", "dosage": "750 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "21 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "thrips": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "1500–2500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
            ],
        },
    },

    "wheat": {
        "loose smut": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Carbendazim", "formulation": "50% WP", "dosage": "2 gm formulation per kg seed", "water_dilution": "1 litre / 10 kg seed (wet slurry treatment)", "waiting_period": "-", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Carboxin", "formulation": "75% WP", "dosage": "2–2.5 gm formulation per kg seed", "water_dilution": "N/A", "waiting_period": "Only one-time seed treatment required", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Tebuconazole", "formulation": "2% DS", "dosage": "0.2 kg / 10 kg seed", "water_dilution": "10 L / 10 kg seed", "waiting_period": "-", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Pseudomonas fluorescens", "formulation": "1.75% WP", "dosage": "Seed treatment: 5 g/kg seed; Foliar spray: 2.5 kg/ha (5 g/litre water)", "water_dilution": "500 litres", "waiting_period": "-", "source": "CIBRC Bio-pesticides 30.09.2025"},
            ],
        },
        "smut": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Seed dresser combination", "formulation": "37:3", "dosage": "200 units as seed dresser", "water_dilution": "NA", "waiting_period": "Seed dresser use", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Sulphur", "formulation": "85% DP", "dosage": "3–4 g/kg seed", "water_dilution": "-", "waiting_period": "-", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "rust": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Azoxystrobin + Cyproconazole", "formulation": "18.2% + 7.3% SC", "dosage": "1% formulation", "water_dilution": "500 litres via knapsack sprayer", "waiting_period": "50 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Seed dresser combination", "formulation": "37:3", "dosage": "200 units as seed dresser", "water_dilution": "NA", "waiting_period": "Seed dresser use", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Sulphur", "formulation": "85% DP", "dosage": "15–20 kg formulation", "water_dilution": "-", "waiting_period": "-", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "powdery mildew": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Azoxystrobin + Cyproconazole", "formulation": "18.2% + 7.3% SC", "dosage": "1% formulation", "water_dilution": "500 litres via knapsack sprayer", "waiting_period": "50 days", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
                {"active_ingredient": "Sulphur", "formulation": "80% WG", "dosage": "2500 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "24 days", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "termites": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Seed dresser combination", "formulation": "37:3", "dosage": "200 units as seed dresser", "water_dilution": "NA", "waiting_period": "Seed dresser use", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
            ],
        },
        "aphids": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Seed dresser combination", "formulation": "37:3", "dosage": "200 units as seed dresser", "water_dilution": "NA", "waiting_period": "Seed dresser use", "source": "CIBRC Fungicides Combination Uses 30.09.2025"},
            ],
        },
    },

    "cotton": {
        "whitefly": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acetamiprid", "formulation": "20% SP", "dosage": "100 g formulation per hectare", "water_dilution": "500–600 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Afidopyropen", "formulation": "50 g/L DC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–750 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Bifenthrin", "formulation": "10% EC", "dosage": "800 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "2500–5000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "5.00% Neem Extract", "dosage": "375 ml formulation per hectare", "water_dilution": "750 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Spiromesifen", "formulation": "22.90% SC", "dosage": "600 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Fenpropathrin", "formulation": "50% + 5% EC", "dosage": "1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Lambda Cyhalothrin", "formulation": "40% + 1.5% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Clothianidin + Pyriproxyfen", "formulation": "3.5% + 8% SE", "dosage": "1250–1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "60 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Diafenthiuron", "formulation": "7.3% + 36.4% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "29 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "whitefly": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acetamiprid", "formulation": "20% SP", "dosage": "100 g formulation per hectare", "water_dilution": "500–600 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Afidopyropen", "formulation": "50 g/L DC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–750 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Bifenthrin", "formulation": "10% EC", "dosage": "800 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "2500–5000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Spiromesifen", "formulation": "22.90% SC", "dosage": "600 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Fenpropathrin", "formulation": "50% + 5% EC", "dosage": "1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Lambda Cyhalothrin", "formulation": "40% + 1.5% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Clothianidin + Pyriproxyfen", "formulation": "3.5% + 8% SE", "dosage": "1250–1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "60 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Diafenthiuron", "formulation": "7.3% + 36.4% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "29 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "bollworms": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acephate", "formulation": "75% SP", "dosage": "780 g formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "97% DF", "dosage": "450–600 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "48 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Alphacypermethrin", "formulation": "10.00% EC", "dosage": "165–280 ml formulation per hectare", "water_dilution": "600–1000 litres", "waiting_period": "7 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Alphacypermethrin", "formulation": "10.00% SC", "dosage": "250–300 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "2500–5000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.30% EC (3000 PPM)", "dosage": "4000 ml formulation per hectare", "water_dilution": "1000 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.03% EC", "dosage": "2500–5000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Nuclear Polyhedrosis Virus of Helicoverpa armigera", "formulation": "0.43% AS", "dosage": "2700 ml formulation per hectare", "water_dilution": "400–600 litres", "waiting_period": "-", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid + Cypermethrin", "formulation": "1.10% + 5.50% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "400–1000 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Chlorpyriphos + Alphacypermethrin", "formulation": "16% + 1% EC", "dosage": "2500 ml formulation per hectare", "water_dilution": "500–750 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Clothianidin + Pyriproxyfen", "formulation": "3.5% + 8% SE", "dosage": "1250–1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "60 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Diafenthiuron", "formulation": "7.3% + 36.4% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "29 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "pink bollworm": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Tolfenpyrad + Bifenthrin", "formulation": "15% + 7.5% SE", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "54 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Fenpropathrin", "formulation": "50% + 5% EC", "dosage": "1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "22 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Lambda Cyhalothrin", "formulation": "40% + 1.5% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Diafenthiuron", "formulation": "7.3% + 36.4% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "29 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "american bollworm": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Azadirachtin", "formulation": "0.30% EC (3000 PPM)", "dosage": "4000 ml formulation per hectare", "water_dilution": "1000 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Chlorpyriphos + Alphacypermethrin", "formulation": "16% + 1% EC", "dosage": "2500 ml formulation per hectare", "water_dilution": "500–750 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "spotted bollworm": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Chlorpyriphos + Alphacypermethrin", "formulation": "16% + 1% EC", "dosage": "2500 ml formulation per hectare", "water_dilution": "500–750 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "jassids": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acephate", "formulation": "75% SP", "dosage": "390 g formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acephate", "formulation": "97% DF", "dosage": "450–600 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "48 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid", "formulation": "20% SP", "dosage": "50 g formulation per hectare", "water_dilution": "500–600 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Afidopyropen", "formulation": "50 g/L DC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–750 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Broflanilide", "formulation": "20% SC", "dosage": "125 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid + Cypermethrin", "formulation": "1.10% + 5.50% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "400–1000 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Clothianidin + Pyriproxyfen", "formulation": "3.5% + 8% SE", "dosage": "1250–1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "60 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Diafenthiuron", "formulation": "7.3% + 36.4% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "29 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Lambda Cyhalothrin", "formulation": "40% + 1.5% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "aphids": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Acetamiprid", "formulation": "20% SP", "dosage": "50 g formulation per hectare", "water_dilution": "500–600 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.03% EC", "dosage": "2500–5000 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "5.00% Neem Extract", "dosage": "375 ml formulation per hectare", "water_dilution": "750 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Spirotetramat", "formulation": "15.31% w/w OD", "dosage": "700 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "52 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid + Cypermethrin", "formulation": "1.10% + 5.50% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "400–1000 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Lambda Cyhalothrin", "formulation": "40% + 1.5% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Clothianidin + Pyriproxyfen", "formulation": "3.5% + 8% SE", "dosage": "1250–1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "60 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Diafenthiuron", "formulation": "7.3% + 36.4% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "29 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "thrips": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Broflanilide", "formulation": "20% SC", "dosage": "125 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Flonicamid", "formulation": "50% WG", "dosage": "150 g formulation per hectare", "water_dilution": "500 litres", "waiting_period": "25 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Fipronil", "formulation": "80% WG", "dosage": "75 g formulation per hectare", "water_dilution": "375–500 litres", "waiting_period": "14 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Spirotetramat", "formulation": "15.31% w/w OD", "dosage": "700 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "52 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Acetamiprid + Cypermethrin", "formulation": "1.10% + 5.50% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "400–1000 litres", "waiting_period": "30 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Profenofos + Lambda Cyhalothrin", "formulation": "40% + 1.5% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Clothianidin + Pyriproxyfen", "formulation": "3.5% + 8% SE", "dosage": "1250–1500 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "60 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Cyantraniliprole + Diafenthiuron", "formulation": "7.3% + 36.4% SC", "dosage": "625 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "29 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Tolfenpyrad + Bifenthrin", "formulation": "15% + 7.5% SE", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "54 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "mites": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Spiromesifen", "formulation": "22.90% SC", "dosage": "600 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "leafhoppers": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Profenofos + Lambda Cyhalothrin", "formulation": "40% + 1.5% EC", "dosage": "1000 ml formulation per hectare", "water_dilution": "500–1000 litres", "waiting_period": "15 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Tolfenpyrad + Bifenthrin", "formulation": "15% + 7.5% SE", "dosage": "750 ml formulation per hectare", "water_dilution": "500 litres", "waiting_period": "54 days", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
    },
    "onion": {
        "purple blotch": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Mancozeb", "formulation": "75% WP", "dosage": "2.5 kg/ha", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Azoxystrobin", "formulation": "23% SC", "dosage": "500 ml/ha", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "750 g/ha", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
            ],
        },
        "anthracnose": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Mancozeb", "formulation": "75% WP", "dosage": "2.5 kg/ha", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Carbendazim", "formulation": "50% WP", "dosage": "1 g/litre water", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Fungicides 30.09.2025"},
            ],
        },
        "downy mildew": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Metalaxyl + Mancozeb", "formulation": "8% + 64% WP", "dosage": "2 kg/ha", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Fungicides 30.09.2025"},
                {"active_ingredient": "Chlorothalonil", "formulation": "75% WP", "dosage": "1.25 kg/ha", "water_dilution": "500 litres", "waiting_period": "14 days", "source": "CIBRC Fungicides 30.09.2025"},
            ],
        },
        "thrips": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Spinosad", "formulation": "45% SC", "dosage": "75 ml/ha", "water_dilution": "500 litres", "waiting_period": "3 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Fipronil", "formulation": "5% SC", "dosage": "1000 ml/ha", "water_dilution": "500 litres", "waiting_period": "6 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "2500 ml/ha", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
            ],
        },
        "weed control": {
            "category": "weed",
            "recommended_products": [
                {"active_ingredient": "Oxyfluorfen", "formulation": "23.5% EC", "dosage": "425-850 ml/ha", "water_dilution": "500-750 litres", "waiting_period": "-", "source": "CIBRC Herbicides 30.09.2025"},
            ],
        },
    },

    "maize": {
        "fall armyworm": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Chlorantraniliprole", "formulation": "18.5% SC", "dosage": "200 ml/ha", "water_dilution": "200 litres", "waiting_period": "14 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Chlorantraniliprole", "formulation": "0.40% GR", "dosage": "50 kg/ha", "water_dilution": "-", "waiting_period": "12.5 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Spinetoram", "formulation": "11.70% SC", "dosage": "250 ml/ha", "water_dilution": "500 litres", "waiting_period": "32 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Flubendiamide", "formulation": "20% WG", "dosage": "250 ml/ha", "water_dilution": "500 litres", "waiting_period": "55 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Emamectin Benzoate", "formulation": "5% SG", "dosage": "200-250 ml/ha", "water_dilution": "500 litres", "waiting_period": "10 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Azadirachtin", "formulation": "0.15% EC", "dosage": "2500 ml/ha", "water_dilution": "500 litres", "waiting_period": "5 days", "source": "CIBRC Bio-insecticides 03.10.2025"},
            ],
        },
        "stem borer": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Chlorantraniliprole", "formulation": "18.5% SC", "dosage": "150 ml/ha", "water_dilution": "500 litres", "waiting_period": "14 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Fipronil", "formulation": "0.3% GR", "dosage": "10 kg/ha", "water_dilution": "-", "waiting_period": "65 days", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Dimethoate", "formulation": "30% EC", "dosage": "660 ml/ha", "water_dilution": "500-1000 litres", "waiting_period": "-", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "shoot fly": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Thiamethoxam", "formulation": "30% FS", "dosage": "350 ml seed treatment", "water_dilution": "-", "waiting_period": "-", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Imidacloprid", "formulation": "48% FS", "dosage": "1.0 ml/kg seed", "water_dilution": "-", "waiting_period": "-", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
        "downy mildew": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Metalaxyl + Mancozeb", "formulation": "8% + 64% WP", "dosage": "2 kg/ha", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Fungicides 30.09.2025"},
            ],
        },
        "turcicum leaf blight": {
            "category": "fungal",
            "recommended_products": [
                {"active_ingredient": "Carbendazim + Mancozeb", "formulation": "12% + 63% WP", "dosage": "750 g/ha", "water_dilution": "500 litres", "waiting_period": "7 days", "source": "CIBRC Chemical MUP 30.09.2025"},
                {"active_ingredient": "Trichoderma harzianum", "formulation": "2.0% WP", "dosage": "20 g/kg seed (seed treatment)", "water_dilution": "-", "waiting_period": "-", "source": "CIBRC Bio-pesticides 30.09.2025"},
            ],
        },
        "aphids": {
            "category": "pest",
            "recommended_products": [
                {"active_ingredient": "Thiamethoxam", "formulation": "30% FS", "dosage": "1.8 g a.i./kg seed", "water_dilution": "-", "waiting_period": "-", "source": "CIBRC Insecticides 03.10.2025"},
                {"active_ingredient": "Dimethoate", "formulation": "30% EC", "dosage": "660 ml/ha", "water_dilution": "500-1000 litres", "waiting_period": "-", "source": "CIBRC Insecticides 03.10.2025"},
            ],
        },
    },

}


def get_medicine(crop, disease):
    """
    Look up treatment for a crop-disease pair.
    Matching order:
    1. Exact match (case-insensitive)
    2. DB key fully contained in disease string
    3. Weighted word-overlap (filters weak words to avoid false matches)
    Returns the disease entry dict, or None if not found.
    """
    WEAK_WORDS = {"leaf", "spot", "rot", "of", "the", "on", "in", "and", "rice", "wheat", "cotton", "tomato", "potato", "maize"}

    crop_key    = crop.lower().strip()
    disease_key = disease.lower().strip()

    crop_data = MEDICINE_DB.get(crop_key)
    if crop_data is None:
        return None

    # 1. Exact match
    if disease_key in crop_data:
        return crop_data[disease_key]

    # 2. DB key fully contained in disease string
    for key in crop_data:
        if key in disease_key:
            return crop_data[key]

    # 3. Weighted word overlap — ignore weak/generic words
    disease_words = set(disease_key.split()) - WEAK_WORDS
    if not disease_words:
        return None

    best_key   = None
    best_score = 0.0

    for key in crop_data:
        key_words = set(key.split()) - WEAK_WORDS
        if not key_words:
            continue
        overlap = disease_words & key_words
        if not overlap:
            continue
        score = len(overlap) / len(key_words)
        if score > best_score:
            best_score = score
            best_key   = key

    # Require at least 50% of key words to match
    if best_key and best_score >= 0.5:
        return crop_data[best_key]

    return None


def get_available_crops():
    return sorted(MEDICINE_DB.keys())


def get_issues_for_crop(crop: str):
    return sorted(MEDICINE_DB.get(crop.lower().strip(), {}).keys())


def get_all_medicines() -> list[dict]:
    """
    Return all MEDICINE_DB entries as a flat list of dicts for vector DB indexing.

    Each dict has keys:
        crop          : str   — e.g. "tomato"
        issue_name    : str   — e.g. "early blight"
        category      : str   — e.g. "fungal" / "pest" / "bacterial"
        ingredient_str: str   — concatenated active ingredients + formulations
    """
    results = []
    for crop, diseases in MEDICINE_DB.items():
        for disease_name, data in diseases.items():
            products = data.get("recommended_products", [])
            ingredient_str = " | ".join(
                f"{p.get('active_ingredient', '')} {p.get('formulation', '')}".strip()
                for p in products
            )
            results.append({
                "crop":           crop,
                "issue_name":     disease_name,
                "category":       data.get("category", "unknown"),
                "ingredient_str": ingredient_str,
            })
    return results