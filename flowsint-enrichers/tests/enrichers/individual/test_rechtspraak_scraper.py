import requests
import json
from typing import Dict, Any
from urllib.parse import urljoin

# --- CONFIGURATIE ---
BASE_URL = "https://uitspraken.rechtspraak.nl/"
API_ENDPOINT = "api/zoek"
API_URL = urljoin(BASE_URL, API_ENDPOINT)

TEST_NAME = "Mark Rutte" 

# De minimale, succesvolle headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*"
}

def create_payload(search_term: str) -> Dict[str, Any]:
    """Maakt de JSON-payload voor de POST-aanroep."""
    return {
        "StartRow": 0,
        "PageSize": 10,
        "ShouldReturnHighlights": True,
        "ShouldCountFacets": True,
        "SortOrder": "Relevance",
        "SearchTerms": [{"Term": search_term.lower(), "Field": "AlleVelden"}], 
        "Contentsoorten": [],
        "Rechtsgebieden": [],
        "Instanties": [],
        "DatumPublicatie": [],
        "DatumUitspraak": [],
        "CorrelationId":"8b0d06c00ff7499686dca71eff62d203",
        "Advanced": {"PublicatieStatus": "AlleenGepubliceerd"},
        "Proceduresoorten": []
        # CorrelationId is optioneel en hoeft niet in het script
    }

def test_rechtspraak_api(search_term: str):
    print(f"--- Test start voor: {search_term} (Simpele POST) ---")
    
    payload = create_payload(search_term)
    response = None

    try:
        print(f"POST naar {API_URL}...")
        
        # Voer de enkele POST-aanroep uit
        response = requests.post(
            API_URL, 
            headers=HEADERS, 
            json=payload, 
            timeout=30
        )
        
        response.raise_for_status() 

        print(f"STATUS: {response.status_code} OK")
        
        # JSON-data verwerken
        response_json = response.json()
        
        results = response_json.get('Results', [])
        result_count_total = response_json.get('ResultCount', len(results))
        
        print(f"TOTAAL GEVONDEN UITSPRAKEN: {result_count_total}")
        print(f"VERWERKTE UITSPRAKEN: {len(results)}")

        if len(results) > 0:
            print("\n--- Gevonden Deeplinks (eerste 3) ---")
            for i, item in enumerate(results[:3]):
                deeplink = item.get('DeeplinkUrl')
                titel = item.get('TitelEmphasis')
                print(f"[{i+1}] ECLI: {titel} -> {deeplink}")
            print("--------------------------------------\n")
        else:
             print("\nGEEN LINKS GEVONDEN.")


    except requests.exceptions.HTTPError as e: 
        print(f"\nFOUT: HTTP Error {e.response.status_code} ({e.response.reason})")
    
    except json.JSONDecodeError:
        print("\nFOUT: JSON Decode Fout. De server stuurde geen geldige JSON terug.")
        if response:
             print(f"RAW Response Tekst (eerste 500): {response.text[:500]}...")
        
    except Exception as e:
        print(f"\nONVERWACHTE FOUT: {e}")

# Voer de test uit
test_rechtspraak_api(TEST_NAME)