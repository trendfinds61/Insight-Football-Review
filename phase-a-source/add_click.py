from pathlib import Path

path = Path("templates/index.html")
content = path.read_text()

old = '''            card.append(league, home, away, status);
            grid.appendChild(card);'''

new = '''            card.append(league, home, away, status);

            card.style.cursor = "pointer";
            card.addEventListener("click", () => {
                window.location.href = "/match/" + match.id;
            });

            grid.appendChild(card);'''

if old not in content:
    print("ERROR: Target code not found.")
else:
    path.write_text(content.replace(old, new, 1))
    print("SUCCESS: Match card click feature added.")