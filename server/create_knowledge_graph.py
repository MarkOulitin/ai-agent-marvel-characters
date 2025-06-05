from neo4j import GraphDatabase
from typing import Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm
import json
import os
import time

load_dotenv()

class Neo4jDataIngestion:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear all nodes and relationships"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def create_constraints(self):
        """Create unique constraints for node properties"""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT character_name IF NOT EXISTS FOR (c:Character) REQUIRE c.name IS UNIQUE",
                "CREATE CONSTRAINT gene_name IF NOT EXISTS FOR (g:Gene) REQUIRE g.name IS UNIQUE",
                "CREATE CONSTRAINT power_name IF NOT EXISTS FOR (p:Power) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT team_name IF NOT EXISTS FOR (t:Team) REQUIRE t.name IS UNIQUE"
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Constraint creation warning: {e}")
    
    def ingest_character_data(self, character_data: Dict[str, Any]):
        """Ingest a single character's data into Neo4j"""
        with self.driver.session() as session:
            # Create Character node with text snippet
            character_name = character_data["character_name"]
            text_snippet = character_data.get("text_snippet", "")
            
            session.run("""
                MERGE (c:Character {name: $name})
                SET c.text_snippet = $text_snippet
            """, name=character_name, text_snippet=text_snippet)
            
            # Create Team node and relationship with confidence
            affiliation = character_data.get("affiliation")
            if affiliation and isinstance(affiliation, dict):
                team_name = affiliation.get("name")
                confidence = affiliation.get("confidence", 0.0)
                
                if team_name:
                    session.run("""
                        MERGE (t:Team {name: $team_name})
                        MERGE (c:Character {name: $character_name})
                        MERGE (c)-[r:MEMBER_OF]->(t)
                        SET r.confidence = $confidence
                    """, team_name=team_name, character_name=character_name, confidence=confidence)
            elif affiliation and isinstance(affiliation, str) and affiliation != "Unknown":
                session.run("""
                    MERGE (t:Team {name: $team_name})
                    MERGE (c:Character {name: $character_name})
                    MERGE (c)-[r:MEMBER_OF]->(t)
                    SET r.confidence = $confidence
                """, team_name=affiliation, character_name=character_name, confidence=1.0)
            
            # Create Gene nodes and HAS_MUTATION relationships with confidence
            for gene_data in character_data.get("known_mutations_genes", []):
                if isinstance(gene_data, dict):
                    gene_name = gene_data.get("name")
                    confidence = gene_data.get("confidence", 0.0)
                else:
                    gene_name = gene_data
                    confidence = 1.0
                
                if gene_name:
                    session.run("""
                        MERGE (g:Gene {name: $gene_name})
                        MERGE (c:Character {name: $character_name})
                        MERGE (c)-[r:HAS_MUTATION]->(g)
                        SET r.confidence = $confidence
                    """, gene_name=gene_name, character_name=character_name, confidence=confidence)
            
            # Create Power nodes and POSSESSES_POWER relationships with confidence
            for power_data in character_data.get("primary_powers", []):
                if isinstance(power_data, dict):
                    power_name = power_data.get("name")
                    confidence = power_data.get("confidence", 0.0)
                else:
                    power_name = power_data
                    confidence = 1.0
                
                if power_name:
                    session.run("""
                        MERGE (p:Power {name: $power_name})
                        MERGE (c:Character {name: $character_name})
                        MERGE (c)-[r:POSSESSES_POWER]->(p)
                        SET r.confidence = $confidence
                    """, power_name=power_name, character_name=character_name, confidence=confidence)
            
            # Create CONFERS relationships between genes and powers with confidence
            for relationship in character_data.get("gene_power_relationships", []):
                gene_name = relationship.get("gene")
                power_name = relationship.get("confers")
                confidence = relationship.get("confidence", 0.0)
                
                if gene_name and power_name:
                    session.run("""
                        MERGE (g:Gene {name: $gene_name})
                        MERGE (p:Power {name: $power_name})
                        MERGE (g)-[r:CONFERS]->(p)
                        SET r.confidence = $confidence
                    """, gene_name=gene_name, power_name=power_name, confidence=confidence)
    
    def ingest_json_file(self, file_path: str):
        """Ingest data from JSON file"""
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        self.clear_database()
        self.create_constraints()
        
        for character in tqdm(data["characters"], desc='Ingesting characters'):
            self.ingest_character_data(character)
        
        print(f"Ingested {len(data['characters'])} characters into Neo4j")

def main():
    ingestion = Neo4jDataIngestion()
    last_attempt = 0
    max_attempts = 20
    for attempt in range(max_attempts):
        try:
            ingestion.driver.verify_connectivity()
            break
        except Exception as e:
            print(f"[{attempt+1}/{max_attempts}] Not connected to Neo4j (probably Neo4j server still in setup): {e}", flush=True)
        last_attempt = attempt
        if last_attempt >= max_attempts-1:
            print('Timeout for conneting to Neo4j', flush=True)
            exit(1)
        else:
            time.sleep(5)

    print('Successfully connected to Neo4j!', flush=True)
    try:
        ingestion.ingest_json_file(os.path.join(os.path.dirname(__file__), 'marvel_dataset.json'))
        print("Data ingested into Neo4j successfully!")
    except Exception as e:
        print(f"Error ingesting data: {e}")
        return
    finally:
        ingestion.close()

if __name__ == "__main__":
    main()