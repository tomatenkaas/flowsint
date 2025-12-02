import httpx
import json
from typing import List, Dict, Any, Tuple
from urllib.parse import urljoin

# Flowsint Necessary Imports
from flowsint_enrichers.registry import flowsint_enricher
from flowsint_core.core.enricher_base import Enricher
from flowsint_core.core.logger import Logger
from flowsint_types.individual import Individual
# NEW: Import the new English type
from flowsint_types.judgment import Judgment 

# --- CONFIGURATION ---
BASE_URL = "https://uitspraken.rechtspraak.nl/"
API_ENDPOINT = "api/zoek"
API_URL = urljoin(BASE_URL, API_ENDPOINT)

# The minimal headers required for a successful POST to the API
POST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*"
}

def create_payload(search_term: str) -> Dict[str, Any]:
    """Creates the JSON payload for the POST call."""
    return {
        "StartRow": 0,
        "PageSize": 100,
        "ShouldReturnHighlights": True,
        "ShouldCountFacets": True,
        "SortOrder": "Relevance",
        # The search term must be in the API payload
        "SearchTerms": [{"Term": search_term.lower(), "Field": "AlleVelden"}], 
        "Contentsoorten": [],
        "Rechtsgebieden": [],
        "Instanties": [],
        "DatumPublicatie": [],
        "DatumUitspraak": [],
        "CorrelationId":"8b0d06c00ff7499686dca71eff62d203",
        "Advanced": {"PublicatieStatus": "AlleenGepubliceerd"},
        "Proceduresoorten": []
    }


@flowsint_enricher
class IndividualToJudgmentsEnricher(Enricher):
    """
    Searches for an individual on Rechtspraak.nl via the internal JSON API and extracts deeplinks to the judgments.
    """

    InputType = Individual
    OutputType = tuple[Individual, Judgment]

    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        return []
    
    @classmethod
    def name(cls) -> str:
        # Use an English name for the enricher
        return "individual_to_dutch_judgments" 

    @classmethod
    def category(cls) -> str:
        return "Source"

    @classmethod
    def key(cls) -> str:
        return "individual"

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        """Calls the Rechtspraak API with the individual's name."""
        
        results: List[OutputType] = []
        
        async with httpx.AsyncClient(headers=POST_HEADERS, follow_redirects=True) as client:
            for individual_obj in data:
                
                search_term = individual_obj.full_name or f"{individual_obj.first_name} {individual_obj.last_name}"
                if not search_term:
                    Logger.warning(self.sketch_id, {"message": "No search term available for individual."})
                    continue
                
                payload = create_payload(search_term)
                response = None 

                try:
                    Logger.info(self.sketch_id, {"message": f"Calling Rechtspraak API for '{search_term}'..."})
                    
                    response = await client.post(API_URL, json=payload, timeout=30.0)
                    response.raise_for_status()
                    
                    response_json = response.json()
                    
                    links_found = 0
                    
                    for item in response_json.get('Results', []):
                        deeplink_url = item.get('DeeplinkUrl')
                        text_fragment = item.get('Tekstfragment', 'No summary available')
                        ecli_code = item.get('TitelEmphasis', 'Unknown ECLI')
                        judgment_date = item.get('Uitspraakdatum', None)
                        
                        # Create the label (first 5 words + ...)
                        excerpt = " ".join(text_fragment.split()[:5]) + "..."
                        
                        if deeplink_url:
                            try:
                                # Create Judgment object and store all metadata
                                judgment_obj = Judgment(
                                    url=deeplink_url, 
                                    label=excerpt, 
                                    ecli=ecli_code,
                                    summary=text_fragment,
                                    publication_date=judgment_date
                                ) 
                                results.append((individual_obj, judgment_obj))
                                links_found += 1
                            except Exception as e:
                                Logger.error(self.sketch_id, {"message": f"Invalid Deeplink URL: {deeplink_url}. Error: {e}"})
                        else:
                            Logger.warning(self.sketch_id, {"message": f"No DeeplinkUrl found for a result of '{search_term}'."})


                    Logger.info(self.sketch_id, {"message": f"Found {links_found} judgments for '{search_term}'."})

                except httpx.HTTPStatusError as e:
                    response = getattr(e, 'response', None) 
                    error_details = response.text[:100] if response else "No response received."
                    Logger.error(self.sketch_id, {"message": f"HTTP Error ({e.response.status_code}) with Rechtspraak API for '{search_term}'. Response: {error_details}"})
                except json.JSONDecodeError:
                    error_details = response.text[:100] if response else "No response received."
                    Logger.error(self.sketch_id, {"message": f"JSON Decode Error. Server did not return JSON for '{search_term}'. Response: {error_details}"})
                except Exception as e:
                    Logger.error(self.sketch_id, {"message": f"Unexpected error in Rechtspraak Enricher: {e}"})
        
        return results

    def postprocess(self, results: List[OutputType], original_input: List[InputType]) -> List[OutputType]:
        """Creates the relationship between the Individual and the found Judgments."""

        for individual_obj in original_input:
             self.create_node(individual_obj)

        for individual_obj, judgment_obj in results:
            
            self.create_node(judgment_obj)

            self.create_relationship(
                individual_obj, 
                judgment_obj, 
                "CITED_BY" 
            )

            full_name = individual_obj.full_name or f"{individual_obj.first_name} {individual_obj.last_name}"
            
            excerpt_label = judgment_obj.label
            
            self.log_graph_message(
                f"Rechtspraak judgment '{excerpt_label}' found for individual '{full_name}'."
            )

        return results