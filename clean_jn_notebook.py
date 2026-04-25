import nbformat

nb = nbformat.read("notebook.ipynb", as_version=4)

# Remove problematic widget metadata
if "widgets" in nb.metadata:
    del nb.metadata["widgets"]

nbformat.write(nb, "clean_notebook.ipynb")