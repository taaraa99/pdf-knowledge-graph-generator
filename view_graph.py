import webbrowser
import os

file_path = os.path.abspath("graph.html")
webbrowser.open(f"file:///{file_path}")
