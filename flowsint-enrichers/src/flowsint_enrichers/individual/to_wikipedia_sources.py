import httpx
from typing import List, Dict, Any, Tuple
# Import van urllib.parse is niet langer nodig, Website type doet de validatie

# Flowsint Noodzakelijke Imports
from flowsint_enrichers.registry import flowsint_enricher
from flowsint_core.core.enricher_base import Enricher
from flowsint_core.core.logger import Logger
from flowsint_types.individual import Individual
from flowsint_types.website import Website # <--- CORRECTIE 1: Importeer Website

# --- CONFIGURATIE ---
DEFAULT_WIKI_URL = "https://nl.wikipedia.org/w/api.php"

@flowsint_enricher
class IndividualToWikipediaEnricher(Enricher):
    """
    Zoekt een individu op de Nederlandse Wikipedia en extraheert externe bron-URLs.
    """

    InputType = Individual
    # Output is een tuple van (origineel Individual object, Website object)
    OutputType = tuple[Individual, Website] # <--- CORRECTIE 2: Gebruik Website

    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "WIKIPEDIA_API_URL",
                "type": "url",
                "description": "De MediaWiki API URL (standaard: Nederlandse Wikipedia).",
                "required": False,
                "default": DEFAULT_WIKI_URL,
            },
        ]
    
    @classmethod
    def name(cls) -> str:
        return "individual_to_wikipedia_sources"

    @classmethod
    def category(cls) -> str:
        return "Source"

    @classmethod
    def key(cls) -> str:
        return "individual"
    async def scan(self, data: List[InputType]) -> List[OutputType]:
        """Zoekt het individu en haalt de externe links op via de Wikipedia API."""
        
        api_url = self.get_params().get("WIKIPEDIA_API_URL", DEFAULT_WIKI_URL)
        results: List[OutputType] = []

        # STAP 1: Voeg de User-Agent header toe. Dit is cruciaal voor de Wikipedia API (403 fix).
        headers = {
            "User-Agent": "Flowsint-Enricher-Project/1.0 (Contact: ilja@nas01.nl)" 
        }

        async with httpx.AsyncClient(headers=headers) as client: # <-- Gebruik de headers hier
            for individual_obj in data:
                
                if individual_obj.full_name:
                    search_term = individual_obj.full_name
                else:
                    search_term = f"{individual_obj.first_name} {individual_obj.last_name}"
                
                # ... STAP A: Zoek de exacte Wikipedia pagina titel ...
                search_params = {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": search_term,
                    "srlimit": 1,
                }

                try:
                    # 1. Zoek naar de pagina titel
                    # Client stuurt nu de User-Agent mee
                    response = await client.get(api_url, params=search_params, timeout=10.0)
                    response.raise_for_status()
                    search_data = response.json()
                    
                    hits = search_data.get('query', {}).get('search', [])
                    if not hits:
                        Logger.info(self.sketch_id, {"message": f"Geen Wikipedia-pagina gevonden voor '{search_term}'."})
                        continue

                    page_title = hits[0]['title']
                    
                    # ... STAP B: Haal alle externe links (extlinks) van die pagina op ...
                    extlinks_params = {
                        "action": "query",
                        "format": "json",
                        "titles": page_title,
                        "prop": "extlinks",
                        "ellimit": 500,
                    }

                    # 2. Haal de links op
                    response = await client.get(api_url, params=extlinks_params, timeout=10.0)
                    response.raise_for_status()
                    links_data = response.json()
                    
                    pages = links_data.get('query', {}).get('pages', {})
                    links_found = 0
                    
                    for page_id in pages:
                        extlinks = pages[page_id].get('extlinks', [])
                        
                        for link_entry in extlinks:
                            url_string = link_entry.get('*')
                            if url_string:
                                try:
                                    # Gebruik het Website object. Pydantic valideert de URL nu.
                                    website_obj = Website(url=url_string) 
                                    
                                    results.append((individual_obj, website_obj))
                                    links_found += 1
                                    
                                except Exception as e:
                                    Logger.error(self.sketch_id, {"message": f"Fout bij verwerken URL '{url_string}': {e}"})
                                
                    Logger.info(self.sketch_id, {"message": f"Vond {links_found} links voor '{page_title}'."})
                
                except httpx.HTTPStatusError as e:
                    # Log nu ook de response tekst voor meer details bij een 403 of 404
                    error_details = e.response.text.strip()[:200]
                    Logger.error(self.sketch_id, {"message": f"API Error ({e.response.status_code}) voor '{search_term}'. Details: {error_details}"})
                except Exception as e:
                    Logger.error(self.sketch_id, {"message": f"Onverwachte fout bij Wikipedia Enricher: {e}"})
        
        return results
    
    def postprocess(self, results: List[OutputType], original_input: List[InputType]) -> List[OutputType]:
            """Creëert de relatie tussen de Individual en de gevonden Website's."""

            # STAP 1: Zorg ervoor dat de input nodes (Individual) in de graaf staan.
            # Dit garandeert dat we de exacte, canonieke node-referentie hebben 
            # voor de bron van de relatie.
            for individual_obj in original_input:
                self.create_node(individual_obj)


            # STAP 2: Creëer de output nodes (Website) en de relaties.
            for individual_obj, website_obj in results:
                
                # 1. Creëer de Website node
                self.create_node(website_obj)

                # 2. Creëer de relatie: (INDIVIDUAL)-[CITED_BY]->(WEBSITE)
                # We gebruiken de individual_obj uit de results-tuple. 
                # Omdat deze structureel identiek is aan de node uit original_input (zie stap 1), 
                # zal create_relationship nu de juiste bronnode vinden.
                self.create_relationship(
                    individual_obj, 
                    website_obj, 
                    "CITED_BY"
                )

                full_name = individual_obj.full_name or f"{individual_obj.first_name} {individual_obj.last_name}"
                self.log_graph_message(
                    f"Website '{website_obj.url}' gevonden als bron voor individu '{full_name}'."
                )

            return results

# Exporteer de types
InputType = IndividualToWikipediaEnricher.InputType
OutputType = IndividualToWikipediaEnricher.OutputType