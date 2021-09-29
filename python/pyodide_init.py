import micropip

# import io
# await micropip is described in dev version doc (python future)
# stable version doc describes to use javascript promise (use .then in js caller)
# but only "await micropip" works in the downloaded stable v0.17.0a2
await micropip.install("pydicom")
# await micropip.install('pyodide/pydicom-2.2.1-py3-none-any.whl')

print("install pydicom ok")
