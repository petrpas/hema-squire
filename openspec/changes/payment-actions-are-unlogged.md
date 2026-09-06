# Ruční zásahy na Platbách nejsou nikde k přečtení

Analýza, ne návrh změny. Zapsáno 2026-09-06 poté, co se ukázalo, že panel
ručních změn je na fázi Platby vždycky prázdný.

## Co se děje

Rail ručních změn filtruje `sheet.edits` na `edit.phase === "payments"`
(`Console.tsx:383`). Jediné pravidlo, které tu fázi nese, je `payment_link`,
a to se do `sheet.edits` nedostane ze dvou nezávislých důvodů:

1. jeho handler je `_apply_opaque` (`rules.py:158`), který vrací `[]` — replay
   z něj nevyrobí žádný `AppliedChange`;
2. jeho target je `txn:<external_id>`, ne id řádku tabulky, takže by ho replay
   přeskočil na `if rule.target not in rows` (`rules.py:281`) i kdyby handler
   něco vracel.

Hlubší důvod je ale ten, že **většina ručních zásahů na Platbách vůbec není
pravidlo.** Ruční zaškrtnutí „zaplaceno", zapsaná platba i její stornování,
reinstate, označení k vrácení a rozšíření tolerance zapisují rovnou do stavu a
vedle toho `PaymentEvent`. Kolem edit-rules enginu procházejí úplně.

## Co z toho je záměr

Že ty akce nejsou pravidla, je správně. Pravidlo je definované jako
přehratelná operace nad tabulkou — `openspec/project.md`: „table state is a
pure function of (source records, rule set, operation parameters)". Přijatá
platba není operace nad tabulkou, je to fakt o světě. Kdyby ruční zaškrtnutí
bylo pravidlo, přehrání sady pravidel by ho muselo umět znovu vykonat, a tím by
se stav placení stal odvozeninou z logu editací místo z peněz.

Záměr je i to, že každý druh platební akce má vlastní pohled. `payments-console`
to má zapsané: *Payment links are visible and removable*, *Payments recorded by
hand are listed and removable*. Linky i zapsané platby vidět jsou — jen jinde
než v railu.

## Co je díra

**1. Ruční zaškrtnutí „zaplaceno" nemá seznam nikde.** Vidíš ho na buňce toho
jednoho řádku a nikde jinde. Otázka „koho jsme letos pustili zdarma" nemá kde
být zodpovězena, přestože odpověď je uložená: `settled_by_hand_at`,
`settled_by_hand_reason` na registraci a `PaymentEvent` vedle toho. Je to
zároveň ten zásah, který si o seznam říká nejvíc — je to jediná cesta, jak se
registrace stane zaplacenou bez peněz, a `add-manual-paid-marking` D2 ji
povolila právě pod podmínkou, že po sobě nechá čitelnou stopu.

**2. `payment_events` nemá žádný endpoint.** Celá auditní stopa plateb —
spárování, neshody, upomínky, expirace, reinstaty, každý ruční zásah — je
v databázi a z UI nedosažitelná. Tabulka se v kódu čte jen na jednom místě
(`payments.py:594`, dotaz na `expired_holding_payment`), jinak se do ní pouze
zapisuje. Migrace `d5a83c1f206e` se na ni odvolává jako na místo, kde přežívají
přepsané importní instanty; je to pravda, ale jen pro toho, kdo umí SQL.

## Na co se bude třeba zeptat

- Je to **jeden pohled, nebo dva?** Log platebních událostí a seznam ručních
  zaškrtnutí jsou dvě různé otázky: „co se s penězi dělo" a „kdo je pustil
  zdarma". Jeden pohled odpovídá na obě špatně, dva znamenají dvě místa.
- **Kde stojí?** Rail je vyhrazený pro pravidla a jejich vrácení — vrátit
  `PaymentEvent` nelze, takže tam nepatří, aniž by se zrušilo, co rail znamená.
  Fronty jsou v hlavním sloupci (`payments-console-owner-decisions`), takže
  hlavní sloupec pod tabulkou je pravděpodobnější místo.
- **Co je čitelná událost?** `PaymentEvent.detail` je dnes anglická technická
  věta stavěná pro čtení v databázi (`"VS 2501001: 100000 cents CZK, 5000 cents
  still outstanding"`). Pohled pro organizátora znamená buď to překládat na
  čtení z `kind` + strukturovaných polí, nebo změnit, co se do `detail` píše —
  a to druhé je změna dat, ne zobrazení.
- **Jak daleko zpět?** Turnaj po sezóně jich má tisíce. Stránkování, nebo
  filtr na registraci?

## Kde to sáhne

`app/models.py` (`PaymentEvent`), `app/routers/payments.py` (nový read
endpoint), `frontend/src/` (nový panel), `openspec/specs/payments-console/`
(nový requirement), lokalizace pro každý `kind`.
