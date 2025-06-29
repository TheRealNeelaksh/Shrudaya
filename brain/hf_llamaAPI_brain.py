# !pip install llama-cpp-python

from llama_cpp import Llama

llm = Llama.from_pretrained(
	repo_id="NeelakshSaxena/LLaMA_Shrydaya_3.2-Instruct",
	filename="Llama-3.2-1B-Instruct-UD-Q4_K_XL.gguf",
)
