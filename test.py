from freedom_parser import parse_freedom_pdf

txs = parse_freedom_pdf("freedom_statement.pdf")

print(f"Найдено операций: {len(txs)}\n")

for t in txs[:10]:
    print(t)
