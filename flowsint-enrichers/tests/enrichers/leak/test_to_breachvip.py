import pytest

from flowsint_types.email import Email 
from flowsint_types.leak import Leak
from flowsint_enrichers.leak.to_breachvip import EmailToBreachVipEnricher

# Gebruik pytest-asyncio voor het testen van asynchrone methoden
pytestmark = pytest.mark.asyncio 

# Dit is een 'geïntegreerde' test omdat het de echte BreachVIP API aanroept.
# Je zou hier normaal een 'mock' of 'fixture' gebruiken, maar voor snelle validatie
# gebruiken we een echt e-mailadres dat waarschijnlijk gelekt is (of een test-term).
TEST_EMAIL = "billgates@microsoft.com" 

async def test_breachvip_enricher_scan():
    """Test de scan-methode door een e-mailadres naar de BreachVIP API te sturen."""
    
    enricher = EmailToBreachVipEnricher()
    
    # 1. Creëer de input: een lijst met één EmailAddress object
    input_email = Email(email=TEST_EMAIL)
    data_input = [input_email]
    
    print(f"\n--- Testing BreachVIP Scan met: {TEST_EMAIL} ---")    # ... (code om input_email en data_input te creëren)
    
    # 2. Roep de asynchrone scan-methode aan
    results = await enricher.scan(data_input)

    # 3. Assertions (Controles)

    # a. Controleer of het resultaat een lijst is
    assert isinstance(results, list)

    # b. Controleer of er resultaten zijn gevonden 
    assert len(results) > 0, f"❌ FAILURE: Geen breaches gevonden voor {TEST_EMAIL}. Controleer API-sleutel en Rate Limit."

    # c. Controleer of de output het juiste type is
    first_result = results[0]
    # FIX: Controleer op Leak in plaats van BreachVipResult
    assert isinstance(first_result, Leak) 
    
    # d. Controleer de essentiële velden
    # FIX: De Leak-klasse heeft 'name', niet 'source'.
    assert first_result.name is not None
    # De velden 'categories' en 'original_email' zijn nu custom attributen,
    # dus controleer alleen op de Pydantic velden van de Leak class.
    assert first_result.leak is not None
    
    print(f"✅ SUCCESS: {len(results)} breaches gevonden. Eerste bron: {first_result.name}")
