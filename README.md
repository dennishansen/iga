*VERY EXPERIMENTAL (UNSTABLE)*
## Iga. A dead simple Auto-GPT capable of self-improvement.

This script starts a CLI chat with an Auto-GPT agent Iga who performs one of the following actions along with its rationale:
- Talk to you: This allows you to respond
- Run shell command: These run in it's own directory. The output is returned to them.
- Think: This simple triggers another resposnse.

This provides provides a minimal basis for guiding Iga to update it's own source code and system instructions. Go wild but not too wild.

### Run

Create `.env` file and add `OPENAI_API_KEY=<your-api-key>`

Instal dependencies `pip install -r requirements.txt`

Run `python script.py`