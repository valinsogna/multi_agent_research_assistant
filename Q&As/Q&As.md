# Questions and Answers

This section contains a collection of frequently asked questions (FAQs) along with their answers. If you have any questions that are not covered here, feel free to reach out for more information.

## Q1: How do the agents coordinate their actions in LangGraph? Is it event-driven?
The coordination does not use events or async listeners. 
LangGraph works like a 'engine' that executes nodes in sequence. 
Each node is an async function that receives the current state, does its work, and returns a dictionary with the changes. LangGraph automatically merges these changes into the state. 
So the Analysis Agent doesn't 'know' when to start - it's LangGraph that calls it after Research is done, passing it the updated state which now contains research_results. 
It's a simpler and more deterministic pattern than event-driven, easier to debug and test.

## Q2: How do the agents share information? Is there a shared memory or context window?
Every agent makes completely independent LLM calls - there is no shared memory or growing context window.
Data passes through the WorkflowState, but is always truncated before being sent to the next LLM.
For example, the Analysis Agent receives 5/10 web results by default settings, with snippets truncated to 200 characters.
This ensures that each call stays under 2000 tokens, compatible even with small models like Llama 3.2 3B.
It's a trade-off: we lose some information but ensure stability and speed.

## Q3: How does the Research Agent perform web searches? Does it use APIs?
The Research Agent generates user queries into multiple variants to cover different angles. 
Then it performs parallel searches: web search for articles and documents, news search for recent news from the last week.
It uses DuckDuckGo because it's free and doesn't require API keys.
The parameters are conservative - maximum 5 results per query, 15 seconds timeout - to balance completeness and speed.
Optionally it can do 'deep search' by downloading full content of the most relevant pages.
At the end, it passes everything to the LLM for initial quality analysis.

## Q4: How is data truncation handled to protect the context window?

In the system, data flows through a shared state called WorkflowState, following a blackboard pattern. Each agent reads what it needs and writes its output.
Regarding context window protection, truncation happens at two points:
- **Research Agent** searches DuckDuckGo and saves the complete results in the state - snippets are typically 300-500 characters. However, when it performs its internal preliminary analysis, it truncates snippets to 200 characters and uses only the first 5 results. This preliminary analysis is just to get an initial confidence score.
- **Analysis Agent** receives the complete results, but when it prepares the context for the LLM, it applies truncation again: it takes only 5 web results, truncates snippets to 200 characters, takes only 3 news items, and limits deep content to 1000 characters per page.
This approach has some redundancy - both agents truncate - but it's a deliberate choice for safety: each agent is responsible for controlling the size of its own context before calling the LLM. This way, even if I were to modify the Research Agent in the future to save more data, the Analysis Agent would still be protected.
The final result is a context of approximately 800-1000 tokens per LLM call, which is compatible even with small models like Llama 3.2 3B that only has a 4K context window. In total, the workflow makes 4 LLM calls - one for Research, one for Analysis, two for Synthesis - and none of these exceeds 2000 input tokens.
