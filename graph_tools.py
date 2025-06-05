from neo4j import GraphDatabase
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from logger import logger
import os
import json

load_dotenv()

_uri = os.getenv("NEO4J_URI")
_user = os.getenv("NEO4J_USER")
_password = os.getenv("NEO4J_PASSWORD")
_driver = GraphDatabase.driver(_uri, auth=(_user, _password))

class QueryInput(BaseModel):
    cypher_query: str = Field(description="cypher query formatted for Neo4j database")

@tool("query_characters_database", args_schema=QueryInput, return_direct=True)
def query_characters_database(cypher_query: str):
    """
    Retrieves information from Neo4j database for a given cypher query.
    The database has 4 types of nodes: Character, Power, Gene and Team
    All names are case sensitive. When matching with specific string use lowercase, e.g. ```WHERE toLower(p.name) = toLower("Lightning Control")```.
    Here are the cypher commands that ingested the data into the databse and define the links between the nodes:
    * Addint a character (superhero or villian):
    ```MERGE (c:Character {name: $name})
    SET c.text_snippet = $text_snippet```
    * Character is memeber of a team:
    ```MERGE (t:Team {name: $team_name})
    MERGE (c:Character {name: $character_name})
    MERGE (c)-[r:MEMBER_OF]->(t)
    SET r.confidence = $confidence```
    * Character has a mutation of a gene:
    ```MERGE (g:Gene {name: $gene_name})
    MERGE (c:Character {name: $character_name})
    MERGE (c)-[r:HAS_MUTATION]->(g)
    SET r.confidence = $confidence```
    * Character posses a super power:
    ```MERGE (p:Power {name: $power_name})
    MERGE (c:Character {name: $character_name})
    MERGE (c)-[r:POSSESSES_POWER]->(p)
    SET r.confidence = $confidence```
    * Gene confers a super power:
    ```MERGE (g:Gene {name: $gene_name})
    MERGE (p:Power {name: $power_name})
    MERGE (g)-[r:CONFERS]->(p)
    SET r.confidence = $confidence```

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

def character_neighbors(character_name, request_id=None):
    cypher_query = """
    MATCH (c:Character {name: $character_name})
    OPTIONAL MATCH (c)-[r1:HAS_MUTATION]->(g:Gene)
    OPTIONAL MATCH (c)-[r2:POSSESSES_POWER]->(p:Power)
    OPTIONAL MATCH (c)-[r3:MEMBER_OF]->(t:Team)
    RETURN c.name as character,
        c.text_snippet as text_snippet,
        collect(DISTINCT {name: g.name, confidence: r1.confidence}) as genes,
        collect(DISTINCT {name: p.name, confidence: r2.confidence}) as powers,
        collect(DISTINCT {name: t.name, confidence: r3.confidence}) as teams
    """
    
    try:
        with _driver.session() as session:
            result = session.run(cypher_query, character_name=character_name)
            record = result.single()
            
            if not record:
                return {"error": f"Character '{character_name}' not found"}
            
            return {
                "character": record["character"],
                "text_snippet": record["text_snippet"],
                "genes": record["genes"],
                "powers": record["powers"],
                "teams": record["teams"],
            }
    except Exception as e:
        logger.error(f'Got error in querying character neighbors: {e}, request_id {request_id}')
        logger.exception(e)
        return {"error": f"Error querying character: {str(e)}"}
