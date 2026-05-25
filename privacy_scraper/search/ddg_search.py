from ddgs import DDGS



def ddg_search(query, max_results=5):
	with DDGS() as ddgs:
		return list(ddgs.text(query, max_results=max_results))