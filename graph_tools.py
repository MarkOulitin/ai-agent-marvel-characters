from neo4j import GraphDatabase
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import json

load_dotenv()

_uri = os.getenv("NEO4J_URI")
_user = os.getenv("NEO4J_USER")
_password = os.getenv("NEO4J_PASSWORD")
_driver = GraphDatabase.driver(_uri, auth=(_user, _password))

class QueryInput(BaseModel):
    cypher_query: str = Field(description="cypher query fommatted for Neo4j database")

@tool("query_characters_database", args_schema=QueryInput, return_direct=True)
def query_characters_database(cypher_query: str):
    """
    Retrieves information from Neo4j database for a given cypher query.
    The database has 4 types of nodes: Character, Power, Gene and Team
    Here are the cypher commands that ingested the data into the databse and define the links between the nodes:
    * Addint a character (superhero or villian):
    ```MERGE (c:Character {name: $name})```
    * Character is memeber of a team:
    ```MERGE (t:Team {name: $team_name})
    MERGE (c:Character {name: $character_name})
    MERGE (c)-[:MEMBER_OF]->(t)```
    * Character has a mutation of a gene:
    ```MERGE (g:Gene {name: $gene_name})
    MERGE (c:Character {name: $character_name})
    MERGE (c)-[:HAS_MUTATION]->(g)```
    * Character posses a super power:
    ```MERGE (p:Power {name: $power_name})
    MERGE (c:Character {name: $character_name})
    MERGE (c)-[:POSSESSES_POWER]->(p)```
    * Gene confers a super power:
    ```MERGE (g:Gene {name: $gene_name})
    MERGE (p:Power {name: $power_name})
    MERGE (g)-[:CONFERS]->(p)```

    Returns results in json format or 'No results found.'
    """
    try:
        with _driver.session() as session:
            result = session.run(cypher_query)
            records = [record.data() for record in result]
            if len(records) == 0:
                return 'No results found.'
            return json.dumps(records)
    except Exception as e:
        return f"Error executing query: {str(e)}"

def character_neighbors(character_name):
    cypher_query = """
    MATCH (c:Character {name: $character_name})
    OPTIONAL MATCH (c)-[:HAS_MUTATION]->(g:Gene)
    OPTIONAL MATCH (c)-[:POSSESSES_POWER]->(p:Power)
    OPTIONAL MATCH (c)-[:MEMBER_OF]->(t:Team)
    RETURN c.name as character,
            collect(DISTINCT g.name) as genes,
            collect(DISTINCT p.name) as powers,
            collect(DISTINCT t.name) as teams
    """
    
    try:
        with _driver.session() as session:
            result = session.run(cypher_query, character_name=character_name)
            record = result.single()
            
            if not record:
                return {"error": f"Character '{character_name}' not found"}
            
            return {
                "character": record["character"],
                "genes": [g for g in record["genes"] if g],
                "powers": [p for p in record["powers"] if p],
                "teams": [t for t in record["teams"] if t]
            }
    except Exception as e:
        return {"error": f"Error querying character: {str(e)}"}
