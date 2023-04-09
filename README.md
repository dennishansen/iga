*VERY EXPERIMENTAL (UNSTABLE)*
## Meet Iga 🦉. A minimalist AutoGPT capable of self-improvement.

Chat with Iga via CLI, and she will performs one of the following actions:
- Chat: This will allow you to respond back
- Run a shell command: These run in the current directory. The output is returned to Iga.
- Think: This simply triggers another action.

Run Iga in her own directory to enable Iga to update her own source code and system instructions. How far can Iga go with a little guidance? Let's find out.

### Run

Create `.env` file and add `OPENAI_API_KEY=<your-api-key>`

Instal dependencies `pip install -r requirements.txt`

Run `python script.py`

### Guidance
- Start by having her read her own files before she making changes
- Encourage Iga to test & validate her work
- Encourage her to keep trying and only ask you if she's really struggling

### Contrubuting
I would love to see Iga implement these
- Improved system instructions to 'bake in' the above guidance
- Realiable file editing
- Use of langchain
- Longer memory
- Search the web

PR useful changes, ideally those created by Iga.
