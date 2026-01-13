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