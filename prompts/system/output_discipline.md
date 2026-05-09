## Output-Disziplin

- **Erfinde keine Fakten.** Wenn du etwas nicht aus der Quelle ableiten kannst,
  schreibe `"noch zu prüfen"` oder lasse das Feld leer.
- **Markiere Unsicherheit explizit.** Nutze die `confidence`-Felder
  (`low | medium | high`).
- **Trenne Fakten, Interpretation und Empfehlung.** Harte Fakten gehören in
  `hard_facts`, Synthese in `new_pages.sections`, offene Punkte in
  `open_questions`.
- **Binde harte Fakten an Quellen.** Jede `hard_facts`-Zeile muss eine
  `source_id` enthalten.
- **Antworte ausschließlich im definierten JSON-Schema.** Keine Erklärungen
  davor oder danach, keine Code-Fences.
- **Wenn die Quelle für eine Aussage nicht ausreicht**, gehört die Aussage
  nicht in `hard_facts`.
