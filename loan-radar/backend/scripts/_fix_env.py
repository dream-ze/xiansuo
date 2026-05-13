import pathlib

p = pathlib.Path(__file__).resolve().parents[1] / ".env"
lines = p.read_text(encoding="utf-8-sig").splitlines()

# Find the XHS_COOKIES= empty line and the following cookie value line
cookie_val = ""
rest_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip() == "XHS_COOKIES=" or line.strip().startswith("XHS_COOKIES=\n") or (line.startswith("XHS_COOKIES=") and not line[len("XHS_COOKIES="):].strip()):
        # Next non-empty line is the cookie value
        if i + 1 < len(lines) and lines[i + 1].startswith("abRequestId="):
            cookie_val = lines[i + 1].strip()
            i += 2
        else:
            rest_lines.append(line)
            i += 1
    elif line.startswith("abRequestId=") and not cookie_val:
        # Orphaned cookie line - use as value
        cookie_val = line.strip()
        i += 1
    elif line.startswith("XHS_TEST_KEYWORD="):
        rest_lines.append("XHS_TEST_KEYWORD=征信花了")
        i += 1
    else:
        if line.strip():
            rest_lines.append(line)
        i += 1

new_content = "XHS_COOKIES=" + cookie_val + "\n" + "\n".join(rest_lines) + "\n"
p.write_text(new_content, encoding="utf-8")
print("Fixed .env:")
for line in p.read_text(encoding="utf-8").splitlines():
    key = line.split("=")[0] if "=" in line else line
    val_len = len(line.split("=", 1)[1]) if "=" in line else 0
    print(f"  {key} = {val_len} chars")
