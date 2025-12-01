from tools.dockertool import DockerTool
from typing import List, Dict, Any

class SherlockTool(DockerTool):
    """Wrapper voor de Sherlock Username Search tool."""

    image = "sherlock/sherlock"
    default_tag = "latest"

    def __init__(cls):
        super().__init__(cls.image, cls.default_tag)

    @classmethod
    def name(cls) -> str:
        return "sherlock"

    @classmethod
    def category(cls) -> str:
        return "OSINT"

    @classmethod
    def description(cls) -> str:
        return "Zoekt naar gebruikersnamen op sociale netwerken en retourneert ruwe URL's."

    def launch(self, username: str, timeout: int = 60) -> List[Dict[str, str]]:
        """
        Voert de Sherlock Docker-container uit.
        
        Args:
            username: De gebruikersnaam om te zoeken.
        Returns:
            Lijst met gevonden profielen: [{'site': 'Facebook', 'url': '...'}]
        """
        if not self.is_installed():
            self.install()

        # Gebruik --print-found om alleen hits te parsen
        command = f"{username} --print-found --timeout 1"

        try:
            raw_output = super().launch(command=command, timeout=timeout)
            return self._parse_output(raw_output)
        except Exception as e:
            print(f"Error running Sherlock: {e}")
            return []

    def _parse_output(self, output: str) -> List[Dict[str, str]]:
        """Parse de tekstoutput van Sherlock naar gestructureerde data."""
        results = []
        for line in output.strip().split('\n'):
            if "[+]" in line and ": " in line:
                try:
                    clean_line = line.replace("[+] ", "").strip()
                    site, url = clean_line.split(": ", 1)
                    results.append({"site": site.strip(), "url": url.strip()})
                except ValueError:
                    continue
        return results
