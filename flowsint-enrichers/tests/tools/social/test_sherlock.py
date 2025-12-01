# flowsint-enrichers/tests/tools/social/test_sherlock_tool.py
from tools.social.sherlock import SherlockTool # Pas het pad aan naar 'social'
from typing import List, Dict, Any
import pytest
 
@pytest.mark.docker
def test_tool_install():
    """Test dat de Sherlock Docker image succesvol gepulled kan worden."""
    tool = SherlockTool()
    tool.install()
    assert tool.is_installed()
    print(f"\n✅ Sherlock image {tool.image} is succesvol geïnstalleerd.")
 
@pytest.mark.docker
def test_tool_launch_valid_user():
    """Test het uitvoeren van de tool tegen een bekende, bestaande gebruikersnaam."""
    tool = SherlockTool()
    
    # Gebruik een gebruikersnaam die gegarandeerd resultaten oplevert voor een goede test
    # Bijv. een bekende testgebruiker, of 'billgates' (als voorbeeld).
    TEST_USER = "TheRock" # Of een andere gebruiker met veel accounts
    
    # De launch methode zou een List[Dict[str, str]] moeten retourneren.
    results: List[Dict[str, str]] = tool.launch(TEST_USER)
    
    # 1. Controleer of het resultaat een lijst is
    assert isinstance(results, list)
    
    # 2. Controleer of er resultaten zijn gevonden (minimaal 1 hit)
    assert len(results) > 0, f"Geen hits gevonden voor gebruiker {TEST_USER}. Test faalt."
    
    # 3. Controleer de structuur van het eerste resultaat (bevat 'site' en 'url')
    assert "site" in results[0]
    assert "url" in results[0]
    
    print(f"\n✅ Sherlock tool succesvol uitgevoerd. {len(results)} hits gevonden voor {TEST_USER}.")
