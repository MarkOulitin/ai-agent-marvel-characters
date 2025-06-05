# Marvel Universe knowledge server
# Setup
❗❗❗ Setup your `OPENAI_API_KEY` in `.env`

(Optional) Setup your langfuse credentials `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_HOST`

Build the server docker image:
```sh
docker build -t marvel-ai-agent:latest .
```

# Run
Server:
```sh
docker compose up -d
```

# Test
## Gradio UI (proxy client to server)
Run:
```sh
conda create -n marvel python=3.12
conda activate marvel
pip install -r requirements.txt

python ui.py
```
**Follow the link** http://127.0.0.1:7860 (url of gradio ui) as you will see in the terminal:
```
Starting Gradio UI for server at http://localhost:8000
Make sure your FastAPI server is running!
* Running on local URL:  http://127.0.0.1:7860
* To create a public link, set `share=True` in `launch()`
```

## Using curl:
- Endpoint `/graph/{character}`
```
curl --location 'localhost:8000/graph/Wolverine'
```
- Endpoint `/question`
```
curl --location 'localhost:8000/question' \
--header 'Content-Type: application/json' \
--data '{
    "question": "Tell me what you know about Wolverine genes and his team members genes"
}'
```

# Graph Schema
We use Neo4j. Here are the cypher commands that generated the database (more details are in `server/create_knowledge_graph.py` and `server/marvel_dataset.json`):
* Adding a character (superhero or villian):
```
MERGE (c:Character {name: $name})
SET c.text_snippet = $text_snippet
```
* Character is memeber of a team:
```
MERGE (t:Team {name: $team_name})
MERGE (c:Character {name: $character_name})
MERGE (c)-[r:MEMBER_OF]->(t)
SET r.confidence = $confidence
```
* Character has a mutation of a gene:
```
MERGE (g:Gene {name: $gene_name})
MERGE (c:Character {name: $character_name})
MERGE (c)-[r:HAS_MUTATION]->(g)
SET r.confidence = $confidence
```
* Character posses a super power:
```
MERGE (p:Power {name: $power_name})
MERGE (c:Character {name: $character_name})
MERGE (c)-[r:POSSESSES_POWER]->(p)
SET r.confidence = $confidence
```
* Gene confers a super power:
```
MERGE (g:Gene {name: $gene_name})
MERGE (p:Power {name: $power_name})
MERGE (g)-[r:CONFERS]->(p)
SET r.confidence = $confidence
```

# Examples
1.  Example of how the ai agent capable to infer the structure of the knowledge graph - heros are linked to teams with confidence score. And generate valid query and answer. Filtering out members with confidence lower than 0.5, e.g. `Iceman` (see source data `server/marvel_dataset.json`).

    Input: 
    ```
    Return all the names team members of X-men with confidence higer than 0.5
    ```

    Response: 
    ```json
    {"response": "Here are the X-Men team members with membership confidence above 0.5:\n\n• Jubilee  \n• Beast  \n• Colossus  \n• Nightcrawler  \n• Professor X  \n• Jean Grey  \n• Cyclops  \n• Wolverine"}
    ```
2. Example of how the ai agent capable to access to the neighbors of the neighbors of in the graph - getting the genes of the team members.

   Input: 
   ```
   Tell me what you know about Wolverine genes and his team members genes
   ```
   
   Response: 
   ```json
   {"response": "Here’s what I found:\n\n1. Wolverine’s Gene Mutations  \n   • Gene Adamantium Bone Integration (confidence: 0.90)  \n   • Gene X (confidence: 0.50)  \n\n2. Wolverine’s Team: X-Men  \n   Below are the other X-Men members (excluding Wolverine) and the gene mutations reported for each:\n\n   • Beast  \n     – Gene PE-5 (0.82)  \n     – Gene EI-3 (0.66)  \n\n   • Colossus  \n     – Gene MT-4 (0.63)  \n     – Gene OS-7 (0.18)  \n\n   • Cyclops  \n     – Gene RQ-2 (0.93)  \n     – Gene OB-1 (0.29)  \n\n   • Gambit  \n     – Gene MA-8 (0.78)  \n     – Gene KE-4 (0.47)  \n\n   • Iceman  \n     – Gene MI-8 (0.58)  \n     – Gene CK-4 (0.68)  \n\n   • Jean Grey  \n     – Gene PF-1 (0.86)  \n     – Gene TP-5 (0.69)  \n\n   • Jubilee  \n     – Gene NP-2 (0.11)  \n     – Gene PG-5 (0.28)  \n\n   • Nightcrawler  \n     – Gene DS-5 (0.70)  \n     – Gene TG-2 (0.12)  \n\n   • Professor X  \n     – Gene MC-6 (0.53)  \n     – Gene OT-1 (0.06)  \n\n   • Psylocke  \n     – Gene TP-9 (0.12)  \n     – Gene PK-8 (0.73)  \n\n   • Rogue  \n     – Gene LF-1 (0.16)  \n     – Gene PA-3 (0.99)  \n\n   • Storm  \n     – Gene AP-4 (0.03)  \n     – Gene WC-9 (0.40)  \n\nAll confidence scores reflect the strength of the reported association between character and gene mutation."}
   ```
3. Access to textual snippets and team member's info and superpowers and fusion with gene info

    Input: `Tell me what you know about the X-men? What genes are the most dangerous in this group?`

    Response:
    ```json
    {
    "response": "The X-Men are Marvel’s premier mutant superhero team, founded by Professor Charles Xavier to promote peaceful coexistence between humans and mutants.  Members include (but aren’t limited to) Cyclops, Jean Grey, Wolverine, Beast, Storm, Rogue, Iceman, Nightcrawler, Colossus, Gambit, Jubilee, Psylocke and others.  Each possesses a mutation in their DNA that grants them superhuman abilities—ranging from telepathy and telekinesis to weather control, healing factors, energy manipulation and more.\n\nAccording to the mutation–power relationships in our database, “most dangerous” (i.e. most power-conferring) genes among current X-Men are those linked to the greatest number of distinct powers.  Twelve genes top the list, each tied to two different super-powers:\n\n• Gene TP-9  \n• Gene PG-5  \n• Gene KE-4  \n• Gene PE-5  \n• Gene OS-7  \n• Gene CK-4  \n• Gene PA-3  \n• Gene DS-5  \n• Gene OT-1  \n• Gene TP-5  \n• Gene WC-9  \n• Gene X  \n\nEach of these mutations is associated with two separate power effects, suggesting a higher potential for versatility—and danger—in combat or crisis scenarios.  \n\nPlease note that this reflects only the mutations and power links cataloged in our current database.  In official Marvel continuity there are many additional X-gene subtypes and power interactions that aren’t all captured here."
    }
    ```

# Breif Explanation
I used ReAct (reason and action) workflow so the LLM has access to the database and potentially can use it several times. I put strong emphasize on detailed prompt engineering. I mentioned how the graph is strctured and what kind of info can be extracted from it, what is the format of the input (cypher query) and what is the output format. Also what the tool can do. I integrated Langfuse for easier debugging, but this solution has more extensive capabilities. 