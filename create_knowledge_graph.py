import json
from neo4j import GraphDatabase
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

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
            # Create Character node
            character_name = character_data["character_name"]
            affiliation = character_data.get("affiliation", "Unknown")
            
            session.run("""
                MERGE (c:Character {name: $name})
            """, name=character_name, affiliation=affiliation)
            
            # Create Team node and relationship
            if affiliation != "Unknown":
                session.run("""
                    MERGE (t:Team {name: $team_name})
                    MERGE (c:Character {name: $character_name})
                    MERGE (c)-[:MEMBER_OF]->(t)
                """, team_name=affiliation, character_name=character_name)
            
            # Create Gene nodes and HAS_MUTATION relationships
            for gene_name in character_data.get("known_mutations_genes", []):
                session.run("""
                    MERGE (g:Gene {name: $gene_name})
                    MERGE (c:Character {name: $character_name})
                    MERGE (c)-[:HAS_MUTATION]->(g)
                """, gene_name=gene_name, character_name=character_name)
            
            # Create Power nodes and POSSESSES_POWER relationships
            for power_name in character_data.get("primary_powers", []):
                session.run("""
                    MERGE (p:Power {name: $power_name})
                    MERGE (c:Character {name: $character_name})
                    MERGE (c)-[:POSSESSES_POWER]->(p)
                """, power_name=power_name, character_name=character_name)
            
            # Create CONFERS relationships between genes and powers
            for relationship in character_data.get("gene_power_relationships", []):
                gene_name = relationship["gene"]
                power_name = relationship["confers"]
                session.run("""
                    MERGE (g:Gene {name: $gene_name})
                    MERGE (p:Power {name: $power_name})
                    MERGE (g)-[:CONFERS]->(p)
                """, gene_name=gene_name, power_name=power_name)
    
    def ingest_json_file(self, file_path: str):
        """Ingest data from JSON file"""
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        self.clear_database()
        self.create_constraints()
        
        for character in data["characters"]:
            self.ingest_character_data(character)
        
        print(f"Ingested {len(data['characters'])} characters into Neo4j")

if __name__ == "__main__":
    def main():
        ingestion = Neo4jDataIngestion()
        try:
            ingestion.ingest_json_file('marvel_dataset.json')
            print("Data ingested into Neo4j successfully!")
        except Exception as e:
            print(f"Error ingesting data: {e}")
            return
        finally:
            ingestion.close()
    main()
    