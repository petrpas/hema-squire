1. ~~Zakládání turnaje - layout~~ (hotovo 2026-09-06)
  - zmenšit mezeru před hline aby byla symetrická mezeře za hline
  - co turnaj zahrnuje - změnit na rozšiřující možnosti
  - texty:
    - Šermíři se hlásí ve Squire. Ten za tebe vede stav přihlášek a seznamy. -> Squire se stará o všechno: přihlášky, odhlášky, seznamy, změny... 
    - Ve Squire se nikdo nepřihlásí a Squire nikomu nic neposílá. -> Přihlášky si sbírám sám, do Squire nahraju seznam lidí
    - payments auto: Squire obstarává platby, řekne si o peníze, hlídá kdo zaplatil, upomíná ostatní.
    - Platby si řešíš sám. Squire soupisku nacení pro export a peněz se nedotkne. -> Platby si řešíš sám. Ve Squire jen nastavíš, kdo zaplatil a kdo ne.
2. ~~Deduplikace~~ (hotovo 2026-09-06)
  - Poznámka ke sloučení -> Pozn.
    - nechceme široký první sloupec, je to plýtvání místem na užších monitorech 
3. ~~Platby~~ (hotovo 2026-09-06)
  - Výpis z libovolné banky, jako CSV nebo XLSX. -> Výpis účtu (.csv, .xlsx)
  - Mazání není dostupné: 43 plateb je připsaných šermířům. Nejdřív je odpojte. -> Mazání není dostupné: odpojte platby.
  - Turnaj nemá nastavený token k bankovnímu API, stahovat tedy nelze. -> Bankovní API: není nastaven token 
  - mezi odstavce umístit malou mezeru
  - Tolerance párování -> radikálně změnšit
      - Jen jeden nadpis Tolerance párování částky (%)
      - tlačítko uložit - na stejném řádku jako editační pole, místo popisku ikona
      - [i] popup vylézá z tabulky - natavit align na center bottom
  - tlačítko Spustit expirace a upomínky skryto (2026-09-06) — v manuálním
    režimu vracelo samé nuly a jediné, co udělat mohlo, bylo orazítkovat
    `seating_settled_at`. Endpoint `POST /payments/process` i testy zůstávají,
    plánovač průchody dál spouští sám. Vrátit jako akce nad tabulkou neplatičů
4. ~~Smazání šermíře~~ (hotovo 2026-09-06) — maže se jen na Importu a Šermířích
   - jen v tabulkách Import a Šermíři, vyhodit z platby a párování na HR
5. Šermíři
   - nejde mi edit disciplín
   - **diagnóza (2026-09-06):** buňka se otevře jen na Šermířích a jen u řádku
     bez `registration_id` (`Console.tsx`). Protože vystavení registrací je teď
     součástí intaku, po importu má registraci každý řádek — podmínka je fakticky
     mrtvá a buňka se neotevře nikdy
   - **rozhodnuto:** otevřít i u vystavených registrací a při úpravě přepočítat,
     co registrace dluží. Rozepsáno jako change `edit-issued-disciplines`
     (2026-09-06) — artefakty hotové, implementace nezačatá
6. ~~Párování na HR~~ (hotovo 2026-09-06) — editovatelné zůstalo hr_id a verdikt
   - zrušit editovatelnost tabulky kromě pole HRID a match
