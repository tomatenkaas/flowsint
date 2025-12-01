from typing import List
from flowsint_core.core.enricher_base import Enricher
from flowsint_enrichers.registry import flowsint_enricher
from flowsint_core.core.logger import Logger
from flowsint_types import SocialAccount, Username 
from tools.social.sherlock import SherlockTool 

# Import the decorator if needed
# from flowsint_enrichers.registry import flowsint_enricher

class SherlockEnricher(Enricher):
    """Scans usernames for linked social accounts using the Sherlock Tool."""

    InputType = Username
    OutputType = SocialAccount

    @classmethod
    def name(cls) -> str:
        return "username_to_socials_sherlock_tool" 

    @classmethod
    def category(cls) -> str:
        return "social"

    @classmethod
    def key(cls) -> str:
        return "value" # Assumed the username field is 'value'

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        """Call the SherlockTool and convert raw results to SocialAccount types."""
        results: List[OutputType] = []
        sherlock_tool = SherlockTool()

        for username_obj in data:
            username_string = username_obj.value

            Logger.info(self.sketch_id, {"message": f"Calling SherlockTool for {username_string}"})

            try:
                # 1. Call the Tool (this executes the Docker container)
                found_profiles = sherlock_tool.launch(username_string)

                # 2. Convert raw Tool data into Flowsint Types
                for hit in found_profiles:
                    # 'username_obj' is the original Pydantic Username instance
                    results.append(
                        SocialAccount(
                            username=username_obj,
                            platform=hit['site'],
                            profile_url=hit['url']
                        )
                    )

                Logger.info(self.sketch_id, {"message": f"Tool found {len(found_profiles)} accounts."})

            except Exception as e:
                Logger.error(self.sketch_id, {"message": f"Error calling Sherlock Tool: {e}"})
                continue

        return results

    def postprocess(self, results: List[OutputType], original_input: List[InputType]) -> List[OutputType]:
        """Create the graph nodes and relationships."""

        # The SocialAccount objects carry the original Username object,
        # which makes it easy to create the relationship.

        for social_account in results:
            # Determine the desired label format: @username (Platform)
            username_value = social_account.username.value
            platform_name = social_account.platform
            
            # 1. Set the custom label on the social_account object
            # This explicitly overrides the default label shown in the graph UI.
            custom_label = f"@{username_value} ({platform_name})"
            social_account.label = custom_label # The crucial line for custom label

            # 2. Create the node for the found SocialAccount
            self.create_node(social_account)

            # 3. Create the node for the original Username (if it doesn't exist yet)
            original_username_node = social_account.username
            self.create_node(original_username_node)

            # 4. Create the relationship: (USERNAME)-[HAS_ACCOUNT]->(SOCIALACCOUNT)
            self.create_relationship(
                original_username_node,
                social_account,
                "HAS_ACCOUNT"
            )

            self.log_graph_message(
                f"Account found: {social_account.username.value} on {social_account.platform}"
            )

        return results
