# Codelabs 2027

Four hands-on codelabs, about an hour each, in Spanish. Each one teaches a technology and ends with something that works. All you need is a browser and a Google account.

**Codelab site:** https://codelabs-2027-z63pqhhmxq-uc.a.run.app

| Codelab | What you learn | Runs on | Live reference |
|---|---|---|---|
| [Entrena a tu propio David](entrena-tu-david/) (Train your own David) | Your own dataset, LoRA fine-tuning of Gemma 4 E2B, base vs. tuned evaluation, GGUF export | Free Colab (T4 GPU) | Notebook with outputs and screenshots |
| [Haz que un agente use tu app](agente-mcp/) (Make an agent use your app) | Python MCP server, tool annotations, your own Gemini agent, human approval outside the agent | Cloud Shell | [Taller Volcán](https://codelab-taller-volcan-z63pqhhmxq-uc.a.run.app) |
| [Haz tu tienda legible para agentes](tienda-para-agentes/) (Make your store readable by agents) | schema.org JSON-LD, product feed, UCP profile and checkout, AP2 signatures | Cloud Shell | [Tostaduría Barrilete](https://codelab-tienda-cafe-z63pqhhmxq-uc.a.run.app) |
| [Split-brain en el navegador](gemma-en-el-navegador/) (Split-brain in the browser) | Gemma 4 E2B in the browser with LiteRT-LM Web, a deterministic personal-data detector, Gemini only sees clean text | Chrome with WebGPU | [Ask without giving away your data](https://codelab-gemma-navegador-z63pqhhmxq-uc.a.run.app) |

Each codelab goes with a talk: "David vs. Goliath", "Built for Agents", "Your Next Customer Is an AI Agent" and "Engineering with Gemma". You don't need to have seen the talk.

## Layout of each codelab

- `codelab.md`: the codelab text; the site is generated from it.
- `inicio/`: the starter code, with `TODO` markers where you write.
- `solucion/`: the result of following every step.
- `tests/`: tests for the solution, plus a test that checks the code in the text matches `solucion/`.
- `referencia/`: how the live version is deployed.

Every step was tested by following it as written, in the environment the codelab names. The outputs in the text come from those runs.

## Build the site

```bash
uv run sitio/build.py --check
npm install && npm run revisar-sitio
scripts/revisar_fugas.sh
```

## License

Code under [Apache 2.0](LICENSE). Synthetic data in `entrena-tu-david/datos/` is CC BY 4.0 (see its `DATOS.md`).
