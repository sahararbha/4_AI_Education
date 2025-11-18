import sys
import google.generativeai as genai

print("--- Python Environment Check ---")
print(f"Python Executable: {sys.executable}")
print(f"Library Version:   {genai.__version__}")
print(f"Library Path:      {genai.__file__}")
print("------------------------------")