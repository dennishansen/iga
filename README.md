## Meet Iga 🦉 - A minimalist AutoGPT capable of self-improvement

_⚠️ VERY EXPERIMENTAL & UNSTABLE_

Chat with Iga via CLI, and she will perform one of the following actions:

- Talk to you: This will allow you to respond back
- Run a shell command: These run in the current directory. The output is returned to Iga.
- Read files: Iga can read the contents of specified files.
- Write files: Iga can create or overwrite files with new content.
- Think: This simply triggers another action.
  Run Iga in her own directory to enable Iga to update her own source code and system instructions. How far can Iga go with a little guidance? Let's find out.

### Run

Create `env.list` file and add `OPENAI_API_KEY=<your-api-key>` and `GPT_MODEL=gpt-3.5-turbo` or `GPT_MODEL=gpt-4` depending on which model you would like to / are able to use

Build the Docker image and run interactively (VS Code's Docker extension is helpful)

### Guidance

- Start by having her read her own files before she making changes
- Encourage Iga to test & validate her work
- Encourage her to keep trying and only ask you if she's really struggling

### Contrubuting

I would love to see Iga implement these

- Improved system instructions to 'bake in' the above guidance
- Reliable file editing
- Use of langchain
- Longer memory
- Search the web

PR useful changes, ideally those created by Iga.
