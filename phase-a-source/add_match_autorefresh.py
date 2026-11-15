from pathlib import Path

path = Path("templates/match.html")
content = path.read_text()

old = "loadMatch();\n</script>"
new = """loadMatch();

// Auto refresh every 60 seconds
setInterval(loadMatch, 60000);
</script>"""

if old not in content:
    print("ERROR: Target code not found.")
else:
    path.write_text(content.replace(old, new, 1))
    print("SUCCESS: Auto-refresh added.")
