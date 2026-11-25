# Backend Lab demo website

One page with two live demos:
- **Payments API:** pay, retry, race requests, refund, and break it with the unsafe button. It runs in your browser, or against your deployed payments API (Connect tab).
- **AI incident research:** 10 sample incidents from llm-rca-bench. Diagnose them yourself, then compare with the true cause and with every method's answer, plus accuracy charts across the whole benchmark.

## Update the research results
After you run AI models in `llm-rca-bench`, rebuild the page so it shows your real AI results:
```
python build.py --rca ../llm-rca-bench
```
(Keep `demo-website` and `llm-rca-bench` side by side, or pass the right path.)

## Deploy
On vercel.com: Add New → Project, import the repo containing this folder, then deploy. Only `index.html` is served.
(Or on netlify.com, drag this folder onto "Deploy manually".)
Then open **Connect** and paste your payments API URL.
