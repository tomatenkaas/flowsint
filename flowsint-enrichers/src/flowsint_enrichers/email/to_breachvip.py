import os
import httpx
from typing import List, Optional, Dict, Any, Tuple, Union
from pydantic import ValidationError
from urllib.parse import urljoin # <-- NIEUWE IMPORT

# FIX: Relatieve import van de registry
# Aanname: flowsint_enricher is hier geregistreerd
from flowsint_core.core.enricher_base import Enricher
from flowsint_core.core.logger import Logger
from flowsint_types.email import Email
from flowsint_types.leak import Leak

# --- CONFIGURATIE ---
# Standaard URL, wordt overschreven door Flowsint parameters indien aanwezig
DEFAULT_BASE_URL = "https://breach.vip/api/search"


class EmailToBreachVipEnricher(Enricher):
    """Zoekt e-mailadressen op in de BreachVIP-database."""

    InputType = Email
    OutputType = tuple[str, Leak] # Type hint: (email_string, Leak_object)

    # NIEUW: Voeg de configuratie toe (conform HIBP-voorbeeld)
    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        """Declareer configureerbare parameters voor deze enricher"""
        return [
            {
                "name": "BREACHVIP_API_URL",
                "type": "url",
                "description": "De BreachVIP API URL voor de search-endpoint.",
                "required": False,
                "default": DEFAULT_BASE_URL,
            },
        ]
    
    @classmethod
    def name(cls) -> str:
        return "email_to_breachvip"

    @classmethod
    def category(cls) -> str:
        return "Leak"

    @classmethod
    def key(cls) -> str:
        return "email"

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        """Roep de BreachVIP API aan voor elk e-mailadres."""
        
        # Haal de basis-URL op uit de parameters of gebruik de default
        api_url = self.get_params().get("BREACHVIP_API_URL", DEFAULT_BASE_URL)
        
        results: List[OutputType] = []

        async with httpx.AsyncClient() as client:
            for email_obj in data:
                email_address = email_obj.email

                # De API is een POST naar de basis-URL, de term zit in de JSON-payload
                payload = {
                    "term": email_address,
                    "fields": ["email"],
                    "wildcard": False,
                    "case_sensitive": False
                }

                Logger.info(self.sketch_id, {"message": f"BreachVIP zoeken naar {email_address} via {api_url}"})

                try:
                    # De API-aanroep
                    response = await client.post(
                        api_url, # Gebruik de configureerbare URL
                        json=payload,
                        timeout=30.0
                    )

                    response.raise_for_status()

                    api_data = response.json()
                    hits = api_data.get('results', [])

                    # 3. Verwerk de resultaten
                    for hit in hits:
                        try:
                            # Creëer het Leak object
                            leak_result = Leak(
                                name=hit['source'],
                                leak=[hit],
                            )

                            # Retourneer als tuple: (email_string, Leak_object)
                            results.append((email_address, leak_result))

                        except ValidationError as e:
                            Logger.error(self.sketch_id, {"message": f"Pydantic Validatie Fout op hit: {e}"})
                            continue
                        except KeyError as e:
                            Logger.error(self.sketch_id, {"message": f"Key Error bij parsen hit: {e}. Ruwe hit: {hit}"})
                            continue

                    Logger.info(self.sketch_id, {"message": f"Vond {len(hits)} breaches voor {email_address}."})

                except httpx.HTTPStatusError as e:
                    Logger.error(self.sketch_id, {"message": f"API Error: Status {e.response.status_code} voor {email_address}. Rate limit? {e}"})
                except Exception as e:
                    Logger.error(self.sketch_id, {"message": f"Onverwachte fout bij BreachVIP: {e}"})
                    continue

        return results

    def postprocess(self, results: List[OutputType], original_input: List[InputType]) -> List[OutputType]:
        """Creëer de graafnodes en relaties."""

        # FIX: Loop over de tuple (email_address, leak_obj)
        for email_address, leak_obj in results:

            # 1. Creëer de node voor de Leak
            self.create_node(leak_obj)

            # 2. Creëer het Email object opnieuw uit de string
            email_obj = Email(email=email_address)
            self.create_node(email_obj)

            # 3. Creëer de relatie: (EMAIL)-[EXPOSED_IN]->(LEAK)
            self.create_relationship(
                email_obj,
                leak_obj,
                "EXPOSED_IN"
            )

            self.log_graph_message(
                f"E-mail gevonden in de breach: {email_address} -> {leak_obj.name}"
            )

        return results

# Export types aan het einde van het bestand
InputType = EmailToBreachVipEnricher.InputType
OutputType = EmailToBreachVipEnricher.OutputType
